"""
F1 data pipeline — Jolpica (Ergast-compatible) API.

All data comes from Jolpica (free, no API key). FastF1 has been removed
to keep the Render 512MB memory budget: fastf1 pulls pyarrow + requests-cache
(~150MB) and was only used for FP2 data that is excluded from the model anyway.
"""

import time
import datetime
from typing import Optional

import httpx
import numpy as np
import pandas as pd

from app.services.cache import cache_get, cache_set

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JOLPICA_BASE = "https://api.jolpi.ca/ergast/f1"
TRAINING_SEASONS = list(range(2018, 2025))  # 2018–2024; update when new seasons complete


def current_season() -> int:
    """Return the current F1 season year. Called at request time, not import time."""
    return datetime.datetime.now(tz=datetime.timezone.utc).year


# Overtaking difficulty 1–10 (higher = harder to pass).
# Values derived from 2018–2024 season average overtakes-per-race data (F1 Stats).
# Safety car rates from historical incident frequency per circuit (2015–2024).
# These are opinionated starting estimates — update when new multi-year data is available.
# New circuits not in this map get neutral defaults (overtaking_difficulty=5.0, safety_car_rate=0.35).
CIRCUIT_METADATA: dict[str, dict] = {
    "monaco":            {"overtaking_difficulty": 9.5, "safety_car_rate": 0.65, "circuit_variance": "high",   "country": "Monaco"},
    "baku":              {"overtaking_difficulty": 5.5, "safety_car_rate": 0.72, "circuit_variance": "high",   "country": "Azerbaijan"},
    "singapore":         {"overtaking_difficulty": 8.0, "safety_car_rate": 0.68, "circuit_variance": "high",   "country": "Singapore"},
    "melbourne":         {"overtaking_difficulty": 5.0, "safety_car_rate": 0.48, "circuit_variance": "normal", "country": "Australia"},
    "shanghai":          {"overtaking_difficulty": 5.5, "safety_car_rate": 0.30, "circuit_variance": "normal", "country": "China"},
    "bahrain":           {"overtaking_difficulty": 4.0, "safety_car_rate": 0.28, "circuit_variance": "normal", "country": "Bahrain"},
    "jeddah":            {"overtaking_difficulty": 6.5, "safety_car_rate": 0.55, "circuit_variance": "high",   "country": "Saudi Arabia"},
    "imola":             {"overtaking_difficulty": 7.5, "safety_car_rate": 0.40, "circuit_variance": "normal", "country": "Italy"},
    "miami":             {"overtaking_difficulty": 5.0, "safety_car_rate": 0.38, "circuit_variance": "normal", "country": "USA"},
    "catalunya":         {"overtaking_difficulty": 6.0, "safety_car_rate": 0.25, "circuit_variance": "normal", "country": "Spain"},
    "villeneuve":        {"overtaking_difficulty": 5.0, "safety_car_rate": 0.45, "circuit_variance": "normal", "country": "Canada"},
    "red_bull_ring":     {"overtaking_difficulty": 3.5, "safety_car_rate": 0.35, "circuit_variance": "normal", "country": "Austria"},
    "silverstone":       {"overtaking_difficulty": 4.5, "safety_car_rate": 0.30, "circuit_variance": "normal", "country": "UK"},
    "hungaroring":       {"overtaking_difficulty": 7.0, "safety_car_rate": 0.28, "circuit_variance": "normal", "country": "Hungary"},
    "spa":               {"overtaking_difficulty": 3.0, "safety_car_rate": 0.55, "circuit_variance": "normal", "country": "Belgium"},
    "zandvoort":         {"overtaking_difficulty": 7.0, "safety_car_rate": 0.38, "circuit_variance": "normal", "country": "Netherlands"},
    "monza":             {"overtaking_difficulty": 3.0, "safety_car_rate": 0.40, "circuit_variance": "normal", "country": "Italy"},
    "suzuka":            {"overtaking_difficulty": 5.5, "safety_car_rate": 0.45, "circuit_variance": "normal", "country": "Japan"},
    "losail":            {"overtaking_difficulty": 4.5, "safety_car_rate": 0.20, "circuit_variance": "normal", "country": "Qatar"},
    "cota":              {"overtaking_difficulty": 4.5, "safety_car_rate": 0.42, "circuit_variance": "normal", "country": "USA"},
    "rodriguez":         {"overtaking_difficulty": 5.5, "safety_car_rate": 0.32, "circuit_variance": "normal", "country": "Mexico"},
    "interlagos":        {"overtaking_difficulty": 4.0, "safety_car_rate": 0.52, "circuit_variance": "normal", "country": "Brazil"},
    "las_vegas":         {"overtaking_difficulty": 5.0, "safety_car_rate": 0.50, "circuit_variance": "high",   "country": "USA"},
    "yas_marina":        {"overtaking_difficulty": 4.5, "safety_car_rate": 0.28, "circuit_variance": "normal", "country": "UAE"},
}

