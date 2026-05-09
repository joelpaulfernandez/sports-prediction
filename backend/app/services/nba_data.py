from __future__ import annotations

"""
NBA data service using nba_api (stats.nba.com — completely free, no API key required).

All functions are synchronous; use asyncio.to_thread() in async route handlers.
Results are cached in-memory with TTL to respect NBA stats API rate limits.
"""

import datetime
import time
import random
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Season constants
# ---------------------------------------------------------------------------

CURRENT_SEASON = "2025-26"
TRAINING_SEASONS = ["2021-22", "2022-23", "2023-24", "2024-25"]

from app.services.cache import cache_get as _cache_get, cache_set as _cache_set


def _sleep():
    """Polite pause between NBA API calls to avoid 429s."""
    time.sleep(0.65)


# NBA GAME_ID format: 10-digit string where index 2 encodes season type.
# 0021xxxxxx = Preseason, 0022xxxxxx = Regular Season, 0042xxxxxx = Playoffs,
# 0052xxxxxx = Play-in. We check this to derive is_playoff cheaply, but if
# the format ever changes the assertion below will surface it loudly.
_VALID_GAME_ID_PREFIXES = {"1", "2", "4", "5"}


def is_playoff_game_id(game_id: str | int) -> bool:
    """
    True if `game_id` follows the NBA convention for a playoff game.
    Pads ints to the canonical 10-digit form so callers don't have to.
    Logs a warning (rather than raising) on unexpected formats so a future
    NBA schema change surfaces in logs without breaking inference.
    """
    s = str(game_id)
    if s.isdigit():
        s = s.zfill(10)
    if len(s) < 3 or s[2:3] not in _VALID_GAME_ID_PREFIXES:
        print(f"[nba_data] WARNING: unexpected GAME_ID format: {game_id!r}")
        return False
    return s[2:3] == "4"


# ---------------------------------------------------------------------------
# Today's games
# ---------------------------------------------------------------------------

def _fetch_all_playoff_games(season: str = CURRENT_SEASON) -> Optional[pd.DataFrame]:
    """
    Fetch all playoff games for a season via LeagueGameFinder (no date filter).
    Returns a merged home/away DataFrame with one row per game, or None on error.
    """
    try:
        from nba_api.stats.endpoints import leaguegamefinder
        finder = leaguegamefinder.LeagueGameFinder(
            league_id_nullable="00",
            season_nullable=season,
            season_type_nullable="Playoffs",
        )
        df = finder.get_data_frames()[0]
        if df.empty:
            return pd.DataFrame()

        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
        df["is_home"] = df["MATCHUP"].str.contains(r" vs\. ")
        home_df = df[df["is_home"]].copy()
        away_df = df[~df["is_home"]].copy()

        merged = home_df.merge(
            away_df[["GAME_ID", "TEAM_ID", "TEAM_NAME", "WL", "PTS"]],
            on="GAME_ID", suffixes=("_home", "_away"),
        )
        return merged
    except Exception as exc:
        print(f"[nba_data] _fetch_all_playoff_games error: {exc}")
        return None


