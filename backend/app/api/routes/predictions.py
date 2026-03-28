from datetime import date
from fastapi import APIRouter, HTTPException

from app.schemas.prediction import GamePrediction, PredictionReason
from app.services import sports_api
from app.services.prediction_engine import get_prediction_engine
from app.services.explainability import generate_reasons

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

# In-memory cache for the current request cycle (keyed by game_id)
_prediction_cache: dict[str, GamePrediction] = {}


def _map_status(api_status: str) -> str:
    """Map api-sports status codes to our internal status strings."""
    live_codes = {"LIVE", "HT", "Q1", "Q2", "Q3", "Q4", "OT", "BT", "P"}
    finished_codes = {"FT", "AOT", "POST", "CANC", "SUSP", "AWD", "WO"}
    if api_status.upper() in live_codes:
        return "live"
    if api_status.upper() in finished_codes:
        return "finished"
    return "scheduled"


async def _build_prediction(game: dict) -> GamePrediction:
    home_info = game["teams"]["home"]
    away_info = game["teams"]["away"]
    home_team = home_info["name"]
    away_team = away_info["name"]
    game_id = str(game["id"])

    # Fetch team stats (falls back to mock data if API is unavailable)
    home_stats = await sports_api.get_team_stats(home_info["id"])
    away_stats = await sports_api.get_team_stats(away_info["id"])

    engine = get_prediction_engine()
    result = engine.generate_prediction(home_stats, away_stats)

    predicted_winner = home_team if result["predicted_winner_is_home"] else away_team

    reason_texts = generate_reasons(
        home_team=home_team,
        away_team=away_team,
        home_stats=home_stats,
        away_stats=away_stats,
        predicted_winner=predicted_winner,
    )
    reasons = [PredictionReason(text=t) for t in reason_texts]

    raw_status = game.get("status", {}).get("short", "NS")
    status = _map_status(raw_status)

    game_date = str(game.get("date", str(date.today())))[:10]

    return GamePrediction(
        game_id=game_id,
        home_team=home_team,
        away_team=away_team,
        predicted_winner=predicted_winner,
        confidence=result["confidence"],
        predicted_home_score=result["predicted_home_score"],
        predicted_away_score=result["predicted_away_score"],
        reasons=reasons,
        game_date=game_date,
        status=status,
    )


@router.get("/games", response_model=list[GamePrediction])
async def get_games():
    """Return predictions for all NBA games scheduled today."""
    global _prediction_cache
    today = str(date.today())
    games = await sports_api.get_upcoming_games(today)

    predictions: list[GamePrediction] = []
    _prediction_cache = {}

    for game in games:
        try:
            prediction = await _build_prediction(game)
            _prediction_cache[prediction.game_id] = prediction
            predictions.append(prediction)
        except Exception as exc:
            # Log and skip malformed game entries
            print(f"Error building prediction for game {game.get('id')}: {exc}")
            continue

    return predictions


@router.get("/games/{game_id}", response_model=GamePrediction)
async def get_game(game_id: str):
    """Return the prediction for a single NBA game."""
    # Try the cache first
    if game_id in _prediction_cache:
        return _prediction_cache[game_id]

    # Re-fetch today's games and find the matching one
    today = str(date.today())
    games = await sports_api.get_upcoming_games(today)

    for game in games:
        if str(game["id"]) == game_id:
            prediction = await _build_prediction(game)
            _prediction_cache[game_id] = prediction
            return prediction

    raise HTTPException(status_code=404, detail=f"Game {game_id} not found for today.")