_CIRCUIT_KEY_MAP = {
    # Jolpica circuitId → our key
    "monaco":         "monaco",
    "baku":           "baku",
    "marina_bay":     "singapore",
    "albert_park":    "melbourne",
    "shanghai":       "shanghai",
    "bahrain":        "bahrain",
    "jeddah":         "jeddah",
    "imola":          "imola",
    "miami":          "miami",
    "catalunya":      "catalunya",
    "villeneuve":     "villeneuve",
    "red_bull_ring":  "red_bull_ring",
    "silverstone":    "silverstone",
    "hungaroring":    "hungaroring",
    "spa":            "spa",
    "zandvoort":      "zandvoort",
    "monza":          "monza",
    "suzuka":         "suzuka",
    "losail":         "losail",
    "americas":       "cota",
    "rodriguez":      "rodriguez",
    "interlagos":     "interlagos",
    "las_vegas":      "las_vegas",
    "yas_marina":     "yas_marina",
}

HIGH_VARIANCE_CIRCUITS = {"monaco", "baku", "singapore", "jeddah", "las_vegas"}


# ---------------------------------------------------------------------------
# Jolpica (Ergast-compatible) helpers
# ---------------------------------------------------------------------------

def _jolpica_get(path: str, timeout: int = 20, retries: int = 4) -> Optional[dict]:
    url = f"{JOLPICA_BASE}{path}.json?limit=100"
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url)
                if resp.status_code == 429:
                    wait = 2 ** attempt * 3  # 3, 6, 12, 24s
                    print(f"[f1_data] Rate limited — waiting {wait}s (attempt {attempt+1}/{retries})")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError:
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 2)
                continue
        except Exception as exc:
            print(f"[f1_data] Jolpica request failed: {path} — {exc}")
            return None
    print(f"[f1_data] Jolpica gave up after {retries} attempts: {path}")
    return None


def get_season_schedule(season: int) -> list[dict]:
    """Return all races for a season with circuit metadata."""
    key = f"f1:schedule:{season}"
    cached = cache_get(key)
    if cached is not None:
        return cached

    data = _jolpica_get(f"/{season}")
    if not data:
        return []

    races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    result = []
    for r in races:
        circuit_id = r.get("Circuit", {}).get("circuitId", "")
        circuit_key = _CIRCUIT_KEY_MAP.get(circuit_id, circuit_id.lower().replace(" ", "_"))
        meta = CIRCUIT_METADATA.get(circuit_key, {
            "overtaking_difficulty": 5.0,
            "safety_car_rate": 0.35,
            "circuit_variance": "normal",
            "country": r.get("Circuit", {}).get("Location", {}).get("country", ""),
        })
        result.append({
            "race_id":            f"{season}_r{r['round']}",
            "season":             season,
            "round":              int(r["round"]),
            "event":              r["raceName"],
            "circuit":            r.get("Circuit", {}).get("circuitName", ""),
            "circuit_id":         circuit_id,
            "circuit_key":        circuit_key,
            "circuit_country":    meta["country"],
            "circuit_variance":   meta["circuit_variance"],
            "race_date":          r["date"],
            "race_time_utc":      r.get("time"),
            "overtaking_difficulty": meta["overtaking_difficulty"],
            "safety_car_rate":    meta["safety_car_rate"],
        })

    # Cache upcoming schedule for 6h, past seasons for 24h
    ttl = 3600 * 6 if season == current_season() else 3600 * 24
    cache_set(key, result, ttl)
    return result


def get_upcoming_races(season: int = 0) -> list[dict]:
    """Return races not yet completed (race_date >= today)."""
    if season == 0:
        season = current_season()
    today = datetime.date.today().isoformat()
    return [r for r in get_season_schedule(season) if r["race_date"] >= today]


