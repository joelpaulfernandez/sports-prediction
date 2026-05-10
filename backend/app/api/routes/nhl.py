"""
NHL prediction API routes.

GET  /nhl/games              — today's games with predictions
GET  /nhl/games/{game_id}    — single game prediction
GET  /nhl/accuracy           — historical model accuracy
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.schemas.nhl_prediction import (
    NHLGamePrediction, NHLPredictionReason, NHLTeamStats, NHLAccuracyStats,
)
from app.services import nhl_data
from app.services.nhl_prediction_engine import predict_game
from app.services.cache import cache_get, cache_set

router = APIRouter(prefix="/nhl", tags=["nhl"])

_TTL_SCHEDULED = 300   # 5 min
_TTL_LIVE      = 30    # 30 s during live games


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/games", response_model=list[NHLGamePrediction])
async def get_nhl_games():
    """Return today's NHL games with win-probability predictions."""
    cached = cache_get("nhl:games:today")
    if cached is not None:
        return [NHLGamePrediction(**g) for g in cached]

    games = await asyncio.to_thread(_build_today_predictions)
    has_live = any(g["status"] == "live" for g in games)
    cache_set("nhl:games:today", games, _TTL_LIVE if has_live else _TTL_SCHEDULED)
    return [NHLGamePrediction(**g) for g in games]


@router.get("/games/{game_id}", response_model=NHLGamePrediction)
async def get_nhl_game(game_id: str):
    """Return prediction for a single NHL game."""
    games = await get_nhl_games()
    match = next((g for g in games if g.game_id == game_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found.")
    return match


@router.get("/accuracy", response_model=NHLAccuracyStats)
async def get_nhl_accuracy():
    """Return historical NHL model accuracy from Supabase."""
    return await asyncio.to_thread(_compute_accuracy)


# ---------------------------------------------------------------------------
# Prediction builder
# ---------------------------------------------------------------------------

def _build_today_predictions() -> list[dict]:
    schedule = nhl_data.get_today_schedule()
    standings = nhl_data.get_standings()

    predictions = []
    for game in schedule:
        home_abbrev = game["home_team_abbrev"]
        away_abbrev = game["away_team_abbrev"]

        home_stats = standings.get(home_abbrev)
        away_stats = standings.get(away_abbrev)

        if home_stats and away_stats:
            result = predict_game(home_stats, away_stats)
            home_win_prob     = result["home_win_prob"]
            confidence        = result["confidence"]
            model_confidence  = result["model_confidence"]
            reasons           = result["reasons"]
            model_version     = result["model_version"]
        else:
            home_win_prob    = 0.54   # raw home ice baseline
            confidence       = 20
            model_confidence = "low"
            reasons          = [f"{game['home_team_full'] or home_abbrev} has home ice advantage."]
            model_version    = "nhl-stats-v1"

        predicted_winner        = game["home_team_full"] if home_win_prob >= 0.5 else game["away_team_full"]
        predicted_winner_abbrev = home_abbrev if home_win_prob >= 0.5 else away_abbrev

        predictions.append({
            "game_id":                 game["game_id"],
            "home_team":               game["home_team_full"] or game["home_team"],
            "home_team_abbrev":        home_abbrev,
            "away_team":               game["away_team_full"] or game["away_team"],
            "away_team_abbrev":        away_abbrev,
            "game_date":               game["game_date"],
            "game_time_utc":           game["game_time_utc"],
            "status":                  game["status"],
            "predicted_winner":        predicted_winner,
            "predicted_winner_abbrev": predicted_winner_abbrev,
            "home_win_prob":           home_win_prob,
            "confidence":              confidence,
            "model_confidence":        model_confidence,
            "reasons":                 [{"text": r} for r in reasons],
            "home_stats":              _to_team_stats(home_stats) if home_stats else None,
            "away_stats":              _to_team_stats(away_stats) if away_stats else None,
            "home_score":              game.get("home_score"),
            "away_score":              game.get("away_score"),
            "model_version":           model_version,
        })

    return predictions


def _to_team_stats(s: dict) -> dict:
    return {
        "wins":                   s.get("wins", 0),
        "losses":                 s.get("losses", 0),
        "ot_losses":              s.get("ot_losses", 0),
        "points":                 s.get("points", 0),
        "points_pct":             s.get("points_pct", 0.0),
        "goals_for_per_game":     s.get("goals_for_per_game", 0.0),
        "goals_against_per_game": s.get("goals_against_per_game", 0.0),
        "pp_pct":                 s.get("pp_pct", 0.0),
        "pk_pct":                 s.get("pk_pct", 0.0),
        "save_pct":               s.get("save_pct", 0.0),
        "shots_for_per_game":     s.get("shots_for_per_game", 0.0),
        "shots_against_per_game": s.get("shots_against_per_game", 0.0),
    }


# ---------------------------------------------------------------------------
# Accuracy
# ---------------------------------------------------------------------------

def _compute_accuracy() -> NHLAccuracyStats:
    try:
        from app.services.db import get_db
        db = get_db()
        rows = db.table("nhl_accuracy_log").select("*").execute().data or []
    except Exception:
        rows = []

    total = len(rows)
    correct = sum(1 for r in rows if r.get("winner_correct", False))
    return NHLAccuracyStats(
        total_predictions=total,
        correct_predictions=correct,
        accuracy_percentage=round(correct / total * 100, 1) if total else 0.0,
        last_updated=datetime.now(tz=timezone.utc).isoformat(),
        backtest_accuracy=0.586,
        backtest_games=1324,
    )
