"""
Accuracy tracking route.

GET  /api/accuracy          — return historical accuracy stats
POST /api/accuracy/update   — check yesterday's predictions against actual results
                               and update the accuracy log (called from startup)
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


@router.post("/accuracy/update", status_code=200)
async def update_accuracy():
    """
    Resolve yesterday's predictions against actual game results.
    Called automatically on server startup and can be called manually.
    """
    import asyncio
    from app.services import nba_data

    db = get_db()
    yesterday = str(datetime.date.today() - datetime.timedelta(days=1))

    predictions = (
        db.table("predictions")
        .select("*")
        .eq("game_date", yesterday)
        .execute()
        .data
    )
    if not predictions:
        return {"updated": 0, "message": f"No predictions stored for {yesterday}"}

    try:
        games = await asyncio.to_thread(nba_data.get_todays_games, yesterday)
    except Exception as exc:
        return {"updated": 0, "message": f"Could not fetch results: {exc}"}

    actual_winners: dict[str, str] = {}
    for game in games:
        if game.get("status_id") == 3:
            home_pts = game.get("home_pts")
            away_pts = game.get("away_pts")
            if home_pts is not None and away_pts is not None:
                winner = (
                    game["home_team_name"] if home_pts > away_pts
                    else game["away_team_name"]
                )
                actual_winners[str(game["id"])] = winner

    if not actual_winners:
        return {"updated": 0, "message": "No finished games found for yesterday"}

    already_logged = {
        r["game_id"]
        for r in db.table("accuracy_log")
        .select("game_id")
        .in_("game_id", [p["game_id"] for p in predictions])
        .execute()
        .data
    }

    rows_to_insert = []
    for pred in predictions:
        gid = pred["game_id"]
        if gid in already_logged or gid not in actual_winners:
            continue
        rows_to_insert.append({
            "game_id": gid,
            "game_date": yesterday,
            "home_team": pred["home_team"],
            "away_team": pred["away_team"],
            "predicted_winner": pred["predicted_winner"],
            "actual_winner": actual_winners[gid],
            "correct": pred["predicted_winner"] == actual_winners[gid],
            "confidence": pred.get("confidence"),
            "timestamp": datetime.datetime.now(tz=timezone.utc).isoformat(),
        })

    if rows_to_insert:
        db.table("accuracy_log").insert(rows_to_insert).execute()

    return {
        "updated": len(rows_to_insert),
        "message": f"Resolved {len(rows_to_insert)} predictions for {yesterday}",
    }