def get_race_result(season: int, round_num: int) -> Optional[pd.DataFrame]:
    """Fetch official race result from Jolpica. Returns driver finishing order."""
    key = f"f1:result:{season}:{round_num}"
    cached = cache_get(key)
    if cached is not None:
        return pd.DataFrame(cached)

    data = _jolpica_get(f"/{season}/{round_num}/results")
    if not data:
        return None

    results = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    if not results:
        return None

    rows = []
    for r in results[0].get("Results", []):
        rows.append({
            "driver_id":     r["Driver"]["driverId"],
            "driver_name":   f"{r['Driver']['givenName']} {r['Driver']['familyName']}",
            "driver_number": r["Driver"].get("permanentNumber", ""),
            "team":          r["Constructor"]["name"],
            "position":      int(r["position"]) if r["position"].isdigit() else 99,
            "grid":          int(r.get("grid", 0)),
            "status":        r.get("status", ""),
            "points":        float(r.get("points", 0)),
            "fastest_lap":   r.get("FastestLap", {}).get("Time", {}).get("time", ""),
        })

    df = pd.DataFrame(rows).sort_values("position").reset_index(drop=True)
    cache_set(key, df.to_dict("records"), ttl=3600 * 24 * 7)
    return df


def get_qualifying_result(season: int, round_num: int) -> Optional[pd.DataFrame]:
    """Fetch qualifying classification from Jolpica."""
    key = f"f1:quali:{season}:{round_num}"
    cached = cache_get(key)
    if cached is not None:
        return pd.DataFrame(cached)

    data = _jolpica_get(f"/{season}/{round_num}/qualifying")
    if not data:
        return None

    races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    if not races:
        return None

    rows = []
    for r in races[0].get("QualifyingResults", []):
        q1 = r.get("Q1", "")
        q2 = r.get("Q2", "")
        q3 = r.get("Q3", "")
        best_time = q3 or q2 or q1
        rows.append({
            "driver_id":     r["Driver"]["driverId"],
            "driver_name":   f"{r['Driver']['givenName']} {r['Driver']['familyName']}",
            "driver_number": r["Driver"].get("permanentNumber", ""),
            "team":          r["Constructor"]["name"],
            "quali_position": int(r["position"]),
            "q1_time":       q1,
            "q2_time":       q2,
            "q3_time":       q3,
            "best_time":     best_time,
        })

    df = pd.DataFrame(rows).sort_values("quali_position").reset_index(drop=True)
    df["quali_gap_s"] = _compute_quali_gaps(df["best_time"].tolist())
    cache_set(key, df.to_dict("records"), ttl=3600 * 12)
    return df


def _time_to_seconds(t: str) -> Optional[float]:
    if not t or t == "":
        return None
    try:
        if ":" in t:
            parts = t.split(":")
            return float(parts[0]) * 60 + float(parts[1])
        return float(t)
    except ValueError:
        return None


def _compute_quali_gaps(times: list[str]) -> list[float]:
    """Convert quali times to gap-to-pole in seconds. Pole = 0.0."""
    secs = [_time_to_seconds(t) for t in times]
    # Find pole time (first non-None)
    pole_time = next((s for s in secs if s is not None), None)
    if pole_time is None:
        return [float(i) for i in range(len(times))]
    gaps = []
    for i, s in enumerate(secs):
        if s is not None:
            gaps.append(round(s - pole_time, 3))
        else:
            # Driver eliminated — estimate gap based on position
            gaps.append(float(i) * 0.5)
    return gaps


def get_driver_season_dnf_rates(season: int) -> dict[str, float]:
    """DNF rate per driver for a season (fraction of races with mechanical/accident DNF)."""
    key = f"f1:dnf_rates:{season}"
    cached = cache_get(key)
    if cached is not None:
        return cached

    dnf_statuses = {"retired", "accident", "collision", "mechanical", "engine", "gearbox",
                    "hydraulics", "electrical", "brakes", "suspension", "driveshaft",
                    "power unit", "turbo", "exhaust", "wheel", "fire"}

    schedule = get_season_schedule(season)
    completed_rounds = []
    today = datetime.date.today().isoformat()
    for race in schedule:
        if race["race_date"] < today:
            completed_rounds.append(race["round"])

    if not completed_rounds:
        return {}

    driver_races: dict[str, int] = {}
    driver_dnfs: dict[str, int] = {}

    for round_num in completed_rounds:
        result = get_race_result(season, round_num)
        if result is None:
            continue
        for _, row in result.iterrows():
            did = row["driver_id"]
            driver_races[did] = driver_races.get(did, 0) + 1
            status_lower = str(row["status"]).lower()
            if any(s in status_lower for s in dnf_statuses):
                driver_dnfs[did] = driver_dnfs.get(did, 0) + 1
        time.sleep(0.1)

    rates = {
        did: round(driver_dnfs.get(did, 0) / driver_races[did], 4)
        for did in driver_races
        if driver_races[did] > 0
    }

    cache_set(key, rates, ttl=3600 * 6)
    return rates