def _get_ongoing_series_matchups(season: str = CURRENT_SEASON) -> list[dict]:
    """
    Detect ongoing playoff series and return one game entry per active series.
    A series is ongoing when neither team has 4 wins yet.
    Home/away alternation follows NBA format (2-2-1-1-1).
    """
    cache_key = f"ongoing_series_{season}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    df = _fetch_all_playoff_games(season)
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return []

    today_str = str(datetime.date.today())

    games_out = []
    df["series_key"] = df.apply(
        lambda r: tuple(sorted([int(r["TEAM_ID_home"]), int(r["TEAM_ID_away"])])),
        axis=1,
    )

    for series_key, series_df in df.groupby("series_key"):
        series_df = series_df.sort_values("GAME_DATE")

        # Higher seed = team that hosted game 1 (game 1 home team)
        first_game = series_df.iloc[0]
        higher_seed_team_id = int(first_game["TEAM_ID_home"])
        lower_seed_team_id = int(first_game["TEAM_ID_away"])
        higher_seed_name = str(first_game["TEAM_NAME_home"])
        lower_seed_name = str(first_game["TEAM_NAME_away"])

        # Count wins per team regardless of home/away assignment in each game
        higher_wins = 0
        lower_wins = 0
        for _, g in series_df.iterrows():
            if int(g["TEAM_ID_home"]) == higher_seed_team_id:
                if g["WL_home"] == "W":
                    higher_wins += 1
                else:
                    lower_wins += 1
            else:
                if g["WL_away"] == "W":
                    higher_wins += 1
                else:
                    lower_wins += 1

        # Series is over once either team has 4 wins
        if higher_wins >= 4 or lower_wins >= 4:
            continue

        games_played = len(series_df)

        # NBA 2-2-1-1-1 home/away pattern (higher seed hosts games 1,2,5)
        home_games_pattern = [True, True, False, False, True, False, True]
        next_game_num = games_played  # 0-indexed
        higher_seed_is_home = home_games_pattern[next_game_num] if next_game_num < len(home_games_pattern) else True

        if higher_seed_is_home:
            next_home_id = higher_seed_team_id
            next_away_id = lower_seed_team_id
            next_home_name = higher_seed_name
            next_away_name = lower_seed_name
        else:
            next_home_id = lower_seed_team_id
            next_away_id = higher_seed_team_id
            next_home_name = lower_seed_name
            next_away_name = higher_seed_name

        synthetic_id = f"04250{series_key[0]:010d}{series_key[1]:010d}"[:16]
        series_label = f"({higher_wins}-{lower_wins})"

        games_out.append({
            "id": synthetic_id,
            "date": today_str,
            "home_team_id": next_home_id,
            "away_team_id": next_away_id,
            "home_team_name": next_home_name,
            "away_team_name": next_away_name,
            "home_pts": None,
            "away_pts": None,
            "status_id": 1,
            "status_text": f"Playoffs {series_label}",
        })

    _cache_set(cache_key, games_out, ttl=300)
    return games_out


def _games_from_live_scoreboard() -> Optional[list[dict]]:
    """
    Fetch today's NBA games from the live data API.
    Returns scheduled, in-progress, and finished games with gameTimeUTC.
    """
    try:
        from nba_api.live.nba.endpoints import scoreboard as live_scoreboard
        sb = live_scoreboard.ScoreBoard()
        data = sb.get_dict()
        raw = data.get("scoreboard", {}).get("games", [])
        if not raw:
            return []

        games = []
        for g in raw:
            home = g["homeTeam"]
            away = g["awayTeam"]
            status = int(g.get("gameStatus", 1))
            home_score = home.get("score")
            away_score = away.get("score")
            game_time_utc = g.get("gameTimeUTC", "")
            # Use UTC date as the canonical game date
            game_date = game_time_utc[:10] if game_time_utc else str(datetime.date.today())
            games.append({
                "id": str(g["gameId"]),
                "date": game_date,
                "home_team_id": int(home["teamId"]),
                "away_team_id": int(away["teamId"]),
                "home_team_name": f"{home.get('teamCity', '')} {home.get('teamName', '')}".strip(),
                "away_team_name": f"{away.get('teamCity', '')} {away.get('teamName', '')}".strip(),
                "home_pts": int(home_score) if home_score and status >= 2 else None,
                "away_pts": int(away_score) if away_score and status >= 2 else None,
                "status_id": status,
                "status_text": g.get("gameStatusText", ""),
                "game_time_utc": game_time_utc,
            })
        return games
    except Exception as exc:
        print(f"[nba_data] live scoreboard error: {exc}")
        return None


def get_todays_games(date: Optional[str] = None) -> list[dict]:
    """
    Return NBA games for today.

    Strategy:
    1. Live scoreboard (nba_api.live) — accurate schedule with UTC tip-off times.
    2. Ongoing series detection — fallback for off-days / between rounds.

    `date` is accepted for cache-keying but the live scoreboard always returns
    the current NBA day regardless of what the client passes.
    """
    game_date = date or str(datetime.date.today())
    cache_key = f"games_{game_date}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    games = _games_from_live_scoreboard()
    if games is not None:
        ttl = 30 if any(g["status_id"] == 2 for g in games) else 120
        _cache_set(cache_key, games, ttl=ttl)
        return games

    # Fallback: ongoing series (for off-days or API outages)
    series_games = _get_ongoing_series_matchups(CURRENT_SEASON)
    if series_games:
        _cache_set(cache_key, series_games, ttl=300)
        return series_games

    return _mock_games(game_date)


# ---------------------------------------------------------------------------
# Team season stats (all 30 teams in one call per measure type)
# ---------------------------------------------------------------------------

