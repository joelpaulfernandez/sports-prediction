"""
F1 feature engineering.

Build per-driver feature vectors for XGBRanker training and inference.
All features derived from pre-race data only — no post-race leakage.
"""

import numpy as np
import pandas as pd
from typing import Optional

F1_FEATURE_NAMES = [
    "quali_gap_to_pole",       # seconds behind pole (0 = pole)
    "grid_position",           # starting grid position (1-indexed)
    "track_position_value",    # grid_pos * overtaking_difficulty (normalized)
    "rolling_avg_finish_5",    # exp-weighted avg finish pos, last 5 races
    "constructor_pace_delta",  # FP2 long run vs field median (s, negative = faster)
    "dnf_risk_score",          # historical DNF fraction (0-1)
    "safety_car_probability",  # circuit SC base rate (0-1)
    "tyre_deg_rate",           # deg rate per lap from FP2 (s/lap)
    "teammate_quali_gap",      # gap to teammate in quali (positive = faster)
    "is_high_variance_circuit",# 1 if Monaco/Baku/Singapore/etc.
]

N_FEATURES = len(F1_FEATURE_NAMES)


def build_driver_features(
    driver_id: str,
    quali_gap_to_pole: float,
    grid_position: int,
    overtaking_difficulty: float,
    rolling_avg_finish: float,
    constructor_pace_delta: float,
    dnf_risk: float,
    safety_car_prob: float,
    tyre_deg_rate: float,
    teammate_quali_gap: float,
    is_high_variance: bool,
) -> np.ndarray:
    """Build a single driver's feature vector (length N_FEATURES)."""
    # Normalize track_position_value: grid_pos scaled by overtaking difficulty
    # Range: 1-20 * 1-10 = 1-200, normalized to 0-1
    track_pos_value = (grid_position * overtaking_difficulty) / 200.0

    return np.array([
        float(quali_gap_to_pole),
        float(grid_position),
        float(track_pos_value),
        float(rolling_avg_finish),
        float(constructor_pace_delta),
        float(max(0.0, min(1.0, dnf_risk))),
        float(safety_car_prob),
        float(tyre_deg_rate),
        float(teammate_quali_gap),
        float(1 if is_high_variance else 0),
    ], dtype=np.float32)


def build_race_feature_matrix(
    quali_df: pd.DataFrame,
    grid_positions: dict[str, int],
    fp2_pace: Optional[pd.DataFrame],
    dnf_rates: dict[str, float],
    rolling_forms: dict[str, dict],
    teammate_gaps: dict[str, float],
    circuit_meta: dict,
) -> tuple[pd.DataFrame, np.ndarray]:
    """
    Build feature matrix for all drivers in a race.

    Returns:
        driver_info_df: DataFrame with driver_id, driver_name, team, quali_position
        X: np.ndarray shape (n_drivers, N_FEATURES)
    """
    overtaking_diff = float(circuit_meta.get("overtaking_difficulty", 5.0))
    safety_car_rate = float(circuit_meta.get("safety_car_rate", 0.35))
    is_high_var = circuit_meta.get("circuit_variance", "normal") == "high"

    # Build FP2 pace lookup: driver_id → (pace_delta, deg_rate)
    fp2_lookup: dict[str, tuple[float, float]] = {}
    if fp2_pace is not None and not fp2_pace.empty:
        for _, row in fp2_pace.iterrows():
            fp2_lookup[str(row["driver_id"])] = (
                float(row.get("vs_median_delta", 0.0)),
                float(row.get("deg_rate", 0.02)),
            )

    rows = []
    feature_rows = []

    for _, driver in quali_df.iterrows():
        did = driver["driver_id"]
        grid_pos = grid_positions.get(did, int(driver.get("quali_position", 10)))
        quali_gap = float(driver.get("quali_gap_s", 0.0))

        form = rolling_forms.get(did, {"rolling_avg_finish_5": 10.0})
        dnf_risk = float(dnf_rates.get(did, 0.10))
        teammate_gap = float(teammate_gaps.get(did, 0.0))
        pace_delta, deg_rate = fp2_lookup.get(did, (0.0, 0.02))

        rows.append({
            "driver_id":      did,
            "driver_name":    driver.get("driver_name", did),
            "driver_number":  str(driver.get("driver_number", "")),
            "team":           driver.get("team", ""),
            "quali_position": int(driver.get("quali_position", 10)),
            "grid_position":  grid_pos,
            "quali_gap_s":    quali_gap,
        })

        feature_rows.append(build_driver_features(
            driver_id=did,
            quali_gap_to_pole=quali_gap,
            grid_position=grid_pos,
            overtaking_difficulty=overtaking_diff,
            rolling_avg_finish=form.get("rolling_avg_finish_5", 10.0),
            constructor_pace_delta=pace_delta,
            dnf_risk=dnf_risk,
            safety_car_prob=safety_car_rate,
            tyre_deg_rate=deg_rate,
            teammate_quali_gap=teammate_gap,
            is_high_variance=is_high_var,
        ))

    if not rows:
        return pd.DataFrame(), np.empty((0, N_FEATURES), dtype=np.float32)

    return pd.DataFrame(rows), np.array(feature_rows, dtype=np.float32)


# ---------------------------------------------------------------------------
# Ranking label encoder
# ---------------------------------------------------------------------------

def position_to_label(position: int, n_drivers: int = 20) -> int:
    """Convert finishing position to XGBRanker label. P1 = highest label."""
    return max(0, n_drivers + 1 - position)
