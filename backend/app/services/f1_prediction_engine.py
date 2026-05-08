"""
F1 prediction engine.

Loads XGBRanker from disk. Falls back to a qualifying-order heuristic
when no model is trained. Hot-reloadable after training completes.
"""

import os
from typing import Optional

import numpy as np

from app.services.f1_features import F1_FEATURE_NAMES, N_FEATURES


class F1PredictionEngine:
    def __init__(self) -> None:
        self._ranker = None
        self._feature_names: list[str] = F1_FEATURE_NAMES
        self._validation_metrics: dict = {}
        self._model_version: str = "rule-based"
        self._trained_at: Optional[str] = None
        self._try_load()

    def _try_load(self) -> None:
        try:
            import joblib
        except ImportError:
            return

        from app.services.f1_model_trainer import get_f1_model_path
        path = get_f1_model_path()

        if not os.path.exists(path):
            print("[f1_engine] No model file found — using qualifying-order fallback.")
            return

        try:
            artifact = joblib.load(path)
            self._ranker = artifact["ranker"]
            self._feature_names = artifact.get("feature_names", F1_FEATURE_NAMES)
            self._validation_metrics = artifact.get("validation_metrics", {})
            self._trained_at = artifact.get("trained_at")
            self._model_version = "xgboost-ranker-v1"
            metrics = self._validation_metrics
            print(
                f"[f1_engine] F1 model loaded — "
                f"winner_acc: {metrics.get('winner_accuracy', '?')}, "
                f"spearman: {metrics.get('avg_spearman', '?')}"
            )
        except Exception as exc:
            print(f"[f1_engine] Failed to load model: {exc}")

    def reload_model(self) -> None:
        self._ranker = None
        self._model_version = "rule-based"
        self._try_load()

    @property
    def is_trained(self) -> bool:
        return self._ranker is not None

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def validation_metrics(self) -> dict:
        return self._validation_metrics

    @property
    def ranker(self):
        return self._ranker

    def predict_race(
        self,
        driver_df,
        X: np.ndarray,
        circuit_meta: dict,
        circuit_name: str = "this circuit",
        compound: str = "medium",
    ) -> list[dict]:
        """
        Predict finishing order for a race.

        Returns list of dicts sorted by predicted position (1 = first):
            position, driver_id, driver_name, team, driver_number,
            win_prob, podium_prob, confidence_score, features, raw_score,
            quali_position, grid_position
        """
        if X.shape[0] == 0:
            return []

        n_drivers = X.shape[0]
        overtaking_diff = float(circuit_meta.get("overtaking_difficulty", 5.0))
        is_high_var = circuit_meta.get("circuit_variance", "normal") == "high"

        if self._ranker is not None:
            raw_scores = self._ranker.predict(X)
        else:
            # Rule-based fallback: lower grid position = higher score
            # Add small random noise to avoid ties
            grid_positions = X[:, 1]  # grid_position feature
            raw_scores = -grid_positions + np.random.normal(0, 0.1, n_drivers)

        # Temperature-scaled softmax for win probability
        temperature = 0.25 if not is_high_var else 0.40
        scaled = raw_scores / temperature
        scaled -= scaled.max()
        win_probs = np.exp(scaled)
        win_probs /= win_probs.sum()

        # Predicted order (rank 1 = highest score)
        predicted_order = np.argsort(-raw_scores)

        results = []
        for rank, driver_idx in enumerate(predicted_order):
            position = rank + 1
            row = driver_df.iloc[driver_idx]
            win_prob = float(win_probs[driver_idx])
            podium_prob = _compute_podium_prob(rank, win_prob, is_high_var, n_drivers)
            confidence_score = _compute_confidence(win_prob, position, is_high_var, self.is_trained)

            results.append({
                "position":       position,
                "driver_id":      row["driver_id"],
                "driver_name":    row["driver_name"],
                "driver_number":  str(row.get("driver_number", "")),
                "team":           row["team"],
                "win_prob":       round(win_prob, 4),
                "podium_prob":    round(podium_prob, 4),
                "confidence_score": confidence_score,
                "features":       X[driver_idx],
                "raw_score":      float(raw_scores[driver_idx]),
                "quali_position": int(row.get("quali_position", position)),
                "grid_position":  int(row.get("grid_position", position)),
                "overtaking_difficulty": overtaking_diff,
            })

        return results


def _compute_podium_prob(
    predicted_rank: int,
    win_prob: float,
    is_high_var: bool,
    n_drivers: int,
) -> float:
    """
    Approximate podium probability from predicted rank and win probability.
    High-variance circuits have flatter distributions.
    """
    # Base probabilities by predicted rank
    variance_factor = 1.4 if is_high_var else 1.0
    base_probs = {
        0: 0.75,
        1: 0.62,
        2: 0.52,
        3: 0.35,
        4: 0.22,
        5: 0.14,
    }
    base = base_probs.get(predicted_rank, max(0.0, 0.12 - predicted_rank * 0.01))

    # Blend with win_prob signal: higher win_prob = higher podium prob
    blended = base * 0.6 + min(0.95, win_prob * 3.5) * 0.4

    # Apply variance factor (high-var circuits compress the distribution)
    if is_high_var:
        blended = 0.5 * blended + 0.5 * (1.0 / min(n_drivers, 20)) * variance_factor

    return float(min(0.98, max(0.01, blended)))


def _compute_confidence(
    win_prob: float,
    predicted_position: int,
    is_high_var: bool,
    is_ml_model: bool,
) -> int:
    """
    0–100 confidence score for top predicted driver.
    Only meaningful for position == 1.
    """
    if predicted_position != 1:
        # Confidence only displayed for predicted winner
        return max(0, min(100, int(win_prob * 100)))

    base = min(95, int(win_prob * 130))

    # Penalties
    if is_high_var:
        base = int(base * 0.80)  # street circuits are less predictable
    if not is_ml_model:
        base = int(base * 0.75)  # rule-based has lower confidence

    return max(10, min(95, base))


# Module singleton
_f1_engine = F1PredictionEngine()


def get_f1_prediction_engine() -> F1PredictionEngine:
    return _f1_engine