def get_all_team_stats(season: str = CURRENT_SEASON) -> dict[int, dict]:
    """
    Return {team_id: stats_dict} for every NBA team this season.
    stats_dict contains advanced metrics (net/off/def rating, pace),
    four-factor metrics (eFG%, TOV%, OREB%, FTA rate), and base stats (PPG, W%).
    Falls back to mock data on API failure.
    """
    cache_key = f"team_stats_{season}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        from nba_api.stats.endpoints import leaguedashteamstats

        # 1. Advanced metrics
        adv_df = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
            league_id_nullable="00",
        ).get_data_frames()[0]
        _sleep()

        # 2. Four Factors
        ff_df = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            measure_type_detailed_defense="Four Factors",
            per_mode_detailed="PerGame",
            league_id_nullable="00",
        ).get_data_frames()[0]
        _sleep()

        # 3. Base stats (PPG, W-L)
        base_df = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            measure_type_detailed_defense="Base",
            per_mode_detailed="PerGame",
            league_id_nullable="00",
        ).get_data_frames()[0]

        result: dict[int, dict] = {}

        for _, row in adv_df.iterrows():
            tid = int(row["TEAM_ID"])
            result[tid] = {
                "team_id": tid,
                "team_name": str(row.get("TEAM_NAME", "")),
                "gp": int(row.get("GP", 0)),
                "w": int(row.get("W", 0)),
                "l": int(row.get("L", 0)),
                "w_pct": float(row.get("W_PCT", 0.5)),
                "off_rating": float(row.get("OFF_RATING", 110.0)),
                "def_rating": float(row.get("DEF_RATING", 110.0)),
                "net_rating": float(row.get("NET_RATING", 0.0)),
                "pace": float(row.get("PACE", 100.0)),
                "ts_pct": float(row.get("TS_PCT", 0.55)),
                "pie": float(row.get("PIE", 0.5)),
            }

        for _, row in ff_df.iterrows():
            tid = int(row["TEAM_ID"])
            if tid in result:
                result[tid].update({
                    "efg_pct": float(row.get("EFG_PCT", 0.52)),
                    "fta_rate": float(row.get("FTA_RATE", 0.25)),
                    "tov_pct": float(row.get("TM_TOV_PCT", 13.0)),
                    "oreb_pct": float(row.get("OREB_PCT", 0.25)),
                    "opp_efg_pct": float(row.get("OPP_EFG_PCT", 0.52)),
                    "opp_fta_rate": float(row.get("OPP_FTA_RATE", 0.25)),
                    "opp_tov_pct": float(row.get("OPP_TOV_PCT", 13.0)),
                    "opp_oreb_pct": float(row.get("OPP_OREB_PCT", 0.25)),
                })

        for _, row in base_df.iterrows():
            tid = int(row["TEAM_ID"])
            if tid in result:
                result[tid].update({
                    "ppg": float(row.get("PTS", 110.0)),
                    "plus_minus": float(row.get("PLUS_MINUS", 0.0)),
                })

        _cache_set(cache_key, result, ttl=3600)
        return result

    except Exception as exc:
        print(f"[nba_data] leaguedashteamstats error: {exc}")
        return _mock_team_stats()


# ---------------------------------------------------------------------------
# Season game log (for Elo + recent form + rest calculation)
# ---------------------------------------------------------------------------

def get_season_game_log(
    season: str = CURRENT_SEASON,
    season_type: str = "Regular Season",
) -> pd.DataFrame:
    """
    Return DataFrame of every game in the season (one row per team per game).
    Key columns: TEAM_ID, GAME_ID, GAME_DATE (datetime), MATCHUP, WL, PTS, PLUS_MINUS.
    MATCHUP contains "vs." for home team, "@" for away team.
    """
    cache_key = f"game_log_{season}_{season_type}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        from nba_api.stats.endpoints import leaguegamefinder

        finder = leaguegamefinder.LeagueGameFinder(
            league_id_nullable="00",
            season_nullable=season,
            season_type_nullable=season_type,
        )
        df = finder.get_data_frames()[0]

        if df.empty:
            return pd.DataFrame()

        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
        df = df.sort_values("GAME_DATE").reset_index(drop=True)

        _cache_set(cache_key, df, ttl=1800)
        return df

    except Exception as exc:
        print(f"[nba_data] leaguegamefinder error ({season} {season_type}): {exc}")
        return pd.DataFrame()


