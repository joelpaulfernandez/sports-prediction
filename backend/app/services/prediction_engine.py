import numpy as np

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False


class PredictionEngine:
    """XGBoost-backed prediction engine with a rule-based fallback."""

    def __init__(self) -> None:
        self.model = None
        self._is_trained = False

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_features(home_stats: dict, away_stats: dict) -> np.ndarray:
        """Return a 1-D feature array for a single matchup."""

        def safe_float(value, default: float = 0.0) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        def win_pct(stats: dict) -> float:
            wins = safe_float(stats.get("wins", {}).get("all", {}).get("total", 0))
            losses = safe_float(stats.get("losses", {}).get("all", {}).get("total", 0))
            total = wins + losses
            return wins / total if total > 0 else 0.5

        def avg_ppg(stats: dict) -> float:
            return safe_float(
                stats.get("points", {}).get("for", {}).get("average", {}).get("all", 105)
            )

        home_win_pct = win_pct(home_stats)
        away_win_pct = win_pct(away_stats)
        home_recent_ppg = avg_ppg(home_stats)
        away_recent_ppg = avg_ppg(away_stats)
        home_is_home_advantage = 1.0

        return np.array(
            [home_win_pct, away_win_pct, home_recent_ppg, away_recent_ppg, home_is_home_advantage],
            dtype=np.float32,
        )

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train_model(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train the XGBoost classifier.

        Args:
            X: Feature matrix, shape (n_samples, 5).
            y: Binary labels — 1 if home team won, 0 otherwise.
        """
        if not XGB_AVAILABLE:
            print("xgboost not installed — skipping training.")
            return

        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=42,
        )
        self.model.fit(X, y)
        self._is_trained = True

    # ------------------------------------------------------------------
    # Prediction helpers
    # ------------------------------------------------------------------

    def predict(self, features: np.ndarray) -> tuple[int, float]:
        """Return (predicted_label, confidence) for a single feature row."""
        if not self._is_trained or self.model is None:
            raise RuntimeError("Model not trained yet.")
        proba = self.model.predict_proba(features.reshape(1, -1))[0]
        label = int(np.argmax(proba))
        confidence = float(proba[label])
        return label, confidence

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_prediction(self, home_team_stats: dict, away_team_stats: dict) -> dict:
        """Generate a prediction for a single matchup.

        Returns a dict with:
          - predicted_winner_is_home: bool
          - confidence: float (0–1)
          - predicted_home_score: int
          - predicted_away_score: int
        """
        features = self._extract_features(home_team_stats, away_team_stats)

        if self._is_trained and XGB_AVAILABLE:
            label, confidence = self.predict(features)
            home_wins = bool(label == 1)
        else:
            home_wins, confidence = self._rule_based_prediction(features)

        home_ppg = features[2]
        away_ppg = features[3]

        # Add a small home-court bump and some variance
        home_score = int(round(home_ppg * 1.01 + (2 if home_wins else -2)))
        away_score = int(round(away_ppg * 0.99 + (-2 if home_wins else 2)))

        # Ensure scores are in a realistic range
        home_score = max(85, min(145, home_score))
        away_score = max(85, min(145, away_score))

        # Make sure the winning team actually has a higher predicted score
        if home_wins and home_score <= away_score:
            home_score = away_score + 4
        elif not home_wins and away_score <= home_score:
            away_score = home_score + 4

        return {
            "predicted_winner_is_home": home_wins,
            "confidence": round(confidence, 4),
            "predicted_home_score": home_score,
            "predicted_away_score": away_score,
        }

    # ------------------------------------------------------------------
    # Rule-based fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _rule_based_prediction(features: np.ndarray) -> tuple[bool, float]:
        """Simple heuristic: higher win% wins, with home-court tie-break."""
        home_win_pct, away_win_pct, home_ppg, away_ppg, _ = features

        # Home advantage adds a small bonus
        adjusted_home = home_win_pct + 0.03
        home_wins = adjusted_home >= away_win_pct

        diff = abs(adjusted_home - away_win_pct)
        # Clamp confidence between 0.50 and 0.85
        confidence = min(0.85, max(0.50, 0.50 + diff * 2.0))

        return home_wins, float(confidence)


# Module-level singleton
_engine = PredictionEngine()


def get_prediction_engine() -> PredictionEngine:
    return _engine
