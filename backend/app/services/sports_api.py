import httpx

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"


async def get_upcoming_games(date: str) -> list[dict]:
    """Fetch NBA games for a given date (YYYY-MM-DD) from ESPN."""
    espn_date = date.replace("-", "")  # ESPN wants YYYYMMDD
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        try:
            response = await client.get("/scoreboard", params={"dates": espn_date})
            response.raise_for_status()
            data = response.json()
            return [_normalize_game(e) for e in data.get("events", [])]
        except httpx.HTTPStatusError as exc:
            print(f"ESPN API error fetching games: {exc.response.status_code}")
            return _mock_games(date)
        except httpx.RequestError as exc:
            print(f"ESPN request error fetching games: {exc}")
            return _mock_games(date)


async def get_team_stats(team_id: int) -> dict:
    """Fetch season stats for a team from ESPN."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        try:
            response = await client.get(f"/teams/{team_id}/statistics")
            response.raise_for_status()
            data = response.json()
            return _normalize_team_stats(data, team_id)
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            print(f"ESPN error fetching team stats for {team_id}: {exc}")
            return _mock_team_stats(team_id)


async def get_standings() -> list[dict]:
    """Fetch current NBA standings from ESPN."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        try:
            response = await client.get("/standings")
            response.raise_for_status()
            data = response.json()
            return _normalize_standings(data)
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            print(f"ESPN error fetching standings: {exc}")
            return _mock_standings()


# ---------------------------------------------------------------------------
# Normalization helpers — map ESPN shapes to our internal format
# ---------------------------------------------------------------------------

def _normalize_game(event: dict) -> dict:
    competition = event.get("competitions", [{}])[0]
    competitors = competition.get("competitors", [])

    home = next((c for c in competitors if c.get("homeAway") == "home"), {})
    away = next((c for c in competitors if c.get("homeAway") == "away"), {})

    status_type = competition.get("status", {}).get("type", {})
    espn_status = status_type.get("name", "STATUS_SCHEDULED")

    home_score_raw = home.get("score")
    away_score_raw = away.get("score")

    return {
        "id": event["id"],
        "date": event.get("date", ""),
        "status": {
            "short": _espn_status_to_short(espn_status),
            "long": status_type.get("description", "Scheduled"),
        },
        "teams": {
            "home": {
                "id": int(home.get("team", {}).get("id", 0)),
                "name": home.get("team", {}).get("displayName", ""),
            },
            "away": {
                "id": int(away.get("team", {}).get("id", 0)),
                "name": away.get("team", {}).get("displayName", ""),
            },
        },
        "scores": {
            "home": {"total": int(home_score_raw) if home_score_raw is not None else None},
            "away": {"total": int(away_score_raw) if away_score_raw is not None else None},
        },
    }


def _espn_status_to_short(espn_status: str) -> str:
    if espn_status == "STATUS_FINAL":
        return "FT"
    if espn_status == "STATUS_IN_PROGRESS":
        return "LIVE"
    return "NS"


def _normalize_team_stats(data: dict, team_id: int) -> dict:
    team = data.get("team", {})

    # Record is in "recordSummary" e.g. "50-27"
    wins, losses = _parse_record(team.get("recordSummary", "0-0"))

    # PPG lives in the offensive stats category (under results.stats.categories)
    ppg = 105.0
    categories = data.get("results", {}).get("stats", {}).get("categories", [])
    for category in categories:
        for stat in category.get("stats", []):
            if stat.get("name") == "avgPoints":
                ppg = float(stat.get("value", 105.0))
                break

    return {
        "team": {"id": team_id, "name": team.get("displayName", f"Team {team_id}")},
        "wins": {"all": {"total": wins}},
        "losses": {"all": {"total": losses}},
        "points": {"for": {"average": {"all": str(ppg)}}},
        "games": wins + losses,
    }


def _normalize_standings(data: dict) -> list[dict]:
    standings = []
    for group in data.get("children", []):
        for entry in group.get("standings", {}).get("entries", []):
            team = entry.get("team", {})
            stats = {s["name"]: s["value"] for s in entry.get("stats", [])}
            standings.append({
                "team": {
                    "id": int(team.get("id", 0)),
                    "name": team.get("displayName", ""),
                },
                "wins": {"all": {"total": int(stats.get("wins", 0))}},
                "losses": {"all": {"total": int(stats.get("losses", 0))}},
            })
    return standings


def _parse_record(record_summary: str) -> tuple[int, int]:
    try:
        parts = record_summary.split("-")
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return 0, 0


# ---------------------------------------------------------------------------
# Mock / fallback data so the app works when ESPN is unreachable
# ---------------------------------------------------------------------------

def _mock_games(date: str) -> list[dict]:
    return [
        {
            "id": "1001",
            "date": date,
            "status": {"short": "NS", "long": "Scheduled"},
            "teams": {
                "home": {"id": 13, "name": "Los Angeles Lakers"},
                "away": {"id": 2, "name": "Boston Celtics"},
            },
            "scores": {"home": {"total": None}, "away": {"total": None}},
        },
        {
            "id": "1002",
            "date": date,
            "status": {"short": "NS", "long": "Scheduled"},
            "teams": {
                "home": {"id": 9, "name": "Golden State Warriors"},
                "away": {"id": 14, "name": "Miami Heat"},
            },
            "scores": {"home": {"total": None}, "away": {"total": None}},
        },
        {
            "id": "1003",
            "date": date,
            "status": {"short": "NS", "long": "Scheduled"},
            "teams": {
                "home": {"id": 24, "name": "Phoenix Suns"},
                "away": {"id": 7, "name": "Denver Nuggets"},
            },
            "scores": {"home": {"total": None}, "away": {"total": None}},
        },
    ]


def _mock_team_stats(team_id: int) -> dict:
    import random
    rng = random.Random(team_id)
    wins = rng.randint(20, 55)
    losses = rng.randint(10, 40)
    return {
        "team": {"id": team_id, "name": f"Team {team_id}"},
        "wins": {"all": {"total": wins}},
        "losses": {"all": {"total": losses}},
        "points": {"for": {"average": {"all": str(round(rng.uniform(105, 125), 1))}}},
        "games": wins + losses,
    }


def _mock_standings() -> list[dict]:
    teams = [
        {"id": 2, "name": "Boston Celtics"},
        {"id": 7, "name": "Denver Nuggets"},
        {"id": 9, "name": "Golden State Warriors"},
        {"id": 13, "name": "Los Angeles Lakers"},
        {"id": 14, "name": "Miami Heat"},
        {"id": 24, "name": "Phoenix Suns"},
    ]
    return [
        {
            "team": t,
            "wins": {"all": {"total": 45 - i * 4}},
            "losses": {"all": {"total": 20 + i * 4}},
        }
        for i, t in enumerate(teams)
    ]