def get_full_season_log(season: str = CURRENT_SEASON) -> pd.DataFrame:
    """Combine regular season + playoff logs for Elo continuity."""
    reg = get_season_game_log(season, "Regular Season")
    _sleep()
    playoffs = get_season_game_log(season, "Playoffs")
    if reg.empty and playoffs.empty:
        return pd.DataFrame()
    parts = [df for df in [reg, playoffs] if not df.empty]
    combined = pd.concat(parts, ignore_index=True)
    return combined.sort_values("GAME_DATE").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Per-team recent form
# ---------------------------------------------------------------------------

def compute_team_recent_form(
    team_id: int,
    game_log: pd.DataFrame,
    n_games: int = 10,
    before_date: Optional[str] = None,
) -> dict:
    """
    Compute recent-form stats for a team.
    Returns: recent_win_pct, recent_net_rtg (avg point diff), last_game_date.
    """
    if game_log is None or game_log.empty:
        return {"recent_win_pct": 0.5, "recent_net_rtg": 0.0, "last_game_date": None}

    team_log = game_log[game_log["TEAM_ID"] == team_id].copy()

    if before_date:
        cutoff = pd.Timestamp(before_date)
        team_log = team_log[team_log["GAME_DATE"] < cutoff]

    team_log = team_log.sort_values("GAME_DATE").tail(n_games)

    if team_log.empty:
        return {"recent_win_pct": 0.5, "recent_net_rtg": 0.0, "last_game_date": None}

    wins = (team_log["WL"] == "W").sum()
    recent_win_pct = float(wins / len(team_log))
    recent_net_rtg = float(team_log["PLUS_MINUS"].mean())
    last_game_date = str(team_log["GAME_DATE"].max().date())

    return {
        "recent_win_pct": recent_win_pct,
        "recent_net_rtg": recent_net_rtg,
        "last_game_date": last_game_date,
    }


def compute_home_road_splits(
    team_id: int,
    game_log: pd.DataFrame,
    before_date: Optional[str] = None,
) -> dict:
    """
    Win % at home and on the road for `team_id`.
    MATCHUP contains "vs." for home games and "@" for away games.
    """
    if game_log is None or game_log.empty:
        return {"home_w_pct": 0.5, "road_w_pct": 0.5}

    team_log = game_log[game_log["TEAM_ID"] == team_id]
    if before_date:
        team_log = team_log[team_log["GAME_DATE"] < pd.Timestamp(before_date)]

    if team_log.empty:
        return {"home_w_pct": 0.5, "road_w_pct": 0.5}

    is_home = team_log["MATCHUP"].str.contains(r" vs\. ", regex=True)
    home_games = team_log[is_home]
    road_games = team_log[~is_home]

    home_w_pct = (
        float((home_games["WL"] == "W").sum() / len(home_games))
        if len(home_games) > 0 else 0.5
    )
    road_w_pct = (
        float((road_games["WL"] == "W").sum() / len(road_games))
        if len(road_games) > 0 else 0.5
    )
    return {"home_w_pct": home_w_pct, "road_w_pct": road_w_pct}


def compute_h2h_features(
    home_id: int,
    away_id: int,
    game_log: pd.DataFrame,
    before_date: Optional[str] = None,
    is_playoff: bool = False,
) -> dict:
    """
    Head-to-head and series-state features for the upcoming game.

    Returns dict with:
      home_won_last     +1.0 if home won the most recent prior meeting,
                        -1.0 if away won it, 0.0 if no prior meetings
      series_lead       (home_wins - away_wins) in the current playoff series
                        before this game; 0.0 for non-playoff games
    """
    default = {"home_won_last": 0.0, "series_lead": 0.0}
    if game_log is None or game_log.empty:
        return default

    # Find all games where both teams faced each other
    # GAME_ID is the same for both teams' rows; we filter to home team's
    # rows and look at OPP via MATCHUP, but simpler: get game_ids that
    # contain both team_ids in the log.
    home_games = game_log[game_log["TEAM_ID"] == home_id]
    if home_games.empty:
        return default

    if before_date:
        cutoff = pd.Timestamp(before_date)
        home_games = home_games[home_games["GAME_DATE"] < cutoff]

    if home_games.empty:
        return default

    # Filter to games where the OPPONENT was the away team
    away_games_in_log = game_log[game_log["TEAM_ID"] == away_id]
    if before_date:
        away_games_in_log = away_games_in_log[away_games_in_log["GAME_DATE"] < pd.Timestamp(before_date)]
    away_game_ids = set(away_games_in_log["GAME_ID"].tolist())

    h2h = home_games[home_games["GAME_ID"].isin(away_game_ids)].sort_values("GAME_DATE")
    if h2h.empty:
        return default

    last = h2h.iloc[-1]
    home_won_last = 1.0 if last["WL"] == "W" else -1.0

    # Series lead — only meaningful for playoff games. Uses the same
    # GAME_ID convention helper as the inference path.
    series_lead = 0.0
    if is_playoff:
        h2h_playoff = h2h[h2h["GAME_ID"].astype(str).map(is_playoff_game_id)]
        if not h2h_playoff.empty:
            home_wins = int((h2h_playoff["WL"] == "W").sum())
            away_wins = int((h2h_playoff["WL"] == "L").sum())
            series_lead = float(home_wins - away_wins)

    return {"home_won_last": home_won_last, "series_lead": series_lead}


