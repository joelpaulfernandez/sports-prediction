import httpx
from app.config import get_settings

BASE_URL = "https://v1.basketball.api-sports.io"


def _get_headers() -> dict:
    settings = get_settings()
    return {
        "x-apisports-key": settings.sports_api_key,
        "Accept": "application/json",
    }


async def get_upcoming_games(date: str) -> list[dict]:
    """Fetch NBA games for a given date (YYYY-MM-DD)."""
    headers = _get_headers()
    params = {
        "date": date,
        "league": "12",   # NBA league ID on api-sports
        "season": "2024-2025",
    }
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        try:
            response = await client.get("/games", headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("response", [])
        except httpx.HTTPStatusError as exc:
            print(f"API error fetching games: {exc.response.status_code}")
            return _mock_games(date)
        except httpx.RequestError as exc:
            print(f"Request error fetching games: {exc}")
            return _mock_games(date)


async def get_team_stats(team_id: int) -> dict:
    """Fetch recent stats for a team."""
    headers = _get_headers()
    params = {
        "id": team_id,
        "league": "12",
        "season": "2024-2025",
    }
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        try:
            response = await client.get("/teams/statistics", headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            responses = data.get("response", [])
            return responses[0] if responses else _mock_team_stats(team_id)
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            print(f"Error fetching team stats for {team_id}: {exc}")
            return _mock_team_stats(team_id)


async def get_standings() -> list[dict]:
    """Fetch current NBA standings."""
    headers = _get_headers()
    params = {
        "league": "12",
        "season": "2024-2025",
    }
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        try:
            response = await client.get("/standings", headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("response", [])
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            print(f"Error fetching standings: {exc}")
            return _mock_standings()


# ---------------------------------------------------------------------------
# Mock / fallback data so the app works without a valid API key
# ---------------------------------------------------------------------------

def _mock_games(date: str) -> list[dict]:
    return [
        {
            "id": 1001,
            "date": date,
            "status": {"short": "NS", "long": "Not Started"},
            "teams": {
                "home": {"id": 1, "name": "Los Angeles Lakers"},
                "away": {"id": 2, "name": "Boston Celtics"},
            },
            "scores": {"home": {"total": None}, "away": {"total": None}},
        },
        {
            "id": 1002,
            "date": date,
            "status": {"short": "NS", "long": "Not Started"},
            "teams": {
                "home": {"id": 3, "name": "Golden State Warriors"},
                "away": {"id": 4, "name": "Miami Heat"},
            },
            "scores": {"home": {"total": None}, "away": {"total": None}},
        },
        {
            "id": 1003,
            "date": date,
            "status": {"short": "NS", "long": "Not Started"},
            "teams": {
                "home": {"id": 5, "name": "Phoenix Suns"},
                "away": {"id": 6, "name": "Denver Nuggets"},
            },
            "scores": {"home": {"total": None}, "away": {"total": None}},
        },
    ]


def _mock_team_stats(team_id: int) -> dict:
    import random
    rng = random.Random(team_id)
    wins = rng.randint(20, 55)
    losses = rng.randint(10, 40)
    total = wins + losses
    home_wins = rng.randint(10, 30)
    home_losses = rng.randint(5, 15)
    return {
        "team": {"id": team_id, "name": f"Team {team_id}"},
        "wins": {"all": {"total": wins}, "home": {"total": home_wins}},
        "losses": {"all": {"total": losses}, "home": {"total": home_losses}},
        "points": {
            "for": {"average": {"all": str(round(rng.uniform(105, 125), 1))}},
        },
        "games": total,
    }


def _mock_standings() -> list[dict]:
    teams = [
        {"id": 1, "name": "Los Angeles Lakers"},
        {"id": 2, "name": "Boston Celtics"},
        {"id": 3, "name": "Golden State Warriors"},
        {"id": 4, "name": "Miami Heat"},
        {"id": 5, "name": "Phoenix Suns"},
        {"id": 6, "name": "Denver Nuggets"},
    ]
    standings = []
    for i, team in enumerate(teams):
        wins = 45 - i * 4
        losses = 20 + i * 4
        standings.append(
            {
                "team": team,
                "wins": {"all": {"total": wins}},
                "losses": {"all": {"total": losses}},
            }
        )
    return standings
