"""
Predictions API routes.

All NBA data fetching is pre-warmed in the background at startup and refreshed
on a schedule. Route handlers serve from an in-memory cache and return in < 100 ms.
"""

import asyncio
from datetime import date, datetime, timezone
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.schemas.prediction import GamePrediction, PredictionReason, TeamStats
from app.services import nba_data
from app.services.elo import EloSystem
from app.services.explainability import generate_reasons
from app.services.prediction_engine import get_prediction_engine

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

# ---------------------------------------------------------------------------
# Warmed prediction cache
# ---------------------------------------------------------------------------

# Keyed by local date string (YYYY-MM-DD).  Populated by warm_predictions().
_cache: dict[str, list[GamePrediction]] = {}
_cache_built_at: dict[str, datetime] = {}
_warm_lock = asyncio.Lock()


def _ttl_seconds(predictions: list[GamePrediction]) -> int:
    """Short TTL during live games, longer when all games are scheduled/final."""
    if any(p.status == "live" for p in predictions):
        return 30
    return 300  # 5 minutes for scheduled / finished


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

    h_recent, a_recent = await asyncio.gather(
        asyncio.to_thread(nba_data.compute_team_recent_form, home_id, game_log, 10),
        asyncio.to_thread(nba_data.compute_team_recent_form, away_id, game_log, 10),
    )

    h_rest = nba_data.compute_rest_days(h_recent.get("last_game_date"), game_date)
    a_rest = nba_data.compute_rest_days(a_recent.get("last_game_date"), game_date)

    h_elo = float(elo_ratings.get(home_id, 1500.0))
    a_elo = float(elo_ratings.get(away_id, 1500.0))

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
        home_team_id=home_id,
        away_team_id=away_id,
        predicted_winner=predicted_winner,
        confidence=result["confidence"],
        predicted_home_score=result["predicted_home_score"],
        predicted_away_score=result["predicted_away_score"],
        reasons=[PredictionReason(text=t) for t in reason_texts],
        game_date=game_date,
        status=_game_status(game.get("status_id", 1)),
        home_pts=game.get("home_pts"),
        away_pts=game.get("away_pts"),
        game_time_utc=game.get("game_time_utc"),
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
# Warming — called at startup and on a schedule
# ---------------------------------------------------------------------------

async def warm_predictions(today: str | None = None) -> list[GamePrediction]:
    """
    Build predictions for `today` and store them in the in-memory cache.
    Subsequent calls to GET /games return from this cache in < 100 ms.
    Safe to call concurrently — only one build runs at a time per date.
    """
    async with _warm_lock:
        today = today or str(date.today())

        # Skip if the cached result is still fresh
        if today in _cache:
            age = (datetime.now(timezone.utc) - _cache_built_at[today]).total_seconds()
            if age < _ttl_seconds(_cache[today]):
                return _cache[today]

        print(f"[warming] Building predictions for {today}…")
        try:
            games = await asyncio.to_thread(nba_data.get_todays_games, today)
            team_stats, elo_ratings, game_log = await _fetch_shared_data()

            predictions: list[GamePrediction] = []
            for game in games:
                try:
                    pred = await _build_prediction(game, team_stats, elo_ratings, game_log)
                    _persist_prediction(pred, today)
                    predictions.append(pred)
                except Exception as exc:
                    print(f"[warming] Skipping game {game.get('id')}: {exc}")

            _cache[today] = predictions
            _cache_built_at[today] = datetime.now(timezone.utc)
            print(f"[warming] Done — {len(predictions)} prediction(s) cached for {today}.")
            return predictions

        except Exception as exc:
            print(f"[warming] Failed: {exc}")
            return _cache.get(today, [])  # return stale rather than nothing


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/games", response_model=list[GamePrediction])
async def get_games(date: Optional[str] = Query(default=None, description="Client local date YYYY-MM-DD")):
    """Return ML-powered predictions for today's NBA games. Served from cache."""
    today = date or str(__import__("datetime").date.today())

    # Return cache immediately if it exists (even if stale — background will refresh)
    if today in _cache and _cache[today]:
        stale = (datetime.now(timezone.utc) - _cache_built_at[today]).total_seconds() > _ttl_seconds(_cache[today])
        if stale:
            # Refresh in background, serve stale now
            asyncio.create_task(warm_predictions(today))
        return _cache[today]

    # Cache is empty — compute now (only happens on first request after cold start
    # if startup warming hasn't finished yet)
    return await warm_predictions(today)


@router.get("/games/{game_id}", response_model=GamePrediction)
async def get_game(game_id: str):
    """Return the prediction for a single game."""
    today = str(date.today())

    # Check warmed cache first
    for pred in _cache.get(today, []):
        if pred.game_id == game_id:
            return pred

    # Fall back to computing just this game
    games = await asyncio.to_thread(nba_data.get_todays_games, today)
    for game in games:
        if str(game["id"]) == game_id:
            team_stats, elo_ratings, game_log = await _fetch_shared_data()
            pred = await _build_prediction(game, team_stats, elo_ratings, game_log)
            return pred

    raise HTTPException(status_code=404, detail=f"Game {game_id} not found for today.")