def get_driver_rolling_form(
    driver_id: str,
    season: int,
    current_round: int,
    n_races: int = 5,
) -> dict:
    """
    Exponentially-weighted avg finish position and recent form stats.
    Uses only races completed BEFORE current_round (no leakage).
    """
    key = f"f1:form:{driver_id}:{season}:{current_round}:{n_races}"
    cached = cache_get(key)
    if cached is not None:
        return cached

    past_rounds = list(range(max(1, current_round - n_races), current_round))
    positions = []
    dnfs = 0

    for r in past_rounds:
        result = get_race_result(season, r)
        if result is None:
            continue
        row = result[result["driver_id"] == driver_id]
        if row.empty:
            continue
        pos = int(row.iloc[0]["position"])
        status = str(row.iloc[0]["status"]).lower()
        if pos >= 99 or "retire" in status or "accident" in status or "mechanical" in status:
            positions.append(20)
            dnfs += 1
        else:
            positions.append(pos)

    if not positions:
        out = {"rolling_avg_finish_5": 10.0, "recent_dnf_count": 0, "races_counted": 0}
        cache_set(key, out, ttl=3600 * 6)
        return out

    # Exponential weights — more recent races matter more
    weights = np.exp(np.linspace(0, 1, len(positions)))
    weights /= weights.sum()
    weighted_avg = float(np.dot(positions, weights))

    out = {
        "rolling_avg_finish_5": round(weighted_avg, 2),
        "recent_dnf_count":     dnfs,
        "races_counted":        len(positions),
    }
    cache_set(key, out, ttl=3600 * 6)
    return out


def get_constructor_pit_stop_avg(team: str, season: int, current_round: int) -> float:
    """Average pit stop time (seconds) for a constructor over last 5 races."""
    key = f"f1:pitstop:{team}:{season}:{current_round}"
    cached = cache_get(key)
    if cached is not None:
        return cached

    past_rounds = list(range(max(1, current_round - 5), current_round))
    all_times: list[float] = []

    for r in past_rounds:
        data = _jolpica_get(f"/{season}/{r}/pitstops")
        if not data:
            continue
        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        if not races:
            continue
        for stop in races[0].get("PitStops", []):
            if stop.get("constructorId", "") == team.lower().replace(" ", "_"):
                t = _time_to_seconds(stop.get("duration", ""))
                if t and 15 < t < 60:
                    all_times.append(t)
        time.sleep(0.1)

    avg = round(float(np.median(all_times)) if all_times else 25.0, 2)
    cache_set(key, avg, ttl=3600 * 12)
    return avg


def get_h2h_teammate_gap(season: int, round_num: int) -> dict[str, float]:
    """
    Teammate qualifying gap per driver.
    Positive = faster than teammate (gap in seconds).
    """
    key = f"f1:h2h_quali:{season}:{round_num}"
    cached = cache_get(key)
    if cached is not None:
        return cached

    quali = get_qualifying_result(season, round_num)
    if quali is None:
        return {}

    gaps: dict[str, float] = {}
    for team in quali["team"].unique():
        team_drivers = quali[quali["team"] == team]
        if len(team_drivers) < 2:
            continue
        sorted_drivers = team_drivers.sort_values("quali_gap_s")
        ids = sorted_drivers["driver_id"].tolist()
        g = sorted_drivers["quali_gap_s"].tolist()
        # Faster driver gets positive gap (advantage over teammate)
        gaps[ids[0]] = round(g[1] - g[0], 3)
        gaps[ids[1]] = round(g[0] - g[1], 3)

    cache_set(key, gaps, ttl=3600 * 12)
    return gaps


# ---------------------------------------------------------------------------
# Penalty-adjusted grid
# ---------------------------------------------------------------------------

def get_grid_positions(season: int, round_num: int) -> dict[str, int]:
    """
    Grid positions after penalties are applied.
    Falls back to qualifying order if race result grid not yet available.
    """
    key = f"f1:grid:{season}:{round_num}"
    cached = cache_get(key)
    if cached is not None:
        return cached

    # Try race result first (has final grid after penalties)
    result = get_race_result(season, round_num)
    if result is not None and "grid" in result.columns:
        grids = {row["driver_id"]: int(row["grid"]) for _, row in result.iterrows() if row["grid"] > 0}
        if grids:
            cache_set(key, grids, ttl=3600 * 24)
            return grids

    # Fall back to qualifying order
    quali = get_qualifying_result(season, round_num)
    if quali is None:
        return {}

    grids = {row["driver_id"]: int(row["quali_position"]) for _, row in quali.iterrows()}
    cache_set(key, grids, ttl=3600 * 3)
    return grids
