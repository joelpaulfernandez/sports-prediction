"""
F1 prediction API routes.

GET  /f1/races                        — upcoming race weekends
GET  /f1/races/{race_id}/predictions  — cached prediction JSON
POST /f1/races/{race_id}/refresh      — trigger data pull + re-predict (admin only)
GET  /f1/accuracy                     — historical model accuracy stats
GET  /f1/recent-results               — last N races: predicted vs actual
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header

from app.config import get_settings
from app.schemas.f1_prediction import (
    F1RacePrediction, F1DriverPrediction, F1PredictionReason,
    F1AccuracyStats, F1AccuracyBreakdown,
)
from app.services import f1_data
from app.services.f1_features import build_race_feature_matrix
from app.services.f1_explainability import generate_f1_reasons
from app.services.f1_prediction_engine import get_f1_prediction_engine
from app.services.cache import cache_get, cache_set

router = APIRouter(prefix="/f1", tags=["f1"])

# TTL constants (seconds)
_TTL_BUILDUP = 3600      # 1h during race weekend build-up
_TTL_POST_QUALI = 3600   # 1h after qualifying (grid is locked)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/recent-results", response_model=list[dict])
async def get_recent_results(n: int = 5):
    """Return last N completed races with predicted vs actual outcomes."""
    return await asyncio.to_thread(_build_recent_results, min(n, 10))


@router.get("/races", response_model=list[dict])
async def get_races():
    """List upcoming F1 race weekends for the current season."""
    races = await asyncio.to_thread(f1_data.get_upcoming_races, f1_data.current_season())
    return [
        {
            "race_id":          r["race_id"],
            "event":            r["event"],
            "circuit":          r["circuit"],
            "circuit_country":  r["circuit_country"],
            "circuit_variance": r["circuit_variance"],
            "race_date":        r["race_date"],
            "race_time_utc":    r.get("race_time_utc"),
            "round":            r["round"],
            "season":           r["season"],
        }
        for r in races
    ]


@router.get("/races/{race_id}/predictions", response_model=F1RacePrediction)
async def get_race_predictions(race_id: str):
    """Return prediction for a race. Served from Redis cache when available."""
    cached = cache_get(f"f1:pred:{race_id}")
    if cached is not None:
        return F1RacePrediction(**cached)

    pred = await _build_race_prediction(race_id)
    if pred is None:
        raise HTTPException(status_code=404, detail=f"Race {race_id} not found or data unavailable.")
    return pred


@router.post("/races/{race_id}/refresh")
async def refresh_race_prediction(
    race_id: str,
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
):
    """Force re-pull of race data and rebuild prediction. Requires X-Admin-Token header."""
    settings = get_settings()
    if x_admin_token != settings.f1_admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token.")

    pred = await _build_race_prediction(race_id, force=True)
    if pred is None:
        raise HTTPException(status_code=404, detail=f"Race {race_id} not found or data unavailable.")

    return {"status": "refreshed", "race_id": race_id, "predictions": len(pred.predictions)}


@router.get("/accuracy", response_model=F1AccuracyStats)
async def get_f1_accuracy():
    """Historical model accuracy broken down by circuit type and confidence."""
    return await asyncio.to_thread(_compute_accuracy_stats)


# ---------------------------------------------------------------------------
# Prediction builder
# ---------------------------------------------------------------------------

async def _build_race_prediction(race_id: str, force: bool = False) -> Optional[F1RacePrediction]:
    """
    Build a full race prediction from qualifying + form data.

    FP2 data is intentionally excluded from the feature matrix: the model was
    trained without FP2 pace (fp2_pace=None → constructor_pace_delta and
    tyre_deg_rate both 0.0). Passing real FP2 numbers at inference would feed
    the model values it never saw during training. Re-enable once the model is
    retrained with FP2 data included.
    """
    season, round_num = _parse_race_id(race_id)
    if season is None:
        return None

    schedule = await asyncio.to_thread(f1_data.get_season_schedule, season)
    race_meta = next((r for r in schedule if r["race_id"] == race_id), None)
    if race_meta is None:
        return None

    # Fetch qualifying + grid data concurrently (FP2 intentionally omitted — see docstring)
    quali, grid, dnf_rates, teammate_gaps = await asyncio.gather(
        asyncio.to_thread(f1_data.get_qualifying_result, season, round_num),
        asyncio.to_thread(f1_data.get_grid_positions, season, round_num),
        asyncio.to_thread(f1_data.get_driver_season_dnf_rates, season),
        asyncio.to_thread(f1_data.get_h2h_teammate_gap, season, round_num),
    )

    if quali is None or quali.empty:
        return None

    # Rolling form per driver (races before this round only — no leakage)
    form_tasks = {
        did: asyncio.to_thread(f1_data.get_driver_rolling_form, did, season, round_num, 5)
        for did in quali["driver_id"].unique()
    }
    form_results = await asyncio.gather(*form_tasks.values())
    rolling_forms = dict(zip(form_tasks.keys(), form_results))

    circuit_key = race_meta.get("circuit_key", "")
    circuit_meta = f1_data.CIRCUIT_METADATA.get(circuit_key, {
        "overtaking_difficulty": 5.0,
        "safety_car_rate": 0.35,
        "circuit_variance": "normal",
        "country": race_meta.get("circuit_country", ""),
    })

    driver_df, X = build_race_feature_matrix(
        quali_df=quali,
        grid_positions=grid or {},
        fp2_pace=None,          # excluded — see docstring above
        dnf_rates=dnf_rates or {},
        rolling_forms=rolling_forms,
        teammate_gaps=teammate_gaps or {},
        circuit_meta=circuit_meta,
    )

    if driver_df.empty:
        return None

    engine = get_f1_prediction_engine()

    race_predictions = engine.predict_race(
        driver_df=driver_df,
        X=X,
        circuit_meta=circuit_meta,
        circuit_name=race_meta.get("circuit", "this circuit"),
        compound="medium",      # no FP2 data → default compound
    )

    driver_preds: list[F1DriverPrediction] = []
    for rp in race_predictions[:20]:
        reasons_text = generate_f1_reasons(
            driver=rp["driver_name"],
            team=rp["team"],
            features=rp["features"],
            model=engine.ranker,
            circuit_name=race_meta.get("circuit", "this circuit"),
            compound="medium",
            overtaking_difficulty=rp.get("overtaking_difficulty", 5.0),
            n_reasons=3 if rp["position"] == 1 else 0,
        )

        driver_preds.append(F1DriverPrediction(
            position=rp["position"],
            driver=rp["driver_name"],
            driver_id=rp["driver_id"],
            team=rp["team"],
            driver_number=rp.get("driver_number"),
            win_prob=rp["win_prob"],
            podium_prob=rp["podium_prob"],
            confidence_score=rp["confidence_score"],
            reasons=[F1PredictionReason(text=t) for t in reasons_text] if reasons_text else [],
            quali_position=rp.get("quali_position"),
            grid_position=rp.get("grid_position"),
        ))

    model_conf = _model_confidence(driver_preds[0].win_prob if driver_preds else 0.3, circuit_meta)

    pred = F1RacePrediction(
        race_id=race_id,
        event=race_meta["event"],
        circuit=race_meta["circuit"],
        circuit_key=circuit_key,
        circuit_country=race_meta["circuit_country"],
        race_date=race_meta["race_date"],
        race_time_utc=race_meta.get("race_time_utc"),
        season=race_meta["season"],
        round=race_meta["round"],
        predictions=driver_preds,
        circuit_variance=race_meta.get("circuit_variance", "normal"),
        model_confidence=model_conf,
        model_version=engine.model_version,
        data_freshness=datetime.now(tz=timezone.utc).isoformat(),
    )

    ttl = _pick_ttl(race_meta)
    if ttl > 0:
        cache_set(f"f1:pred:{race_id}", pred.model_dump(), ttl=ttl)

    _persist_f1_prediction(pred)

    return pred


# ---------------------------------------------------------------------------
# Accuracy resolution — runs at startup and nightly to score completed races
# ---------------------------------------------------------------------------

def resolve_f1_accuracy() -> int:
    """
    Compare stored predictions against actual race results and write rows to
    f1_accuracy_log. Called at startup and after each race weekend.
    Returns the number of newly resolved races.
    """
    try:
        from app.services.db import get_db
        db = get_db()

        # Fetch unresolved predictions (no matching accuracy log entry)
        preds = db.table("f1_predictions").select("*").execute().data or []
        resolved_ids = {
            r["race_id"]
            for r in (db.table("f1_accuracy_log").select("race_id").execute().data or [])
        }
        unresolved = [p for p in preds if p["race_id"] not in resolved_ids]
    except Exception as exc:
        print(f"[f1_accuracy] DB error: {exc}")
        return 0

    import datetime as dt
    today = dt.date.today().isoformat()
    resolved = 0

    for pred in unresolved:
        race_date = pred.get("race_date", "9999-99-99")
        if race_date >= today:
            continue  # race hasn't happened yet

        season, round_num = _parse_race_id(pred["race_id"])
        if season is None:
            continue

        try:
            result = f1_data.get_race_result(season, round_num)
            if result is None or result.empty:
                continue

            actual_winner_id = result.iloc[0]["driver_id"]
            winner_correct = pred["predicted_winner_id"] == actual_winner_id

            actual_podium_ids = {
                row["driver_id"]
                for _, row in result.iterrows()
                if int(row["position"]) <= 3
            }
            podium_correct = sum(
                1 for d_id in [pred.get("predicted_winner_id")]
                if d_id in actual_podium_ids
            )

            # Spearman between stored prediction order and actual result
            rank_correlation = None
            try:
                from scipy.stats import spearmanr
                import numpy as np
                # We only have the winner stored; skip Spearman here — full
                # rank is computed in /recent-results which uses live data.
            except Exception:
                pass

            db.table("f1_accuracy_log").upsert(
                {
                    "race_id":          pred["race_id"],
                    "event":            pred.get("event", ""),
                    "season":           pred.get("season"),
                    "circuit_key":      pred.get("circuit_key", ""),
                    "circuit_variance": pred.get("circuit_variance", "normal"),
                    "race_date":        race_date,
                    "winner_correct":   winner_correct,
                    "podium_correct":   podium_correct,
                    "confidence_score": pred.get("confidence_score", 0),
                    "model_version":    pred.get("model_version", ""),
                    "rank_correlation": rank_correlation,
                    "resolved_at":      datetime.now(tz=timezone.utc).isoformat(),
                },
                on_conflict="race_id",
            ).execute()
            resolved += 1
        except Exception as exc:
            print(f"[f1_accuracy] Failed to resolve {pred['race_id']}: {exc}")
            continue

    return resolved


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_race_id(race_id: str) -> tuple[Optional[int], Optional[int]]:
    """Parse '2025_r5' → (2025, 5). Returns (None, None) on bad input."""
    try:
        parts = race_id.split("_r")
        return int(parts[0]), int(parts[1])
    except (IndexError, ValueError):
        return None, None


def _pick_ttl(race_meta: dict) -> int:
    """
    Select Redis TTL (seconds) based on how close we are to race start.
    Returns 0 within 30 min of the race — cache is locked, no update.
    """
    import datetime as dt
    race_date = race_meta.get("race_date", "")
    race_time = race_meta.get("race_time_utc", "")

    if not race_date:
        return _TTL_BUILDUP

    try:
        if race_time:
            race_dt_str = f"{race_date}T{race_time}".rstrip("Z") + "+00:00"
            race_dt = dt.datetime.fromisoformat(race_dt_str)
        else:
            race_dt = dt.datetime.fromisoformat(f"{race_date}T13:00:00+00:00")

        minutes_to_race = (race_dt - dt.datetime.now(tz=dt.timezone.utc)).total_seconds() / 60

        if minutes_to_race <= 30:
            return 0  # locked — no cache update 30 min before lights out
        return _TTL_BUILDUP
    except Exception:
        return _TTL_BUILDUP


def _detect_compound(fp2_pace) -> str:
    """Return the dominant tyre compound from FP2 long-run data, or 'medium'."""
    if fp2_pace is None or fp2_pace.empty:
        return "medium"
    if "compound" not in fp2_pace.columns:
        return "medium"
    counts = fp2_pace["compound"].value_counts()
    return str(counts.index[0]).lower() if len(counts) > 0 else "medium"


def _model_confidence(win_prob: float, circuit_meta: dict) -> str:
    """
    Translate win probability into a human-readable confidence tier.
    Thresholds are lower for high-variance circuits (Monaco, Baku, Singapore)
    because genuine prediction difficulty is higher there.
    """
    is_high_var = circuit_meta.get("circuit_variance", "normal") == "high"
    threshold_high = 0.45 if not is_high_var else 0.35
    threshold_med = 0.30 if not is_high_var else 0.22
    if win_prob >= threshold_high:
        return "high"
    if win_prob >= threshold_med:
        return "medium"
    return "low"


def _persist_f1_prediction(pred: F1RacePrediction) -> None:
    """
    Write predicted winner to Supabase so it can be scored after the race.
    Silently skips if DB is unavailable — predictions still serve from cache.
    """
    try:
        from app.services.db import get_db
        if not pred.predictions:
            return
        top = pred.predictions[0]
        db = get_db()
        db.table("f1_predictions").upsert(
            {
                "race_id":             pred.race_id,
                "event":               pred.event,
                "season":              pred.season,
                "round":               pred.round,
                "circuit_key":         pred.circuit_key,
                "circuit_variance":    pred.circuit_variance,
                "predicted_winner":    top.driver,
                "predicted_winner_id": top.driver_id,
                "win_prob":            top.win_prob,
                "confidence_score":    top.confidence_score,
                "model_version":       pred.model_version,
                "timestamp":           datetime.now(tz=timezone.utc).isoformat(),
            },
            on_conflict="race_id",
        ).execute()
    except Exception as exc:
        print(f"[f1] Could not persist prediction: {exc}")


# ---------------------------------------------------------------------------
# Accuracy computation
# ---------------------------------------------------------------------------

def _compute_accuracy_stats() -> F1AccuracyStats:
    """Pull resolved predictions from f1_accuracy_log and compute breakdowns."""
    try:
        from app.services.db import get_db
        db = get_db()
        rows = db.table("f1_accuracy_log").select("*").execute().data or []
    except Exception:
        rows = []

    empty = F1AccuracyBreakdown(
        total=0, winner_correct=0, podium_2of3=0,
        winner_accuracy=0.0, podium_accuracy=0.0,
    )

    if not rows:
        return F1AccuracyStats(
            last_3_races=empty, current_season=empty,
            permanent_circuits=empty, street_circuits=empty,
            high_confidence=empty, low_confidence=empty,
            last_updated=datetime.now(tz=timezone.utc).isoformat(),
        )

    import datetime as dt
    current_year = dt.datetime.now(tz=dt.timezone.utc).year
    rows_sorted = sorted(rows, key=lambda r: r.get("race_date", ""), reverse=True)
    high_var_keys = f1_data.HIGH_VARIANCE_CIRCUITS

    def _breakdown(subset: list[dict]) -> F1AccuracyBreakdown:
        if not subset:
            return empty
        total = len(subset)
        winner_correct = sum(1 for r in subset if r.get("winner_correct", False))
        podium_total = sum(int(r.get("podium_correct", 0)) for r in subset)
        return F1AccuracyBreakdown(
            total=total,
            winner_correct=winner_correct,
            podium_2of3=sum(1 for r in subset if int(r.get("podium_correct", 0)) >= 2),
            winner_accuracy=round(winner_correct / total, 4),
            podium_accuracy=round(podium_total / (total * 3), 4),
            avg_rank_correlation=_safe_mean([r.get("rank_correlation") for r in subset]),
        )

    return F1AccuracyStats(
        last_3_races=_breakdown(rows_sorted[:3]),
        current_season=_breakdown([r for r in rows if str(r.get("season", "")) == str(current_year)]),
        permanent_circuits=_breakdown([r for r in rows if r.get("circuit_key", "") not in high_var_keys]),
        street_circuits=_breakdown([r for r in rows if r.get("circuit_key", "") in high_var_keys]),
        high_confidence=_breakdown([r for r in rows if int(r.get("confidence_score", 0)) >= 70]),
        low_confidence=_breakdown([r for r in rows if int(r.get("confidence_score", 0)) < 55]),
        last_updated=datetime.now(tz=timezone.utc).isoformat(),
    )


def _safe_mean(vals: list) -> Optional[float]:
    """Return mean of non-None values, or None if list is empty."""
    clean = [float(v) for v in vals if v is not None]
    return round(sum(clean) / len(clean), 4) if clean else None


# ---------------------------------------------------------------------------
# Recent results builder
# ---------------------------------------------------------------------------

def _build_recent_results(n: int = 5) -> list[dict]:
    """
    For the last N completed races: re-run the pre-race prediction (qualifying
    data only) and compare to the actual result. Returns structured comparison
    dicts for the frontend to render side-by-side.
    """
    import datetime as dt
    import numpy as np

    season = f1_data.current_season()
    schedule = f1_data.get_season_schedule(season)
    today = dt.date.today().isoformat()
    completed = sorted(
        [r for r in schedule if r["race_date"] < today],
        key=lambda r: r["round"],
        reverse=True,
    )[:n]

    dnf_rates = f1_data.get_driver_season_dnf_rates(season)

    from app.services.f1_prediction_engine import F1PredictionEngine
    engine = F1PredictionEngine()

    results = []
    for race in completed:
        round_num = race["round"]
        try:
            quali = f1_data.get_qualifying_result(season, round_num)
            result = f1_data.get_race_result(season, round_num)
            grid = f1_data.get_grid_positions(season, round_num)
            gaps = f1_data.get_h2h_teammate_gap(season, round_num)

            if quali is None or result is None:
                continue

            rolling_forms: dict = {}
            for did in quali["driver_id"].unique():
                rolling_forms[did] = f1_data.get_driver_rolling_form(did, season, round_num, 5)

            circuit_key = f1_data._CIRCUIT_KEY_MAP.get(race.get("circuit_id", ""), race.get("circuit_key", ""))
            circuit_meta = f1_data.CIRCUIT_METADATA.get(circuit_key, {
                "overtaking_difficulty": 5.0, "safety_car_rate": 0.35, "circuit_variance": "normal",
            })

            driver_df, X = build_race_feature_matrix(
                quali_df=quali, grid_positions=grid or {},
                fp2_pace=None,          # consistent with training — see _build_race_prediction
                dnf_rates=dnf_rates or {},
                rolling_forms=rolling_forms, teammate_gaps=gaps or {},
                circuit_meta=circuit_meta,
            )

            if driver_df.empty:
                continue

            preds = engine.predict_race(driver_df, X, circuit_meta)

            actual_top = result.head(10)
            actual_pos = {row["driver_id"]: int(row["position"]) for _, row in result.iterrows()}

            pred_winner_id = preds[0]["driver_id"]
            actual_winner_id = result.iloc[0]["driver_id"]
            winner_correct = pred_winner_id == actual_winner_id

            pred_podium_ids = {p["driver_id"] for p in preds[:3]}
            actual_podium_ids = {row["driver_id"] for _, row in result.iterrows() if row["position"] <= 3}
            podium_overlap = len(pred_podium_ids & actual_podium_ids)

            spearman = None
            try:
                from scipy.stats import spearmanr
                driver_ids = driver_df["driver_id"].tolist()
                pred_ranks = {p["driver_id"]: p["position"] for p in preds}
                common = [d for d in driver_ids if d in actual_pos and d in pred_ranks]
                if len(common) >= 5:
                    corr, _ = spearmanr(
                        [pred_ranks[d] for d in common],
                        [actual_pos[d] for d in common],
                    )
                    spearman = round(float(corr), 3) if not np.isnan(corr) else None
            except Exception:
                pass

            results.append({
                "race_id":          race["race_id"],
                "event":            race["event"],
                "circuit":          race["circuit"],
                "circuit_country":  race["circuit_country"],
                "circuit_variance": race["circuit_variance"],
                "race_date":        race["race_date"],
                "round":            race["round"],
                "season":           race["season"],
                "winner_correct":   winner_correct,
                "podium_overlap":   podium_overlap,
                "spearman":         spearman,
                "model_version":    engine.model_version,
                "predicted": [
                    {
                        "position":    p["position"],
                        "driver":      p["driver_name"],
                        "driver_id":   p["driver_id"],
                        "team":        p["team"],
                        "win_prob":    round(p["win_prob"], 4),
                        "podium_prob": round(p["podium_prob"], 4),
                    }
                    for p in preds[:10]
                ],
                "actual": [
                    {
                        "position":  int(row["position"]),
                        "driver":    row["driver_name"],
                        "driver_id": row["driver_id"],
                        "team":      row["team"],
                        "status":    row.get("status", "Finished"),
                    }
                    for _, row in actual_top.iterrows()
                ],
            })
        except Exception as exc:
            print(f"[f1] recent-results failed for R{round_num}: {exc}")
            continue

    return results
