"""
Player availability features.

The model used to be blind to injuries — if a star player was out, predictions
were unchanged. This module computes "rotation strength" features from recent
game logs that act as a proxy for injury status without scraping injury reports.

Three signals are derived per team, computed from the team's last N games before
the game being predicted (so it is leakage-safe for training):

  • star_minutes_ratio   — share of total minutes played by the season-long top
                           scorer. Drops to ~0 when the star is out.
  • top3_minutes_ratio   — same for the top 3 scorers combined. Captures depth
                           injuries (e.g. one of three stars hurt).
  • rotation_size        — number of distinct players who played 15+ MPG. Stays
                           around 8-10 for healthy teams; drops on injuries.
"""

from __future__ import annotations

import datetime
from typing import Optional

import pandas as pd

from app.services.cache import cache_get as _cache_get, cache_set as _cache_set


def _season_player_log(season: str, season_type: str = "Regular Season") -> Optional[pd.DataFrame]:
    """Fetch every player-game row for `season`. Cached for 30 minutes."""
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
        _cache_set(cache_key, df, ttl=1800)
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


def _identify_top_scorers(team_log: pd.DataFrame, top_n: int = 3) -> list[int]:
    """Top-N players by total points scored across the data we have."""
    if team_log.empty:
        return []
    by_player = team_log.groupby("PLAYER_ID")["PTS"].sum().sort_values(ascending=False)
    return [int(pid) for pid in by_player.head(top_n).index]


def compute_team_availability(
    team_id: int,
    season: str = "2025-26",
    before_date: Optional[str] = None,
    n_games: int = 3,
) -> dict:
    """
    Return rotation/availability features for `team_id` heading into the next game.

    `before_date` is exclusive — only games strictly before this date are used,
    so this is safe to call from training code (no leakage from the game being
    predicted).
    """
    log = _full_season_player_log(season)
    if log.empty:
        return _default_features()

    team_log = log[log["TEAM_ID"] == team_id].copy()
    if before_date:
        cutoff = pd.Timestamp(before_date)
        team_log = team_log[team_log["GAME_DATE"] < cutoff]

    if team_log.empty:
        return _default_features()

    # Identify the team's top scorers from the entire season-to-date — this is
    # a stable definition that doesn't churn game-to-game.
    top1 = _identify_top_scorers(team_log, top_n=1)
    top3 = _identify_top_scorers(team_log, top_n=3)

    # Take the most recent N games (by unique GAME_ID, sorted by date)
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

    total_minutes = recent["MIN"].sum()
    if total_minutes <= 0:
        return _default_features()

    star_minutes = recent[recent["PLAYER_ID"].isin(top1)]["MIN"].sum()
    top3_minutes = recent[recent["PLAYER_ID"].isin(top3)]["MIN"].sum()

    star_ratio = float(star_minutes / total_minutes)
    top3_ratio = float(top3_minutes / total_minutes)

    # Rotation size: distinct players averaging 15+ MPG over the recent window
    by_player = (
        recent.groupby("PLAYER_ID")["MIN"]
        .agg(["sum", "count"])
        .assign(mpg=lambda d: d["sum"] / d["count"])
    )
    rotation_size = int((by_player["mpg"] >= 15).sum())

    return {
        "star_minutes_ratio": star_ratio,
        "top3_minutes_ratio": top3_ratio,
        "rotation_size": rotation_size,
    }


def _default_features() -> dict:
    """Sensible neutral defaults when data is unavailable."""
    return {
        "star_minutes_ratio": 0.20,   # a healthy star plays ~36 of 240 minutes ≈ 15%; we use 20% as a slight buffer
        "top3_minutes_ratio": 0.45,   # top 3 typically combine for ~45% of minutes
        "rotation_size": 9,           # typical NBA rotation
    }
