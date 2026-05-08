"""
Playoff bracket route.

GET /api/bracket  Returns the 2025-26 NBA playoff bracket structured by round,
                  with each game annotated by our prediction (correct/wrong/none).
"""

import asyncio
from typing import Optional

from fastapi import APIRouter

from app.services import nba_data
from app.services.cache import cache_get, cache_set
from app.services.db import get_db

router = APIRouter(prefix="/api", tags=["bracket"])

ROUND_NAMES = ["First Round", "Conference Semifinals", "Conference Finals", "NBA Finals"]
ROUND_SIZES = [8, 4, 2, 1]  # number of series per round


def _build_bracket(season: str = nba_data.CURRENT_SEASON) -> dict:
    df = nba_data._fetch_all_playoff_games(season)
    if df is None or df.empty:
        return {"season": season, "rounds": []}

    # Pull all our stored predictions for this season
    pred_lookup: dict[str, dict] = {}
    try:
        rows = (
            get_db()
            .table("predictions")
            .select("game_id,predicted_winner,confidence")
            .execute()
            .data
        )
        pred_lookup = {r["game_id"]: r for r in rows}
    except Exception as exc:
        print(f"[bracket] Could not load predictions: {exc}")

    # Cross-reference with the live scoreboard. LeagueGameFinder lags real
    # game-end by several minutes — its WL and PTS columns may still hold
    # provisional values right after a buzzer. The live scoreboard is the
    # ground truth for status and current/final scores.
    live_lookup: dict[str, dict] = {}
    live_game_ids: set[str] = set()
    try:
        live_games = nba_data._games_from_live_scoreboard() or []
        for g in live_games:
            gid = str(g["id"])
            live_lookup[gid] = g
            if int(g.get("status_id", 1)) == 2:
                live_game_ids.add(gid)
    except Exception as exc:
        print(f"[bracket] Could not load live scoreboard: {exc}")

    # Group games by series (sorted team-id pair as key)
    series_dict: dict[tuple[int, int], list] = {}
    for _, row in df.iterrows():
        key = tuple(sorted([int(row["TEAM_ID_home"]), int(row["TEAM_ID_away"])]))
        series_dict.setdefault(key, []).append(row)

    # Build series objects
    series_list: list[dict] = []
    for series_key, rows in series_dict.items():
        rows_sorted = sorted(rows, key=lambda r: r["GAME_DATE"])
        first_game = rows_sorted[0]

        # Higher seed = home team in game 1 (NBA seeding rule)
        higher_id = int(first_game["TEAM_ID_home"])
        lower_id = int(first_game["TEAM_ID_away"])
        higher_name = str(first_game["TEAM_NAME_home"])
        lower_name = str(first_game["TEAM_NAME_away"])

        higher_wins = 0
        lower_wins = 0
        games: list[dict] = []

        for r in rows_sorted:
            game_id = str(r["GAME_ID"])
            home_id = int(r["TEAM_ID_home"])
            away_id = int(r["TEAM_ID_away"])
            is_live = game_id in live_game_ids

            # Prefer live scoreboard scores when available — LeagueGameFinder
            # holds stale Q3/Q4 partials for several minutes post-buzzer.
            live = live_lookup.get(game_id)
            if live and live.get("home_pts") is not None and live.get("away_pts") is not None:
                home_pts = int(live["home_pts"])
                away_pts = int(live["away_pts"])
            else:
                home_pts = int(r["PTS_home"]) if not _isnan(r.get("PTS_home")) else None
                away_pts = int(r["PTS_away"]) if not _isnan(r.get("PTS_away")) else None

            # Determine winner from points rather than the WL column. WL can lag
            # the box score by several minutes for just-finished games.
            home_won = (
                home_pts > away_pts
                if home_pts is not None and away_pts is not None
                else None
            )

            actual_winner_id: Optional[int] = None
            actual_winner_name: Optional[str] = None
            if not is_live and home_won is not None:
                actual_winner_id = home_id if home_won else away_id
                actual_winner_name = (
                    str(r["TEAM_NAME_home"]) if home_won else str(r["TEAM_NAME_away"])
                )

            # Only count completed games toward the series score
            if actual_winner_id is not None:
                if actual_winner_id == higher_id:
                    higher_wins += 1
                else:
                    lower_wins += 1

            pred = pred_lookup.get(game_id)
            predicted_winner_name = pred.get("predicted_winner") if pred else None
            confidence = pred.get("confidence") if pred else None

            correct: Optional[bool]
            if is_live or predicted_winner_name is None or actual_winner_name is None:
                correct = None
            else:
                correct = predicted_winner_name == actual_winner_name

            games.append({
                "game_id": game_id,
                "date": str(r["GAME_DATE"].date()),
                "home_team_id": home_id,
                "away_team_id": int(r["TEAM_ID_away"]),
                "home_team_name": str(r["TEAM_NAME_home"]),
                "away_team_name": str(r["TEAM_NAME_away"]),
                "home_pts": home_pts,
                "away_pts": away_pts,
                "actual_winner_id": actual_winner_id,
                "predicted_winner_name": predicted_winner_name,
                "confidence": float(confidence) if confidence is not None else None,
                "correct": correct,
            })

        series_winner_id = (
            higher_id if higher_wins >= 4 else (lower_id if lower_wins >= 4 else None)
        )

        series_list.append({
            "first_game_date": str(rows_sorted[0]["GAME_DATE"].date()),
            "higher_seed": {
                "team_id": higher_id,
                "team_name": higher_name,
                "wins": higher_wins,
            },
            "lower_seed": {
                "team_id": lower_id,
                "team_name": lower_name,
                "wins": lower_wins,
            },
            "winner_team_id": series_winner_id,
            "games": games,
        })

    # Assign rounds based on first-game-date ordering (NBA rounds happen sequentially)
    series_list.sort(key=lambda s: s["first_game_date"])

    rounds: list[dict] = []
    idx = 0
    for round_num, size in enumerate(ROUND_SIZES):
        bucket = series_list[idx : idx + size]
        idx += size
        rounds.append({
            "name": ROUND_NAMES[round_num],
            "round_number": round_num + 1,
            "series": bucket,
        })
        if idx >= len(series_list):
            break

    # Compute prediction accuracy across the bracket
    all_games = [g for s in series_list for g in s["games"]]
    total_with_pred = sum(1 for g in all_games if g["correct"] is not None)
    correct = sum(1 for g in all_games if g["correct"] is True)

    return {
        "season": season,
        "rounds": rounds,
        "summary": {
            "total_games": len(all_games),
            "games_with_prediction": total_with_pred,
            "correct_predictions": correct,
            "accuracy_pct": round(correct / total_with_pred * 100, 1) if total_with_pred else 0.0,
        },
    }


def _isnan(v) -> bool:
    try:
        import math
        return v is None or (isinstance(v, float) and math.isnan(v))
    except Exception:
        return v is None


@router.get("/bracket")
async def get_bracket():
    """Return the playoff bracket with prediction accuracy per game."""
    cache_key = "playoff_bracket_v4"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    bracket = await asyncio.to_thread(_build_bracket)
    cache_set(cache_key, bracket, ttl=300)
    return bracket
