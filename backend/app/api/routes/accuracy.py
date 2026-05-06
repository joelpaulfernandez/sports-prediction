"""
Accuracy tracking route.

GET  /api/accuracy          — return historical accuracy stats
POST /api/accuracy/update   — check yesterday's predictions against actual results
                               and update the accuracy log (called from startup)
"""

import json
import os
import datetime
from datetime import timezone

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.prediction import AccuracyStats
from app.services.prediction_engine import get_prediction_engine

router = APIRouter(prefix="/api", tags=["accuracy"])


def _load_json(path: str, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


@router.get("/accuracy", response_model=AccuracyStats)
def get_accuracy():
    """Return historical model accuracy statistics."""
    settings = get_settings()
    log: list[dict] = _load_json(settings.accuracy_log_path, [])

    total = len(log)
    correct = sum(1 for e in log if e.get("correct") is True)
    accuracy_pct = round(correct / total * 100, 2) if total > 0 else 0.0

    last_updated = datetime.datetime.now(tz=timezone.utc).isoformat()
    timestamps = [e.get("timestamp", "") for e in log if e.get("timestamp")]
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

    settings = get_settings()
    yesterday = str(datetime.date.today() - datetime.timedelta(days=1))

    pred_log: dict = _load_json(settings.predictions_log_path, {})
    if yesterday not in pred_log:
        return {"updated": 0, "message": f"No predictions stored for {yesterday}"}

    predictions = pred_log[yesterday]
    if not predictions:
        return {"updated": 0, "message": "No predictions to resolve"}

    # Fetch yesterday's game results
    try:
        games = await asyncio.to_thread(nba_data.get_todays_games, yesterday)
    except Exception as exc:
        return {"updated": 0, "message": f"Could not fetch results: {exc}"}

    # Build lookup: game_id → actual winner name
    actual_winners: dict[str, str] = {}
    for game in games:
        if game.get("status_id") == 3:  # finished
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

    acc_log: list[dict] = _load_json(settings.accuracy_log_path, [])
    already_logged = {e["game_id"] for e in acc_log}

    added = 0
    for pred in predictions:
        gid = pred["game_id"]
        if gid in already_logged or gid not in actual_winners:
            continue

        actual = actual_winners[gid]
        correct = pred["predicted_winner"] == actual

        acc_log.append({
            "game_id": gid,
            "game_date": yesterday,
            "home_team": pred["home_team"],
            "away_team": pred["away_team"],
            "predicted_winner": pred["predicted_winner"],
            "actual_winner": actual,
            "correct": correct,
            "confidence": pred.get("confidence"),
            "timestamp": datetime.datetime.now(tz=timezone.utc).isoformat(),
        })
        added += 1

    if added > 0:
        _save_json(settings.accuracy_log_path, acc_log)

    return {"updated": added, "message": f"Resolved {added} predictions for {yesterday}"}
