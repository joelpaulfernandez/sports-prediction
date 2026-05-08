"""
Accuracy tracking route.

GET  /api/accuracy          — return historical accuracy stats
POST /api/accuracy/update   — resolve any unresolved predictions whose game has
                              finished (today, yesterday, or further back)
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
    """Return historical model accuracy statistics."""
    db = get_db()
    rows = db.table("accuracy_log").select("correct,timestamp").execute().data

    total = len(rows)
    correct = sum(1 for r in rows if r.get("correct") is True)
    accuracy_pct = round(correct / total * 100, 2) if total > 0 else 0.0

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
        model_cv_accuracy=engine.cv_accuracy,
        model_version=engine.model_version,
    )


RESOLUTION_WINDOW_DAYS = 7  # how far back we'll resolve unmarked predictions


@router.post("/accuracy/update", status_code=200)
async def update_accuracy():
    """
    Resolve any predictions whose game has finished but isn't yet in
    accuracy_log. Scans the last RESOLUTION_WINDOW_DAYS days so games delayed
    or rescheduled past a single day don't get orphaned.

    Uses explicit UTC because game_date in Supabase is set from gameTimeUTC[:10]
    — anchoring to server-local time would skew on UTC-offset servers.
    """
    import asyncio
    from app.services import nba_data

    db = get_db()
    today = datetime.datetime.now(tz=timezone.utc).date()
    target_dates = [
        str(today - datetime.timedelta(days=i))
        for i in range(RESOLUTION_WINDOW_DAYS)
    ]

    # Pull all stored predictions for those dates
    predictions = (
        db.table("predictions")
        .select("*")
        .in_("game_date", target_dates)
        .execute()
        .data
    )
    if not predictions:
        return {"updated": 0, "message": f"No predictions stored in window {target_dates[-1]}..{target_dates[0]}"}

    # Fetch finished games per date and aggregate winners. We track which side
    # (home or away) won rather than the team name, so the prediction's
    # "predicted side" and the actual winning side can be compared with no
    # cross-source string matching ("LA Lakers" vs "Los Angeles Lakers").
    actual_winners: dict[str, dict] = {}
    for d in target_dates:
        try:
            games = await asyncio.to_thread(nba_data.get_todays_games, d)
        except Exception as exc:
            print(f"[accuracy] Could not fetch results for {d}: {exc}")
            continue
        for game in games:
            if int(game.get("status_id", 0)) != 3:
                continue  # not finished
            home_pts = game.get("home_pts")
            away_pts = game.get("away_pts")
            if home_pts is None or away_pts is None:
                continue
            home_won = home_pts > away_pts
            actual_winners[str(game["id"])] = {
                "home_won": home_won,
                "winner_name": game["home_team_name"] if home_won else game["away_team_name"],
                "date": d,
            }

    if not actual_winners:
        return {"updated": 0, "message": "No newly finished games to resolve"}

    already_logged = {
        r["game_id"]
        for r in db.table("accuracy_log")
        .select("game_id")
        .in_("game_id", list(actual_winners.keys()))
        .execute()
        .data
    }

    rows_to_insert = []
    for pred in predictions:
        gid = pred["game_id"]
        if gid in already_logged or gid not in actual_winners:
            continue
        info = actual_winners[gid]
        # The prediction record carries home_team, away_team, and predicted_winner
        # all sourced from the same row, so comparing predicted_winner to home_team
        # is a safe local string comparison. We then compare "side" (home vs away)
        # to the actual winning side, which is robust to name format differences.
        predicted_home = pred.get("predicted_winner") == pred.get("home_team")
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
