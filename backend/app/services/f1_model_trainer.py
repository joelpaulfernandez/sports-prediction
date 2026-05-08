"""
F1 model training pipeline.

Trains XGBRanker (rank:pairwise) on 2018-2023 seasons.
Validates on 2024 as holdout. Persists artifact to f1_model.pkl.

Leakage protection:
- Only uses qualifying and FP2 data (available pre-race)
- Rolling form computed from races BEFORE current round only
- No race-day telemetry
"""

import os
import time
import datetime
from typing import Optional

import numpy as np
import pandas as pd

from app.services import f1_data
from app.services.f1_features import (
    build_race_feature_matrix, position_to_label, F1_FEATURE_NAMES, N_FEATURES
)
from app.config import get_settings

TRAINING_SEASONS = f1_data.TRAINING_SEASONS
VALIDATION_SEASON = 2024
F1_MODEL_PATH_KEY = "f1_model_path"


def get_f1_model_path() -> str:
    settings = get_settings()
    base = os.path.dirname(settings.model_path)
    return os.path.join(base, "f1_model.pkl")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def train_f1_and_save(
    model_path: Optional[str] = None,
    seasons: Optional[list[int]] = None,
) -> dict:
    """
    Train XGBRanker on F1 seasons and save artifact.
    Returns metadata dict or empty dict on failure.
    """
    try:
        import xgboost as xgb
        from scipy.stats import spearmanr
    except ImportError as exc:
        print(f"[f1_trainer] Missing dependency: {exc}")
        return {}

    if model_path is None:
        model_path = get_f1_model_path()
    if seasons is None:
        seasons = TRAINING_SEASONS

    all_X: list[np.ndarray] = []
    all_y: list[int] = []
    all_groups: list[int] = []

    for season in seasons:
        print(f"[f1_trainer] Processing {season}…")
        X_s, y_s, groups_s = _build_season_examples(season)
        if len(X_s) > 0:
            all_X.append(X_s)
            all_y.extend(y_s)
            all_groups.extend(groups_s)
        print(f"[f1_trainer]   → {sum(groups_s)} training examples across {len(groups_s)} races")
        time.sleep(0.5)

    if not all_X:
        print("[f1_trainer] No training data — aborting.")
        return {}

    X = np.vstack(all_X).astype(np.float32)
    y = np.array(all_y, dtype=np.int32)
    groups = np.array(all_groups, dtype=np.int32)

    print(f"[f1_trainer] Total examples: {len(X)} across {len(groups)} races")

    ranker = xgb.XGBRanker(
        objective="rank:pairwise",
        n_estimators=400,
        max_depth=4,
        learning_rate=0.04,
        subsample=0.80,
        colsample_bytree=0.80,
        min_child_weight=4,
        gamma=0.5,
        reg_alpha=0.1,
        reg_lambda=1.5,
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    )

    ranker.fit(X, y, group=groups)

    # Evaluate on validation season (2024)
    print(f"[f1_trainer] Evaluating on {VALIDATION_SEASON}…")
    val_metrics = _evaluate_season(ranker, VALIDATION_SEASON)
    print(f"[f1_trainer] Val metrics: {val_metrics}")

    importance = dict(zip(F1_FEATURE_NAMES, ranker.feature_importances_.tolist()))
    top5 = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"[f1_trainer] Top features: {top5}")

    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    try:
        import joblib
    except ImportError:
        print("[f1_trainer] joblib not available — model not saved.")
        return {}

    artifact = {
        "ranker": ranker,
        "feature_names": F1_FEATURE_NAMES,
        "n_features": N_FEATURES,
        "training_seasons": seasons,
        "n_training_examples": int(len(X)),
        "n_training_races": int(len(groups)),
        "validation_metrics": val_metrics,
        "feature_importance": importance,
        "trained_at": datetime.datetime.utcnow().isoformat(),
    }
    joblib.dump(artifact, model_path)
    print(f"[f1_trainer] Saved to {model_path}")

    return {
        "n_examples": int(len(X)),
        "n_races": int(len(groups)),
        "validation_metrics": val_metrics,
        "trained_at": artifact["trained_at"],
    }


# ---------------------------------------------------------------------------
# Season example builder
# ---------------------------------------------------------------------------

def _build_season_examples(season: int) -> tuple[np.ndarray, list[int], list[int]]:
    """Build (X, labels, groups) for all races in a season."""
    schedule = f1_data.get_season_schedule(season)
    today = datetime.date.today().isoformat()

    # Only completed races
    completed = [r for r in schedule if r["race_date"] < today]
    if not completed:
        return np.empty((0, N_FEATURES)), [], []

    X_parts: list[np.ndarray] = []
    y_parts: list[int] = []
    group_sizes: list[int] = []

    dnf_rates = f1_data.get_driver_season_dnf_rates(season)

    for race in completed:
        round_num = race["round"]

        try:
            X_race, y_race = _build_race_examples(season, round_num, race, dnf_rates)
        except Exception as exc:
            print(f"[f1_trainer] Skipping {season} R{round_num}: {exc}")
            continue

        if len(X_race) < 3:
            continue

        X_parts.append(X_race)
        y_parts.extend(y_race)
        group_sizes.append(len(X_race))
        time.sleep(1.0)

    if not X_parts:
        return np.empty((0, N_FEATURES)), [], []

    return np.vstack(X_parts).astype(np.float32), y_parts, group_sizes


