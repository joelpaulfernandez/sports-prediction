"""
Prediction engine.

On init, tries to load a persisted XGBoost model from disk.  If no model
exists, all predictions fall back to a multi-signal rule-based heuristic
(net rating + Elo + win%) while training runs in the background.

Call reload_model() after training completes to hot-swap the model without
restarting the server.
"""

import os
from typing import Optional

import numpy as np

from app.services.feature_engineering import build_features, FEATURE_NAMES
from app.config import get_settings


class PredictionEngine:
    def __init__(self) -> None:
        self._model = None
        self._feature_names: list[str] = FEATURE_NAMES
        self._cv_accuracy: Optional[float] = None
        self._n_training_games: Optional[int] = None
        self._model_version: str = "rule-based"
        self._try_load()

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    def _try_load(self) -> None:
        try:
            import joblib
        except ImportError:
            return

        path = get_settings().model_path
        if not os.path.exists(path):
            print("[engine] No model file found — using rule-based fallback.")
            return

        try:
            artifact = joblib.load(path)
            self._model = artifact["model"]
            self._feature_names = artifact.get("feature_names", FEATURE_NAMES)
            self._cv_accuracy = artifact.get("cv_accuracy")
            self._n_training_games = artifact.get("n_training_games")
            self._model_version = "xgboost-v1"
            print(
                f"[engine] Model loaded — CV accuracy: {self._cv_accuracy:.3f} "
                f"over {self._n_training_games} games."
            )
        except Exception as exc:
            print(f"[engine] Failed to load model: {exc}")

    def reload_model(self) -> None:
        """Hot-reload from disk after a training run completes."""
        self._model = None
        self._model_version = "rule-based"
        self._try_load()

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def is_trained(self) -> bool:
        return self._model is not None

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def cv_accuracy(self) -> Optional[float]:
        return self._cv_accuracy

    # ------------------------------------------------------------------
    # Core prediction
    # ------------------------------------------------------------------

    def generate_prediction(
        self,
        home_stats: dict,
        away_stats: dict,
        home_recent: dict,
        away_recent: dict,
        home_elo: float,
        away_elo: float,
        home_rest: int = 3,
        away_rest: int = 3,
    ) -> dict:
        """
        Return prediction dict:
          predicted_winner_is_home, confidence, predicted_home_score,
          predicted_away_score, feature_vector (np.ndarray).
        """
        features = build_features(
            home_stats, away_stats,
            home_recent, away_recent,
            home_elo, away_elo,
            home_rest, away_rest,
        )

        if self._model is not None:
            proba = self._model.predict_proba(features.reshape(1, -1))[0]
            label = int(np.argmax(proba))
            confidence = float(proba[label])
            home_wins = label == 1
        else:
            home_wins, confidence = self._rule_based(features)

        home_ppg = float(home_stats.get("ppg", 110.0))
        away_ppg = float(away_stats.get("ppg", 110.0))

        # Predicted score: use each team's PPG with a small winner/loser nudge
        home_score = int(round(home_ppg + (3 if home_wins else -3)))
        away_score = int(round(away_ppg + (-3 if home_wins else 3)))
        home_score = max(88, min(145, home_score))
        away_score = max(88, min(145, away_score))

        # Guarantee winning team has the higher score
        if home_wins and home_score <= away_score:
            home_score = away_score + 4
        elif not home_wins and away_score <= home_score:
            away_score = home_score + 4

        return {
            "predicted_winner_is_home": home_wins,
            "confidence": round(confidence, 4),
            "predicted_home_score": home_score,
            "predicted_away_score": away_score,
            "features": features,
        }

    # ------------------------------------------------------------------
    # Rule-based fallback (used when no model is trained)
    # ------------------------------------------------------------------

    @staticmethod
    def _rule_based(features: np.ndarray) -> tuple[bool, float]:
        """
        Multi-signal heuristic using net rating, Elo, and win%.
        Weights chosen to approximate XGBoost feature importances.
        """
        net_diff  = float(features[0])   # net_rtg_diff
        elo_diff  = float(features[14])  # elo_diff (already /100)
        wp_diff   = float(features[9])   # win_pct_diff
        rec_diff  = float(features[12])  # recent_win_pct_diff
        rest_diff = float(features[15])  # rest_diff

        score = (
            net_diff  * 0.40
            + elo_diff * 40.0   # un-normalise back to ~rating points scale
            + wp_diff  * 8.0
            + rec_diff * 5.0
            + rest_diff * 0.8   # rest advantage
        )

        home_wins = score >= 0.0

        # Sigmoid-like confidence mapping
        abs_score = abs(score)
        confidence = min(0.84, 0.52 + abs_score * 0.018)

        return home_wins, float(confidence)


# Module-level singleton
_engine = PredictionEngine()


def get_prediction_engine() -> PredictionEngine:
    return _engine
