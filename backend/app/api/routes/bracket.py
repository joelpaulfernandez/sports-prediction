"""
Playoff bracket route.

WHAT THIS FILE DOES (in plain English)
──────────────────────────────────────
This builds the data behind the Bracket page on the frontend. It answers:

  • Which playoff series have happened or are in progress?
  • Who's ahead in each series? (e.g. "Thunder lead 2-0 vs Lakers")
  • Game-by-game, which prediction did we make and was it right?

The frontend turns this into the 4-column bracket layout you see, with green
✓ / red ✗ / gray dot badges for each game.

Output: JSON grouped by round (First Round → Conf Semis → Conf Finals → Finals),
with each round containing a list of series, and each series containing the
games played so far. Cached for 5 minutes so we don't hammer the NBA stats API.
"""

import asyncio
from typing import Optional

from fastapi import APIRouter

from app.services import nba_data
from app.services.cache import cache_get, cache_set
from app.services.db import get_db

router = APIRouter(prefix="/api", tags=["bracket"])

# NBA playoff structure: 8 first-round series, then 4 semis, 2 conf finals, 1 final.
ROUND_NAMES = ["First Round", "Conference Semifinals", "Conference Finals", "NBA Finals"]
ROUND_SIZES = [8, 4, 2, 1]


def _build_bracket(season: str = nba_data.CURRENT_SEASON) -> dict:
    """Assemble the complete bracket JSON the frontend renders."""
    # Fetch every playoff game played this season (one big stats API call).
    df = nba_data._fetch_all_playoff_games(season)
    if df is None or df.empty:
        return {"season": season, "rounds": []}

    # Pull every prediction we've made (across all dates) so we can join them
    # against the games below. Keyed by game_id for instant lookup.
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
        # If Supabase is unavailable, fall back to "no predictions on file" —
        # bracket still renders with gray dots for every game.
        print(f"[bracket] Could not load predictions: {exc}")

    # Also pull the live scoreboard. We need this for two reasons:
    #
    # 1. The stats endpoint (LeagueGameFinder) is slow to update right after
    #    a game ends — its WL column can still say the wrong team won for
    #    several minutes, and its PTS values may show partial scores. The
    #    live scoreboard is the source of truth for the final score.
    #
    # 2. To detect games that are CURRENTLY in progress so we don't mark them
    #    as predicted-wrong yet (the model might be picking the team that's
    #    currently trailing but ends up winning).
    live_lookup: dict[str, dict] = {}
    live_game_ids: set[str] = set()
    try:
        live_games = nba_data._games_from_live_scoreboard() or []
        for g in live_games:
            gid = str(g["id"])
            live_lookup[gid] = g
            if int(g.get("status_id", 1)) == 2:  # status_id 2 = "Live"
                live_game_ids.add(gid)
    except Exception as exc:
        print(f"[bracket] Could not load live scoreboard: {exc}")

    # Group games into series. Two teams playing each other multiple times
    # (e.g. Lakers vs Thunder games 1-7) form one series. We use a sorted
    # tuple of team IDs as the key so we don't accidentally split a series
    # based on which team was home.
    series_dict: dict[tuple[int, int], list] = {}
    for _, row in df.iterrows():
        key = tuple(sorted([int(row["TEAM_ID_home"]), int(row["TEAM_ID_away"])]))
        series_dict.setdefault(key, []).append(row)

    # ── For each series, build a structured object the frontend can render. ──
    series_list: list[dict] = []
    for series_key, rows in series_dict.items():
        # Sort the games chronologically so game 1 is first.
        rows_sorted = sorted(rows, key=lambda r: r["GAME_DATE"])
        first_game = rows_sorted[0]

        # By NBA convention, the higher-seeded team hosts game 1.
        # We use that to label the two teams as "higher seed" / "lower seed".
        higher_id = int(first_game["TEAM_ID_home"])
        lower_id = int(first_game["TEAM_ID_away"])
        higher_name = str(first_game["TEAM_NAME_home"])
        lower_name = str(first_game["TEAM_NAME_away"])

        # Running counts. We'll only increment these for FINISHED games.
        higher_wins = 0
        lower_wins = 0
        games: list[dict] = []

        for r in rows_sorted:
            game_id = str(r["GAME_ID"])
            home_id = int(r["TEAM_ID_home"])
            away_id = int(r["TEAM_ID_away"])
            is_live = game_id in live_game_ids  # True if game is still in progress

            # Pull the score. We try the live scoreboard FIRST (most current),
            # and fall back to the stats endpoint if live data isn't available.
            # _safe_int handles weird values like "N/A" or "" without crashing.
            live = live_lookup.get(game_id)
            home_pts: Optional[int] = None
            away_pts: Optional[int] = None
            if live and live.get("home_pts") is not None and live.get("away_pts") is not None:
                home_pts = _safe_int(live["home_pts"])
                away_pts = _safe_int(live["away_pts"])
            if home_pts is None or away_pts is None:
                home_pts = _safe_int(r.get("PTS_home"))
                away_pts = _safe_int(r.get("PTS_away"))

            # Decide who won by comparing points directly. We could use the
            # WL ("W"/"L") column from stats but that lags the actual buzzer.
            home_won = (
                home_pts > away_pts
                if home_pts is not None and away_pts is not None
                else None
            )

            # Resolve the actual winner only if the game is truly finished.
            # For live games we leave winner=None — the bracket badge will
            # show as a gray dot rather than committing to right/wrong.
            actual_winner_id: Optional[int] = None
            actual_winner_name: Optional[str] = None
            if not is_live and home_won is not None:
                actual_winner_id = home_id if home_won else away_id
                actual_winner_name = (
                    str(r["TEAM_NAME_home"]) if home_won else str(r["TEAM_NAME_away"])
                )

            # Bump the series score only when this game is fully decided.
            if actual_winner_id is not None:
                if actual_winner_id == higher_id:
                    higher_wins += 1
                else:
                    lower_wins += 1

            # Did we predict this game? Pull our stored prediction (if any).
            pred = pred_lookup.get(game_id)
            predicted_winner_name = pred.get("predicted_winner") if pred else None
            confidence = pred.get("confidence") if pred else None

            # The "correct" flag drives the green ✓ / red ✗ / gray dot badge.
            #   None  → no answer yet (live game OR no prediction on file)
            #   True  → we picked the right team
            #   False → we picked the loser
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

        # NBA playoff series are best-of-7. First team to 4 wins is the
        # series winner. If neither team has 4 yet, the series is ongoing.
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

    # ── Sort series by their start date and split into rounds. ──
    # NBA rounds run sequentially: all 8 first-round series start before
    # any second-round series starts. So we just sort by start date and
    # take the first 8 → first round, next 4 → semis, etc.
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
            break  # later rounds haven't started yet — stop

    # Top-of-page summary stats: total games played, how many we predicted,
    # how many we got right, and our hit rate.
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


def _safe_int(v) -> Optional[int]:
    """
    Defensive int() coercion. Live and stats endpoints occasionally return
    non-numeric placeholders ("N/A", "--", "") for missing scores; we'd
    rather treat those as "no score yet" than crash bracket rendering.
    """
    if v is None or _isnan(v):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None


@router.get("/bracket")
async def get_bracket():
    """Return the playoff bracket with prediction accuracy per game."""
    cache_key = "playoff_bracket_v5"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    bracket = await asyncio.to_thread(_build_bracket)
    cache_set(cache_key, bracket, ttl=300)
    return bracket
