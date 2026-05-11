"""
NHL data service using the public NHL Stats API (api-web.nhle.com).

All functions are synchronous; wrap in asyncio.to_thread() in async handlers.
NHL API requires no key and has generous rate limits.
"""

from __future__ import annotations

import datetime
import time
from typing import Optional

import requests

from app.services.cache import cache_get, cache_set

_BASE = "https://api-web.nhle.com/v1"
_SESSION = requests.Session()
_SESSION.headers["User-Agent"] = "StatCast/2.0 (sports-prediction; educational)"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(path: str, ttl: int = 300) -> Optional[dict]:
    key = f"nhl:raw:{path}"
    cached = cache_get(key)
    if cached is not None:
        return cached
    try:
        resp = _SESSION.get(f"{_BASE}{path}", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        cache_set(key, data, ttl)
        return data
    except Exception as exc:
        print(f"[nhl_data] GET {path} failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------

def get_today_schedule() -> list[dict]:
    """Return today's NHL games with basic metadata."""
    cached = cache_get("nhl:schedule:today")
    if cached is not None:
        return cached

    today = datetime.date.today().isoformat()
    data = _get(f"/schedule/{today}", ttl=120)
    if not data:
        return []

    games = []
    for week in data.get("gameWeek", []):
        week_date = week.get("date", "")
        if week_date != today:
            continue
        for game in week.get("games", []):
            start_utc = game.get("startTimeUTC", "")
            game_date = week_date

            state = game.get("gameState", "")
            if state in ("FUT", "PRE"):
                status = "scheduled"
            elif state in ("LIVE", "CRIT"):
                status = "live"
            elif state in ("FINAL", "OFF"):
                status = "finished"
            else:
                status = "scheduled"

            home = game.get("homeTeam", {})
            away = game.get("awayTeam", {})

            games.append({
                "game_id":        str(game.get("id", "")),
                "home_team":      home.get("placeName", {}).get("default", home.get("abbrev", "")),
                "home_team_abbrev": home.get("abbrev", ""),
                "home_team_full": f"{home.get('placeName', {}).get('default', '')} {home.get('commonName', {}).get('default', '')}".strip(),
                "away_team":      away.get("placeName", {}).get("default", away.get("abbrev", "")),
                "away_team_abbrev": away.get("abbrev", ""),
                "away_team_full": f"{away.get('placeName', {}).get('default', '')} {away.get('commonName', {}).get('default', '')}".strip(),
                "game_date":      game_date,
                "game_time_utc":  start_utc,
                "status":         status,
                "home_score":     home.get("score"),
                "away_score":     away.get("score"),
                "venue":          game.get("venue", {}).get("default", ""),
            })

    cache_set("nhl:schedule:today", games, 120)
    return games


# ---------------------------------------------------------------------------
# Standings / team stats
# ---------------------------------------------------------------------------

def get_standings() -> dict[str, dict]:
    """
    Return standings keyed by team abbreviation.
    Each value has wins, losses, ot_losses, points, and advanced stats.
    """
    cached = cache_get("nhl:standings")
    if cached is not None:
        return cached

    data = _get("/standings/now", ttl=3600)
    if not data:
        return {}

    standings: dict[str, dict] = {}
    for team in data.get("standings", []):
        abbrev = team.get("teamAbbrev", {}).get("default", "")
        if not abbrev:
            continue

        gp = team.get("gamesPlayed", 0) or 1

        standings[abbrev] = {
            "team_name":  f"{team.get('placeName', {}).get('default', '')} {team.get('teamCommonName', {}).get('default', '')}".strip(),
            "abbrev":     abbrev,
            "wins":       team.get("wins", 0),
            "losses":     team.get("losses", 0),
            "ot_losses":  team.get("otLosses", 0),
            "points":     team.get("points", 0),
            "points_pct": team.get("pointPctg", 0.0),
            "gp":         gp,
            "goals_for_per_game":     round(team.get("goalFor", 0) / gp, 3),
            "goals_against_per_game": round(team.get("goalAgainst", 0) / gp, 3),
            "goal_diff_per_game":     round((team.get("goalFor", 0) - team.get("goalAgainst", 0)) / gp, 3),
            # Shots, PP, PK, SV% come from club-stats endpoint (fetched separately)
            "pp_pct":              0.0,
            "pk_pct":              0.0,
            "save_pct":            0.0,
            "shots_for_per_game":  0.0,
            "shots_against_per_game": 0.0,
            # L10 record
            "l10_wins":  team.get("l10Wins", 0),
            "l10_losses": team.get("l10Losses", 0),
            "l10_ot":    team.get("l10OtLosses", 0),
        }

    # Enrich with advanced stats
    _enrich_standings_with_stats(standings)

    cache_set("nhl:standings", standings, 3600)
    return standings


def _enrich_standings_with_stats(standings: dict[str, dict]) -> None:
    """
    Compute SV% and shots/game from club-stats goalie/skater player lists.

    The NHL API returns per-player arrays (no team-level aggregates), so we
    aggregate manually: SV% = total saves / total shots across all goalies.
    PP/PK% are not available from the public API; those weights are 0.
    """
    season = _current_season_code()
    for abbrev, team_data in standings.items():
        try:
            data = _get(f"/club-stats/{abbrev}/{season}/2", ttl=7200)
            if not data:
                continue

            goalies  = data.get("goalies", [])
            skaters  = data.get("skaters", [])
            gp = team_data["gp"] or 1

            # SV% — aggregate across all goalies weighted by shots faced
            total_shots = sum(g.get("shotsAgainst", 0) for g in goalies)
            total_saves = sum(g.get("saves", 0) for g in goalies)
            if total_shots > 0:
                team_data["save_pct"] = round(total_saves / total_shots, 4)

            # Shots for per game — sum skater shots / GP
            total_skater_shots = sum(s.get("shots", 0) for s in skaters)
            if total_skater_shots > 0:
                team_data["shots_for_per_game"] = round(total_skater_shots / gp, 2)

            # Shots against per game — derivable from goalie saves + GA
            if total_shots > 0:
                team_data["shots_against_per_game"] = round(total_shots / gp, 2)

            time.sleep(0.05)
        except Exception as exc:
            print(f"[nhl_data] stats enrich failed for {abbrev}: {exc}")


def _current_season_code() -> str:
    """Return '20242025' style season code for the current NHL season."""
    today = datetime.date.today()
    year = today.year if today.month >= 9 else today.year - 1
    return f"{year}{year + 1}"


# ---------------------------------------------------------------------------
# Recent results (for accuracy tracking)
# ---------------------------------------------------------------------------

def get_recent_results(n: int = 10) -> list[dict]:
    """Return last N completed NHL games with final scores."""
    cached = cache_get(f"nhl:recent:{n}")
    if cached is not None:
        return cached

    # Walk backwards through schedule dates
    results = []
    check_date = datetime.date.today() - datetime.timedelta(days=1)
    attempts = 0

    while len(results) < n and attempts < 14:
        attempts += 1
        date_str = check_date.isoformat()
        data = _get(f"/schedule/{date_str}", ttl=86400)
        if data:
            for week in data.get("gameWeek", []):
                for game in week.get("games", []):
                    state = game.get("gameState", "")
                    if state not in ("FINAL", "OFF"):
                        continue
                    home = game.get("homeTeam", {})
                    away = game.get("awayTeam", {})
                    results.append({
                        "game_id":        str(game.get("id", "")),
                        "game_date":      date_str,
                        "home_abbrev":    home.get("abbrev", ""),
                        "away_abbrev":    away.get("abbrev", ""),
                        "home_score":     home.get("score", 0),
                        "away_score":     away.get("score", 0),
                    })
        check_date -= datetime.timedelta(days=1)

    results = results[:n]
    cache_set(f"nhl:recent:{n}", results, 3600)
    return results
