import json
import os
from datetime import datetime, timezone
from fastapi import APIRouter
from app.schemas.prediction import AccuracyStats

router = APIRouter(prefix="/api", tags=["accuracy"])

# Path to the JSON file that stores historical prediction outcomes
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
ACCURACY_LOG_PATH = os.path.join(DATA_DIR, "accuracy_log.json")


def _load_log() -> list[dict]:
    """Load the accuracy log from disk, returning an empty list on failure."""
    try:
        with open(ACCURACY_LOG_PATH, "r") as fh:
            data = json.load(fh)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


@router.get("/accuracy", response_model=AccuracyStats)
def get_accuracy():
    """Return historical model accuracy statistics."""
    log = _load_log()
    total = len(log)
    correct = sum(1 for entry in log if entry.get("correct") is True)
    accuracy_pct = round((correct / total * 100), 2) if total > 0 else 0.0
    last_updated = datetime.now(tz=timezone.utc).isoformat()

    # If we have logged entries, use the timestamp of the most recent one
    if log:
        timestamps = [e.get("timestamp", "") for e in log if e.get("timestamp")]
        if timestamps:
            last_updated = max(timestamps)

    return AccuracyStats(
        total_predictions=total,
        correct_predictions=correct,
        accuracy_percentage=accuracy_pct,
        last_updated=last_updated,
    )
