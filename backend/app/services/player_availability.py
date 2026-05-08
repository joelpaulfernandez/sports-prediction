"""
Player availability features.

Three rotation-strength signals are derived per team, computed from the team's
last N games before the game being predicted (leakage-safe for training):

  • star_minutes_ratio   share of total minutes played by the season's top
                         scorer. Drops to ~0 when the star is out.
  • top3_minutes_ratio   same for the top 3 scorers combined.
  • rotation_size        number of distinct players averaging 15+ MPG.

Designed for batch use: a `SeasonAvailability` object precomputes everything
heavy once per season, then `get_features(team_id, before_date)` is a fast
in-memory lookup. Training can build one of these per season and reuse it
across thousands of games.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from app.services.cache import cache_get as _cache_get, cache_set as _cache_set


# ---------------------------------------------------------------------------
# Raw data fetch (cached)
# ---------------------------------------------------------------------------

def _season_player_log(season: str, season_type: str = "Regular Season") -> Optional[pd.DataFrame]:
    """Fetch every player-game row for `season`. Cached for 4 hours."""
    cache_key = f"player_log_{season}_{season_type}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        from nba_api.stats.endpoints import leaguegamelog
        df = leaguegamelog.LeagueGameLog(
            season=season,
            player_or_team_abbreviation="P",
            season_type_all_star=season_type,
        ).get_data_frames()[0]
        if df.empty:
            return df
        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
        df["MIN"] = pd.to_numeric(df["MIN"], errors="coerce").fillna(0)
        df["PTS"] = pd.to_numeric(df["PTS"], errors="coerce").fillna(0)
        # Cache for 4 hours so a single training run never re-fetches mid-flight
        _cache_set(cache_key, df, ttl=14400)
        return df
    except Exception as exc:
        print(f"[player_availability] LeagueGameLog ({season}, {season_type}) error: {exc}")
        return None


def _full_season_player_log(season: str) -> pd.DataFrame:
    """Combined regular-season + playoff per-player game log."""
    reg = _season_player_log(season, "Regular Season")
    playoffs = _season_player_log(season, "Playoffs")
    parts = [df for df in (reg, playoffs) if df is not None and not df.empty]
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True).sort_values("GAME_DATE").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

def _default_features() -> dict:
    """Sensible neutral defaults when data is unavailable."""
    return {
        "star_minutes_ratio": 0.20,
        "top3_minutes_ratio": 0.45,
        "rotation_size": 9,
    }


# ---------------------------------------------------------------------------
# Batch precomputation (used by trainer + inference)
# ---------------------------------------------------------------------------

class SeasonAvailability:
    """
    Build once per season, query many times. The expensive operations
    (network fetch, top-scorer identification, sorting) happen in __init__;
    `get_features()` is then a fast in-memory lookup.
    """

    def __init__(self, season: str):
        self.season = season
        log = _full_season_player_log(season)

        # Per-team cached data
        self._team_logs: dict[int, pd.DataFrame] = {}
        self._top1: dict[int, set[int]] = {}
        self._top3: dict[int, set[int]] = {}

        if log.empty:
            return

        for team_id, team_log in log.groupby("TEAM_ID"):
            team_log = team_log.sort_values("GAME_DATE")
            self._team_logs[int(team_id)] = team_log

            by_player = team_log.groupby("PLAYER_ID")["PTS"].sum().sort_values(ascending=False)
            top_player_ids = list(by_player.head(3).index)
            self._top1[int(team_id)] = {int(top_player_ids[0])} if top_player_ids else set()
            self._top3[int(team_id)] = {int(p) for p in top_player_ids}

    def get_features(
        self,
        team_id: int,
        before_date: Optional[str] = None,
        n_games: int = 3,
    ) -> dict:
        team_log = self._team_logs.get(int(team_id))
        if team_log is None or team_log.empty:
            return _default_features()

        if before_date:
            cutoff = pd.Timestamp(before_date)
            team_log = team_log[team_log["GAME_DATE"] < cutoff]

        if team_log.empty:
            return _default_features()

        last_games = (
            team_log.groupby("GAME_ID")["GAME_DATE"]
            .max()
            .sort_values(ascending=False)
            .head(n_games)
            .index.tolist()
        )
        recent = team_log[team_log["GAME_ID"].isin(last_games)]
        if recent.empty:
            return _default_features()

        total_minutes = float(recent["MIN"].sum())
        if total_minutes <= 0:
            return _default_features()

        top1_set = self._top1.get(int(team_id), set())
        top3_set = self._top3.get(int(team_id), set())

        star_minutes = float(recent[recent["PLAYER_ID"].isin(top1_set)]["MIN"].sum())
        top3_minutes = float(recent[recent["PLAYER_ID"].isin(top3_set)]["MIN"].sum())

        by_player = (
            recent.groupby("PLAYER_ID")["MIN"]
            .agg(["sum", "count"])
            .assign(mpg=lambda d: d["sum"] / d["count"])
        )
        rotation_size = int((by_player["mpg"] >= 15).sum())

        return {
            "star_minutes_ratio": star_minutes / total_minutes,
            "top3_minutes_ratio": top3_minutes / total_minutes,
            "rotation_size": rotation_size,
        }


# Module-level cache of SeasonAvailability instances
_season_cache: dict[str, SeasonAvailability] = {}


def get_season_availability(season: str) -> SeasonAvailability:
    """Return a cached SeasonAvailability for `season`, building it if needed."""
    if season not in _season_cache:
        _season_cache[season] = SeasonAvailability(season)
    return _season_cache[season]


# ---------------------------------------------------------------------------
# Convenience wrapper for the inference path (one-off calls)
# ---------------------------------------------------------------------------

def compute_team_availability(
    team_id: int,
    season: str = "2025-26",
    before_date: Optional[str] = None,
    n_games: int = 3,
) -> dict:
    """One-off lookup that uses the cached SeasonAvailability under the hood."""
    return get_season_availability(season).get_features(team_id, before_date, n_games)
