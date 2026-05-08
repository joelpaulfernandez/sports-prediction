"""
Accuracy tracking route.

WHAT THIS FILE DOES (in plain English)
──────────────────────────────────────
Whenever we make a prediction, we save it in Supabase. Once the game finishes,
we want to check whether we got it right and add that result to a separate
"accuracy_log" table. This file does both of those jobs:

  GET  /api/accuracy          — reads the accuracy_log and returns stats:
                                 how many predictions, how many right,
                                 percentage, last update timestamp.
                                 Used by the AccuracyBanner on the frontend.

  POST /api/accuracy/update   — scans the last week of predictions, looks up
                                 which games have finished, and writes the
                                 outcome (correct or wrong) into accuracy_log.
                                 Runs every 5 minutes via the warming task,
                                 plus once on every server startup.
"""

import datetime
from datetime import timezone

from fastapi import APIRouter

from app.schemas.prediction import AccuracyStats
from app.services.db import get_db
from app.services.prediction_engine import get_prediction_engine

router = APIRouter(prefix="/api", tags=["accuracy"])


@router.get("/accuracy", response_model=AccuracyStats)
def get_accuracy():
    """
    Return the running accuracy stats. The frontend's AccuracyBanner reads this.

    Just a count of all rows in accuracy_log: total, how many were correct,
    and the percentage. We also include the model's cross-validation accuracy
    so the UI can show "model trained at ~68%" alongside the live result.
    """
    db = get_db()
    # Pull just the two columns we need from every row in accuracy_log.
    rows = db.table("accuracy_log").select("correct,timestamp").execute().data

    # Tally up.
    total = len(rows)
    correct = sum(1 for r in rows if r.get("correct") is True)
    accuracy_pct = round(correct / total * 100, 2) if total > 0 else 0.0

    # "last_updated" is the most recent timestamp in the table — the frontend
    # uses this to decide when something has changed.
    last_updated = datetime.datetime.now(tz=timezone.utc).isoformat()
    timestamps = [r["timestamp"] for r in rows if r.get("timestamp")]
    if timestamps:
        last_updated = max(timestamps)

    engine = get_prediction_engine()
    return AccuracyStats(
        total_predictions=total,
        correct_predictions=correct,
        accuracy_percentage=accuracy_pct,
        last_updated=last_updated,
        model_cv_accuracy=engine.cv_accuracy,    # how the model scored during training
        model_version=engine.model_version,      # "xgboost-v1" or "rule-based"
    )


# How many days back we'll look for predictions that haven't been graded yet.
# Set to 7 because games sometimes get rescheduled or delayed; 1 or 2 days
# isn't enough to catch those — they'd silently get skipped forever.
RESOLUTION_WINDOW_DAYS = 7


@router.post("/accuracy/update", status_code=200)
async def update_accuracy():
    """
    Walk through the last week of stored predictions, find the ones whose
    games are now finished, and write a row into accuracy_log for each.

    Two important details:

    1. We use UTC dates throughout because predictions are stored with their
       game_date in UTC (derived from gameTimeUTC). If we used server-local
       time here, late-night ET games would land on the wrong day.

    2. We compare home-vs-away "side" rather than team names, to avoid
       brittle string matches like "LA Lakers" vs "Los Angeles Lakers".
       More on this below.
    """
    import asyncio
    from app.services import nba_data

    db = get_db()

    # Build the list of dates to scan: today, yesterday, ..., 6 days ago.
    today = datetime.datetime.now(tz=timezone.utc).date()
    target_dates = [
        str(today - datetime.timedelta(days=i))
        for i in range(RESOLUTION_WINDOW_DAYS)
    ]

    # Fetch every prediction we made during that window from Supabase.
    predictions = (
        db.table("predictions")
        .select("*")
        .in_("game_date", target_dates)
        .execute()
        .data
    )
    if not predictions:
        return {"updated": 0, "message": f"No predictions stored in window {target_dates[-1]}..{target_dates[0]}"}

    # For each date, ask the NBA which games finished and who won. We store
    # whether the HOME team won (a boolean), not the team name. This lets us
    # compare against our prediction by "side" instead of by name later.
    actual_winners: dict[str, dict] = {}
    for d in target_dates:
        try:
            # Get every game that took place on this date (live + finished).
            games = await asyncio.to_thread(nba_data.get_todays_games, d)
        except Exception as exc:
            # NBA API hiccup — log it and continue with other dates.
            print(f"[accuracy] Could not fetch results for {d}: {exc}")
            continue
        for game in games:
            # status_id == 3 means "Final"; we only care about finished games.
            if int(game.get("status_id", 0)) != 3:
                continue
            home_pts = game.get("home_pts")
            away_pts = game.get("away_pts")
            # Skip if scores aren't populated yet.
            if home_pts is None or away_pts is None:
                continue
            home_won = home_pts > away_pts
            # Index by game_id for easy lookup against our predictions.
            actual_winners[str(game["id"])] = {
                "home_won": home_won,
                "winner_name": game["home_team_name"] if home_won else game["away_team_name"],
                "date": d,
            }

    if not actual_winners:
        return {"updated": 0, "message": "No newly finished games to resolve"}

    # Don't double-log the same game. Pull existing entries from accuracy_log
    # so we know which game_ids we've already graded.
    already_logged = {
        r["game_id"]
        for r in db.table("accuracy_log")
        .select("game_id")
        .in_("game_id", list(actual_winners.keys()))
        .execute()
        .data
    }

    # Build the rows we need to insert.
    rows_to_insert = []
    for pred in predictions:
        gid = pred["game_id"]
        # Skip if already logged or if the game hasn't finished yet.
        if gid in already_logged or gid not in actual_winners:
            continue
        info = actual_winners[gid]
        # Determine which "side" we predicted: home or away.
        # Comparing predicted_winner to home_team here is safe because both
        # strings came from the same prediction row — same source, same format.
        predicted_home = pred.get("predicted_winner") == pred.get("home_team")
        # We're correct iff our predicted side matches the actual winning side.
        # This avoids comparing team names across data sources, which could
        # fail on subtle differences like "LA Lakers" vs "Los Angeles Lakers".
        is_correct = predicted_home == info["home_won"]
        rows_to_insert.append({
            "game_id": gid,
            "game_date": info["date"],
            "home_team": pred["home_team"],
            "away_team": pred["away_team"],
            "predicted_winner": pred["predicted_winner"],
            "actual_winner": info["winner_name"],
            "correct": is_correct,
            "confidence": pred.get("confidence"),
            "timestamp": datetime.datetime.now(tz=timezone.utc).isoformat(),
        })

    if rows_to_insert:
        db.table("accuracy_log").insert(rows_to_insert).execute()

    return {
        "updated": len(rows_to_insert),
        "message": f"Resolved {len(rows_to_insert)} prediction(s)",
    }
