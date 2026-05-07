"""
Predictions API routes.

All data fetching from stats.nba.com is offloaded to threads via
asyncio.to_thread() so the FastAPI event loop is never blocked.
"""

import asyncio
from datetime import date, datetime, timezone

import pandas as pd
from fastapi import APIRouter, HTTPException

from app.schemas.prediction import GamePrediction, PredictionReason, TeamStats
from app.services import nba_data
from app.services.elo import EloSystem
from app.services.explainability import generate_reasons
from app.services.prediction_engine import get_prediction_engine

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

# In-process cache keyed by game_id (refreshed each call to /games)
_prediction_cache: dict[str, GamePrediction] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _game_status(status_id: int) -> str:
    if status_id == 2:
        return "live"
    if status_id == 3:
        return "finished"
    return "scheduled"


def _build_team_stats(stats: dict, recent: dict, elo: float, rest: int) -> TeamStats:
    def g(d, k, default=0.0):
        try:
            return float(d.get(k, default) or default)
        except (TypeError, ValueError):
            return default

    return TeamStats(
        net_rating=g(stats, "net_rating"),
        off_rating=g(stats, "off_rating", 110.0),
        def_rating=g(stats, "def_rating", 110.0),
        efg_pct=g(stats, "efg_pct", 0.52),
        tov_pct=g(stats, "tov_pct", 13.0),
        oreb_pct=g(stats, "oreb_pct", 0.25),
        w_pct=g(stats, "w_pct", 0.5),
        elo=round(elo, 1),
        recent_win_pct=g(recent, "recent_win_pct", g(stats, "w_pct", 0.5)),
        recent_net_rtg=g(recent, "recent_net_rtg", g(stats, "net_rating")),
        rest_days=rest,
    )


def _persist_prediction(prediction: GamePrediction, game_date: str) -> None:
    """Store prediction in Supabase so accuracy can be checked once the game ends."""
    try:
        from app.services.db import get_db
        db = get_db()
        db.table("predictions").upsert(
            {
                "game_id": prediction.game_id,
                "game_date": game_date,
                "home_team": prediction.home_team,
                "away_team": prediction.away_team,
                "predicted_winner": prediction.predicted_winner,
                "confidence": prediction.confidence,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
            on_conflict="game_id",
        ).execute()
    except Exception as exc:
        print(f"[predictions] Could not persist prediction: {exc}")


async def _build_prediction(
    game: dict,
    team_stats: dict,
    elo_ratings: dict,
    game_log: pd.DataFrame,
) -> GamePrediction:
    home_id = game["home_team_id"]
    away_id = game["away_team_id"]
    home_name = game["home_team_name"]
    away_name = game["away_team_name"]
    game_date = game["date"]

    h_stats = team_stats.get(home_id, {})
    a_stats = team_stats.get(away_id, {})

    # Recent form (computed in thread to avoid blocking)
    h_recent, a_recent = await asyncio.gather(
        asyncio.to_thread(nba_data.compute_team_recent_form, home_id, game_log, 10),
        asyncio.to_thread(nba_data.compute_team_recent_form, away_id, game_log, 10),
    )

    h_rest = nba_data.compute_rest_days(h_recent.get("last_game_date"), game_date)
    a_rest = nba_data.compute_rest_days(a_recent.get("last_game_date"), game_date)

    h_elo = float(elo_ratings.get(home_id, 1500.0))
    a_elo = float(elo_ratings.get(away_id, 1500.0))

    # NBA playoff game IDs have '4' at index 2 (e.g. "0042501001")
    is_playoff = str(game["id"])[2:3] == "4"

    engine = get_prediction_engine()
    result = engine.generate_prediction(
        h_stats, a_stats,
        h_recent, a_recent,
        h_elo, a_elo,
        h_rest, a_rest,
        is_playoff=is_playoff,
    )

    predicted_winner = home_name if result["predicted_winner_is_home"] else away_name

    reason_texts = generate_reasons(
        home_team=home_name,
        away_team=away_name,
        home_stats=h_stats,
        away_stats=a_stats,
        home_recent=h_recent,
        away_recent=a_recent,
        home_elo=h_elo,
        away_elo=a_elo,
        home_rest=h_rest,
        away_rest=a_rest,
        predicted_winner=predicted_winner,
    )

    return GamePrediction(
        game_id=str(game["id"]),
        home_team=home_name,
        away_team=away_name,
        predicted_winner=predicted_winner,
        confidence=result["confidence"],
        predicted_home_score=result["predicted_home_score"],
        predicted_away_score=result["predicted_away_score"],
        reasons=[PredictionReason(text=t) for t in reason_texts],
        game_date=game_date,
        status=_game_status(game.get("status_id", 1)),
        home_pts=game.get("home_pts"),
        away_pts=game.get("away_pts"),
        home_stats=_build_team_stats(h_stats, h_recent, h_elo, h_rest),
        away_stats=_build_team_stats(a_stats, a_recent, a_elo, a_rest),
        model_version=engine.model_version,
    )


async def _fetch_shared_data() -> tuple[dict, dict, pd.DataFrame]:
    """Fetch team stats and game log concurrently (both are cached after first call)."""
    team_stats, game_log = await asyncio.gather(
        asyncio.to_thread(nba_data.get_all_team_stats),
        asyncio.to_thread(nba_data.get_full_season_log),
    )

    elo_ratings: dict[int, float] = {}
    if game_log is not None and not game_log.empty:
        elo_sys = EloSystem()
        await asyncio.to_thread(elo_sys.process_game_log, game_log)
        elo_ratings = elo_sys.ratings

    if game_log is None:
        game_log = pd.DataFrame()

    return team_stats, elo_ratings, game_log


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/games", response_model=list[GamePrediction])
async def get_games():
    """Return ML-powered predictions for all NBA games scheduled today."""
    global _prediction_cache

    today = str(date.today())

    # Fetch today's schedule + shared data concurrently
    games_coro = asyncio.to_thread(nba_data.get_todays_games, today)
    shared_coro = _fetch_shared_data()

    games, (team_stats, elo_ratings, game_log) = await asyncio.gather(
        games_coro, shared_coro
    )

    _prediction_cache = {}
    predictions: list[GamePrediction] = []

    for game in games:
        try:
            pred = await _build_prediction(game, team_stats, elo_ratings, game_log)
            _prediction_cache[pred.game_id] = pred
            _persist_prediction(pred, today)
            predictions.append(pred)
        except Exception as exc:
            print(f"[predictions] Skipping game {game.get('id')}: {exc}")

    return predictions


@router.get("/games/{game_id}", response_model=GamePrediction)
async def get_game(game_id: str):
    """Return the prediction for a single game."""
    if game_id in _prediction_cache:
        return _prediction_cache[game_id]

    today = str(date.today())
    games = await asyncio.to_thread(nba_data.get_todays_games, today)

    for game in games:
        if str(game["id"]) == game_id:
            team_stats, elo_ratings, game_log = await _fetch_shared_data()
            pred = await _build_prediction(game, team_stats, elo_ratings, game_log)
            _prediction_cache[game_id] = pred
            return pred

    raise HTTPException(status_code=404, detail=f"Game {game_id} not found for today.")