def _build_race_examples(
    season: int,
    round_num: int,
    race_meta: dict,
    dnf_rates: dict[str, float],
) -> tuple[np.ndarray, list[int]]:
    """Build feature matrix + labels for one race."""
    quali = f1_data.get_qualifying_result(season, round_num)
    result = f1_data.get_race_result(season, round_num)

    if quali is None or result is None:
        return np.empty((0, N_FEATURES)), []

    grid = f1_data.get_grid_positions(season, round_num)
    # Skip FP2 during training — FastF1 downloads take 30-60 min for 6 seasons.
    # FP2 features default to 0.0; model learns from quali/form/circuit signals only.
    # FP2 is still used at inference time for upcoming races.
    fp2_pace = None
    teammate_gaps = f1_data.get_h2h_teammate_gap(season, round_num)

    # Rolling form: compute for each driver BEFORE this round
    rolling_forms: dict[str, dict] = {}
    for did in quali["driver_id"].unique():
        rolling_forms[did] = f1_data.get_driver_rolling_form(
            did, season, round_num, n_races=5
        )

    circuit_meta = f1_data.CIRCUIT_METADATA.get(
        f1_data._CIRCUIT_KEY_MAP.get(race_meta.get("circuit_id", ""), ""),
        {"overtaking_difficulty": 5.0, "safety_car_rate": 0.35, "circuit_variance": "normal"}
    )

    driver_df, X = build_race_feature_matrix(
        quali_df=quali,
        grid_positions=grid,
        fp2_pace=fp2_pace,
        dnf_rates=dnf_rates,
        rolling_forms=rolling_forms,
        teammate_gaps=teammate_gaps,
        circuit_meta=circuit_meta,
    )

    if driver_df.empty:
        return np.empty((0, N_FEATURES)), []

    # Build labels from actual race results
    result_pos = {row["driver_id"]: int(row["position"]) for _, row in result.iterrows()}
    n_drivers = len(driver_df)

    y = []
    valid_mask = []
    for i, row in driver_df.iterrows():
        did = row["driver_id"]
        pos = result_pos.get(did, n_drivers + 1)
        pos = min(pos, n_drivers)  # cap at n_drivers for DNFs
        y.append(position_to_label(pos, n_drivers))
        valid_mask.append(True)

    return X[valid_mask], y


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def _evaluate_season(ranker, season: int) -> dict:
    """Evaluate ranker on a season. Returns accuracy metrics."""
    try:
        from scipy.stats import spearmanr
        from sklearn.metrics import brier_score_loss
    except ImportError:
        return {}

    schedule = f1_data.get_season_schedule(season)
    today = datetime.date.today().isoformat()
    completed = [r for r in schedule if r["race_date"] < today]

    if not completed:
        return {}

    dnf_rates = f1_data.get_driver_season_dnf_rates(season)
    winner_correct = 0
    podium_correct_total = 0
    spearman_scores: list[float] = []
    total_races = 0

    for race in completed:
        round_num = race["round"]
        try:
            X_race, y_race = _build_race_examples(season, round_num, race, dnf_rates)
        except Exception:
            continue

        if len(X_race) < 3:
            continue

        quali = f1_data.get_qualifying_result(season, round_num)
        result = f1_data.get_race_result(season, round_num)
        if quali is None or result is None:
            continue

        scores = ranker.predict(X_race)
        predicted_order = np.argsort(-scores)  # descending

        # Top-1 accuracy
        actual_winner_pos = 0  # index of the actual winner
        actual_positions = {row["driver_id"]: int(row["position"]) for _, row in result.iterrows()}
        driver_ids = quali["driver_id"].tolist()

        winner_idx = None
        for i, did in enumerate(driver_ids):
            if actual_positions.get(did, 99) == 1:
                winner_idx = i
                break

        if winner_idx is not None and predicted_order[0] == winner_idx:
            winner_correct += 1

        # Podium: count correctly predicted podium finishers (top 3)
        predicted_podium = set(predicted_order[:3])
        actual_podium = set()
        for i, did in enumerate(driver_ids):
            if actual_positions.get(did, 99) <= 3:
                actual_podium.add(i)
        overlap = len(predicted_podium & actual_podium)
        podium_correct_total += overlap

        # Spearman rank correlation
        predicted_ranks = np.argsort(np.argsort(-scores)) + 1
        actual_ranks = np.array([actual_positions.get(did, 20) for did in driver_ids])
        corr, _ = spearmanr(predicted_ranks, actual_ranks)
        if not np.isnan(corr):
            spearman_scores.append(float(corr))

        total_races += 1
        time.sleep(0.2)

    if total_races == 0:
        return {}

    return {
        "total_races": total_races,
        "winner_accuracy": round(winner_correct / total_races, 4),
        "avg_podium_overlap": round(podium_correct_total / (total_races * 3), 4),
        "avg_spearman": round(float(np.mean(spearman_scores)) if spearman_scores else 0.0, 4),
    }
