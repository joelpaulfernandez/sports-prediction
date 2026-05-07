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


# ---------------------------------------------------------------------------
# Today's games
# ---------------------------------------------------------------------------

def _parse_cdn_game(g: dict, game_date: str) -> dict:
    home = g["homeTeam"]
    away = g["awayTeam"]
    status = int(g.get("gameStatus", 1))
    home_score = g["homeTeam"].get("score")
    away_score = g["awayTeam"].get("score")
    return {
        "id": g["gameId"],
        "date": game_date,
        "home_team_id": int(home["teamId"]),
        "away_team_id": int(away["teamId"]),
        "home_team_name": f"{home.get('teamCity', '')} {home.get('teamName', '')}".strip(),
        "away_team_name": f"{away.get('teamCity', '')} {away.get('teamName', '')}".strip(),
        "home_pts": int(home_score) if home_score is not None and status >= 2 else None,
        "away_pts": int(away_score) if away_score is not None and status >= 2 else None,
        "status_id": status,
        "status_text": g.get("gameStatusText", ""),
    }


def _games_from_gamefinder(game_date: str) -> Optional[list[dict]]:
    """
    Use LeagueGameFinder to find games for a specific date.
    Works for completed games and sometimes scheduled ones.
    """
    try:
        from nba_api.stats.endpoints import leaguegamefinder
        finder = leaguegamefinder.LeagueGameFinder(
            league_id_nullable="00",
            date_from_nullable=game_date,
            date_to_nullable=game_date,
            season_type_nullable="Playoffs",
        )
        df = finder.get_data_frames()[0]
        if df.empty:
            # Try regular season too
            finder2 = leaguegamefinder.LeagueGameFinder(
                league_id_nullable="00",
                date_from_nullable=game_date,
                date_to_nullable=game_date,
                season_type_nullable="Regular Season",
            )
            df = finder2.get_data_frames()[0]
        if df.empty:
            return []

        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
        df["is_home"] = df["MATCHUP"].str.contains(r" vs\. ")
        home_df = df[df["is_home"]].copy()
        away_df = df[~df["is_home"]].copy()

        merged = home_df.merge(
            away_df[["GAME_ID", "TEAM_ID", "TEAM_NAME", "PTS", "WL"]],
            on="GAME_ID", suffixes=("_home", "_away"),
        )

        games = []
        for _, row in merged.iterrows():
            h_pts = None if pd.isna(row.get("PTS_home", float("nan"))) else int(row["PTS_home"])
            a_pts = None if pd.isna(row.get("PTS_away", float("nan"))) else int(row["PTS_away"])
            status_id = 3 if h_pts is not None else 1
            games.append({
                "id": str(row["GAME_ID"]),
                "date": game_date,
                "home_team_id": int(row["TEAM_ID_home"]),
                "away_team_id": int(row["TEAM_ID_away"]),
                "home_team_name": str(row["TEAM_NAME_home"]),
                "away_team_name": str(row["TEAM_NAME_away"]),
                "home_pts": h_pts,
                "away_pts": a_pts,
                "status_id": status_id,
                "status_text": "Final" if status_id == 3 else "Scheduled",
            })
        return games
    except Exception as exc:
        print(f"[nba_data] leaguegamefinder (date={game_date}) error: {exc}")
        return None


def get_todays_games(date: Optional[str] = None) -> list[dict]:
    """
    Return NBA games for `date` (YYYY-MM-DD, defaults to today).
    Uses LeagueGameFinder which reliably works when stats.nba.com endpoints
    like scoreboardv2 are unavailable.
    """
    game_date = date or str(datetime.date.today())
    cache_key = f"games_{game_date}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    games = _games_from_gamefinder(game_date)
    if games is not None:
        _cache_set(cache_key, games, ttl=120)
        return games

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
