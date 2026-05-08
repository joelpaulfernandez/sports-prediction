"""
Player availability features — a stand-in for an injury report.

WHAT THIS FILE DOES (in plain English)
──────────────────────────────────────
The model used to be totally blind to injuries. If LeBron was out, our
prediction for the Lakers was the same as if he were healthy. That's a
huge problem because a missing star can swing a game by 8+ points.

We can't easily get the official NBA injury report (it's a PDF, not an API),
so instead we infer it from the box score. The trick: if a team's leading
scorer played zero minutes in their last game, they're probably still hurt.

We derive three signals per team from their last few games:

  star_minutes_ratio   What share of total minutes did the team's top scorer
                       play? A healthy star plays ~15% of total team minutes
                       (about 36 of 240). When they're out, this drops near 0.

  top3_minutes_ratio   Same idea, but for the top 3 scorers combined. Catches
                       situations where multiple stars are out.

  rotation_size        How many different players are getting real minutes
                       (15+ per game)? Drops when a team is shorthanded.

These three numbers go into the model alongside team strength, rest, etc.

Performance trick: building these signals from the raw player game logs is
slow if you do it per-game. The SeasonAvailability class precomputes the
heavy bits once per season and then answers "what was the team's rotation
on date X?" instantly. The trainer relies on this — without it, retraining
took an hour; with it, ~5 minutes.
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
    A precomputed lookup table for one season's worth of player rotation data.

    The expensive work (downloading the season's player game logs, splitting
    them by team, finding each team's top scorers) happens once in __init__.
    After that, get_features() is a quick in-memory lookup.

    Training the model means computing rotation features for ~6,500 historical
    games. Without this class, each one would re-process the whole season's
    data — that's why training used to stall for an hour.
    """

    def __init__(self, season: str):
        self.season = season
        # Pull every player's game-by-game stats for this season (one big API call).
        log = _full_season_player_log(season)

        # Per-team caches we'll fill in below.
        self._team_logs: dict[int, pd.DataFrame] = {}    # each team's full game log
        self._top1: dict[int, set[int]] = {}              # each team's #1 scorer (player_id)
        self._top3: dict[int, set[int]] = {}              # each team's top-3 scorers

        if log.empty:
            return  # no data for this season — leave caches empty, defaults will kick in

        # Split the giant log into a smaller frame per team.
        for team_id, team_log in log.groupby("TEAM_ID"):
            team_log = team_log.sort_values("GAME_DATE")
            self._team_logs[int(team_id)] = team_log

            # Identify each team's top scorers by total points across the season.
            # We use these IDs later to check "did the star play in the last few games?"
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
        """
        Return the three rotation-strength numbers for `team_id`, looking only
        at the team's last `n_games` games before `before_date`.

        `before_date` is exclusive — important for training so we don't peek
        at the game we're trying to predict (that would be cheating).
        """
        # Get the team's pre-sorted game log. Empty = no data, return defaults.
        team_log = self._team_logs.get(int(team_id))
        if team_log is None or team_log.empty:
            return _default_features()

        # Clip to games strictly before the target date.
        if before_date:
            cutoff = pd.Timestamp(before_date)
            team_log = team_log[team_log["GAME_DATE"] < cutoff]

        if team_log.empty:
            return _default_features()

        # Find the most recent N unique games (by date), grab those player rows.
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

        # Total team minutes across those games. Used as the denominator for ratios.
        total_minutes = float(recent["MIN"].sum())
        if total_minutes <= 0:
            return _default_features()

        # The top scorers we identified during __init__.
        top1_set = self._top1.get(int(team_id), set())
        top3_set = self._top3.get(int(team_id), set())

        # Sum up minutes played by the star and top-3, just in these recent games.
        star_minutes = float(recent[recent["PLAYER_ID"].isin(top1_set)]["MIN"].sum())
        top3_minutes = float(recent[recent["PLAYER_ID"].isin(top3_set)]["MIN"].sum())

        # For rotation size: count distinct players averaging 15+ minutes per
        # game over the recent window. A healthy NBA rotation is usually 8-10.
        by_player = (
            recent.groupby("PLAYER_ID")["MIN"]
            .agg(["sum", "count"])
            .assign(mpg=lambda d: d["sum"] / d["count"])
        )
        rotation_size = int((by_player["mpg"] >= 15).sum())

        return {
            # Each ratio is "share of total team minutes" — drops near 0 when
            # the player is missing entirely.
            "star_minutes_ratio": star_minutes / total_minutes,
            "top3_minutes_ratio": top3_minutes / total_minutes,
            "rotation_size": rotation_size,
        }


# In-memory cache: avoids rebuilding the same SeasonAvailability twice.
# Keyed by season string ("2025-26", etc.). The trainer hits each season once,
# the inference path hits the current season many times — both benefit.
_season_cache: dict[str, SeasonAvailability] = {}


def get_season_availability(season: str) -> SeasonAvailability:
    """Return a cached SeasonAvailability for `season`, building it on first call."""
    if season not in _season_cache:
        _season_cache[season] = SeasonAvailability(season)
    return _season_cache[season]


# ---------------------------------------------------------------------------
# Convenience wrapper — same answer as get_season_availability().get_features(),
# but a one-liner for callers that only need a single team's features.
# ---------------------------------------------------------------------------

def compute_team_availability(
    team_id: int,
    season: str = "2025-26",
    before_date: Optional[str] = None,
    n_games: int = 3,
) -> dict:
    """One-off lookup that uses the cached SeasonAvailability under the hood."""
    return get_season_availability(season).get_features(team_id, before_date, n_games)