def compute_rest_days(last_game_date: Optional[str], game_date: Optional[str] = None) -> int:
    """Days between last game and upcoming game, capped at 7."""
    if not last_game_date:
        return 7
    ref = (
        datetime.date.today()
        if not game_date
        else datetime.date.fromisoformat(game_date)
    )
    last = datetime.date.fromisoformat(last_game_date)
    return min(int((ref - last).days), 7)


# ---------------------------------------------------------------------------
# Mock / fallback data
# ---------------------------------------------------------------------------

_MOCK_TEAMS = [
    (1610612747, "Los Angeles Lakers"),
    (1610612738, "Boston Celtics"),
    (1610612744, "Golden State Warriors"),
    (1610612748, "Miami Heat"),
    (1610612756, "Phoenix Suns"),
    (1610612743, "Denver Nuggets"),
    (1610612751, "Brooklyn Nets"),
    (1610612752, "New York Knicks"),
]


def _mock_games(date: str) -> list[dict]:
    return [
        {
            "id": "0042501001",
            "date": date,
            "home_team_id": 1610612747,
            "away_team_id": 1610612738,
            "home_team_name": "Los Angeles Lakers",
            "away_team_name": "Boston Celtics",
            "home_pts": None,
            "away_pts": None,
            "status_id": 1,
            "status_text": "7:30 pm ET",
        },
        {
            "id": "0042501002",
            "date": date,
            "home_team_id": 1610612744,
            "away_team_id": 1610612743,
            "home_team_name": "Golden State Warriors",
            "away_team_name": "Denver Nuggets",
            "home_pts": None,
            "away_pts": None,
            "status_id": 1,
            "status_text": "10:00 pm ET",
        },
    ]


def _mock_team_stats() -> dict[int, dict]:
    result = {}
    for tid, name in _MOCK_TEAMS:
        rng = random.Random(tid)
        w = rng.randint(28, 58)
        l = rng.randint(12, 42)
        net = rng.uniform(-6.0, 9.0)
        off = 110.0 + rng.uniform(-4, 5)
        result[tid] = {
            "team_id": tid,
            "team_name": name,
            "gp": w + l,
            "w": w,
            "l": l,
            "w_pct": round(w / (w + l), 3),
            "off_rating": round(off, 1),
            "def_rating": round(off - net, 1),
            "net_rating": round(net, 1),
            "pace": round(rng.uniform(97.5, 102.5), 1),
            "ts_pct": round(rng.uniform(0.540, 0.605), 3),
            "pie": round(rng.uniform(0.470, 0.540), 3),
            "efg_pct": round(rng.uniform(0.510, 0.575), 3),
            "fta_rate": round(rng.uniform(0.205, 0.310), 3),
            "tov_pct": round(rng.uniform(11.0, 16.5), 1),
            "oreb_pct": round(rng.uniform(0.215, 0.315), 3),
            "opp_efg_pct": round(rng.uniform(0.510, 0.565), 3),
            "opp_fta_rate": round(rng.uniform(0.210, 0.305), 3),
            "opp_tov_pct": round(rng.uniform(11.5, 16.0), 1),
            "opp_oreb_pct": round(rng.uniform(0.220, 0.310), 3),
            "ppg": round(110.0 + net + rng.uniform(-3, 3), 1),
            "plus_minus": round(net, 1),
        }
    return result
