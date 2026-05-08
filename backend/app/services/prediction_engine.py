"""
Prediction engine.

WHAT THIS FILE DOES (in plain English)
──────────────────────────────────────
This is the "brain" that actually picks a winner.

When the server starts up, this file looks for a trained model file on disk
(the .pkl file that the trainer produces). If found, it loads it into memory
so we can use it instantly for every game.

If the model file is missing — for example, on a fresh server before training
has finished — we fall back to a simple "rule-based" guesser that uses a few
common-sense signals (net rating, Elo, win %). Predictions still work, just
not as accurately, until the real model is ready.

Once training completes, the server can swap in the new model without
restarting (that's what reload_model() does).

There's only ever one PredictionEngine in memory — it's a "singleton" that
the rest of the code asks for via get_prediction_engine().
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np

from app.services.feature_engineering import build_features, FEATURE_NAMES
from app.config import get_settings


class PredictionEngine:
    def __init__(self) -> None:
        # Start empty: no model loaded, default to rule-based until proven
        # otherwise. _try_load() will populate _model if there's one on disk.
        self._model = None
        self._feature_names: list[str] = FEATURE_NAMES
        self._cv_accuracy: Optional[float] = None       # how accurate the model was during training
        self._n_training_games: Optional[int] = None    # how many games we trained on
        self._model_version: str = "rule-based"         # flips to "xgboost-v1" if a real model loads
        self._try_load()

    # ------------------------------------------------------------------
    # Model lifecycle — loading and reloading the trained model file
    # ------------------------------------------------------------------

    def _try_load(self) -> None:
        """
        Try to load a previously trained model from disk.
        If anything goes wrong (file missing, joblib not installed, corrupt
        file), we just leave the engine in rule-based mode and log the issue.
        Predictions never crash — they just get less accurate.
        """
        try:
            import joblib
        except ImportError:
            return  # joblib isn't installed; can't read the model file

        path = get_settings().model_path
        if not os.path.exists(path):
            # First-time startup: training hasn't produced a model yet.
            print("[engine] No model file found — using rule-based fallback.")
            return

        try:
            # Load the saved bundle: the trained model + metadata about it.
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
            # Something corrupt — log and stay on rule-based.
            print(f"[engine] Failed to load model: {exc}")

    def reload_model(self) -> None:
        """
        Called by the nightly retrain task after a fresh model is saved.
        Wipes the in-memory model and reloads from disk so users immediately
        see predictions from the new model — no server restart needed.
        """
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
        is_playoff: bool = False,
        home_avail: dict | None = None,
        away_avail: dict | None = None,
        home_splits: dict | None = None,
        away_splits: dict | None = None,
        h2h: dict | None = None,
    ) -> dict:
        """
        The main prediction entry point. Given everything we know about a
        matchup, returns a dictionary with:
          • predicted_winner_is_home — True if we think home wins
          • confidence — how sure we are (0.5 = coin flip, 1.0 = certain)
          • predicted_home_score / predicted_away_score — rough score guesses
          • features — the raw 38-number feature vector (used for debugging)
        """
        # Step 1: Translate the matchup into the 38-number feature vector.
        features = build_features(
            home_stats, away_stats,
            home_recent, away_recent,
            home_elo, away_elo,
            home_rest, away_rest,
            is_playoff=is_playoff,
            home_avail=home_avail,
            away_avail=away_avail,
            home_splits=home_splits,
            away_splits=away_splits,
            h2h=h2h,
        )

        # Step 2: Run the prediction.
        if self._model is not None:
            # Real ML path: ask XGBoost for the probability of each outcome.
            # predict_proba returns [prob_away_wins, prob_home_wins]; we pick
            # the bigger one as our answer and report its probability as the
            # confidence.
            proba = self._model.predict_proba(features.reshape(1, -1))[0]
            label = int(np.argmax(proba))
            confidence = float(proba[label])
            home_wins = label == 1
        else:
            # Fallback path: simple weighted formula (no trained model loaded).
            home_wins, confidence = self._rule_based(features)

        # Step 3: Estimate a rough score for each side.
        # We start from each team's season points-per-game average, then nudge
        # the predicted winner up by 3 and the loser down by 3 — a soft hint
        # rather than a hard rule.
        home_ppg = float(home_stats.get("ppg", 110.0))
        away_ppg = float(away_stats.get("ppg", 110.0))
        home_score = int(round(home_ppg + (3 if home_wins else -3)))
        away_score = int(round(away_ppg + (-3 if home_wins else 3)))

        # Clamp to the realistic NBA range (88-145) to catch any outliers.
        home_score = max(88, min(145, home_score))
        away_score = max(88, min(145, away_score))

        # Sanity check: the team we said "wins" must actually have the higher
        # predicted score. If the PPG nudge wasn't enough (e.g. a low-scoring
        # team narrowly beats a high-scoring team), bump them above by 4.
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
        The simple guesser used when no trained model is loaded.

        It pulls the five most predictive numbers out of the feature vector
        (net rating gap, Elo gap, win %, recent form, rest) and combines them
        with hand-picked weights. Bigger positive total = more confident the
        home team wins.

        The weights below were chosen to roughly mimic what XGBoost ends up
        learning, so this fallback gives reasonable answers (~58-62% accuracy)
        while we wait for the real model to train.
        """
        # Pull the five most-predictive features by index into the vector.
        net_diff  = float(features[0])   # net_rtg_diff (single best signal)
        elo_diff  = float(features[14])  # elo_diff (already divided by 100)
        wp_diff   = float(features[9])   # win_pct_diff (full season)
        rec_diff  = float(features[12])  # recent_win_pct_diff (last 10 games)
        rest_diff = float(features[15])  # rest_diff (days of rest gap)

        # Weighted sum: positive = home team favored, negative = away favored.
        score = (
            net_diff  * 0.40
            + elo_diff * 40.0   # multiply elo back up since we'd divided it by 100
            + wp_diff  * 8.0
            + rec_diff * 5.0
            + rest_diff * 0.8
        )

        home_wins = score >= 0.0

        # Convert the raw score into a confidence between 0.52 and 0.84.
        # We never report 100% confidence from a heuristic — it'd be misleading.
        abs_score = abs(score)
        confidence = min(0.84, 0.52 + abs_score * 0.018)

        return home_wins, float(confidence)


# Module-level singleton
_engine = PredictionEngine()


def get_prediction_engine() -> PredictionEngine:
    return _engine
