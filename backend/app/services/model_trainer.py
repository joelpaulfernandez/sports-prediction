"""
Model training pipeline.

Fetches multiple seasons of NBA game results from stats.nba.com, builds
20-feature vectors for each game, trains an XGBoost classifier, evaluates
it with 5-fold cross-validation, and persists the artifact to disk.

Training strategy (avoids data leakage)
────────────────────────────────────────
For each training game we use:
  • Elo ratings computed from all games BEFORE that game date (no leakage)
  • Season stats (slightly leaky for early-season games, acceptable — standard
    practice in sports ML; stats stabilise after ~20 games)
  • Recent form derived from the game log BEFORE that game date (no leakage)

Running time: ~3-5 minutes on first run (API calls, ~3 seasons × ~1 230 games).
The trained artifact is cached at settings.model_path and auto-loaded on restart.
"""

import os
import time
import json
import datetime

import numpy as np
import pandas as pd

from app.services import nba_data, player_availability
from app.services.elo import EloSystem
from app.services.feature_engineering import build_features, FEATURE_NAMES
from app.config import get_settings

TRAINING_SEASONS = nba_data.TRAINING_SEASONS


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def train_and_save(
    model_path: str | None = None,
    seasons: list[str] | None = None,
) -> dict:
    """
    Train XGBoost on NBA seasons and save to model_path.
    `seasons` defaults to TRAINING_SEASONS; pass extra seasons (e.g. the
    current one) to include in-progress data without touching the default.
    Returns a metadata dict; empty dict on failure.
    """
    try:
        import xgboost as xgb
        from sklearn.model_selection import cross_val_score, StratifiedKFold
    except ImportError as exc:
        print(f"[trainer] Missing dependency: {exc}")
        return {}

    if model_path is None:
        model_path = get_settings().model_path

    if seasons is None:
        seasons = TRAINING_SEASONS

    X_parts: list[np.ndarray] = []
    y_parts: list[int] = []

    for season in seasons:
        print(f"[trainer] Fetching {season}…")
        rows, labels = _build_season_examples(season)
        if rows:
            X_parts.append(np.array(rows, dtype=np.float32))
            y_parts.extend(labels)
        print(f"[trainer]   → {len(rows)} training games")
        time.sleep(1.0)

    if not X_parts:
        print("[trainer] No training data collected — aborting.")
        return {}

    X = np.vstack(X_parts)
    y = np.array(y_parts, dtype=np.int32)

    print(f"[trainer] Total training examples: {len(X)}")
    print(f"[trainer] Home-win rate in training data: {y.mean():.3f}")

    model = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=4,
        learning_rate=0.04,
        subsample=0.80,
        colsample_bytree=0.80,
        min_child_weight=6,
        gamma=1.0,
        reg_alpha=0.1,
        reg_lambda=1.5,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
    print(f"[trainer] 5-fold CV accuracy: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    model.fit(X, y)

    importance = dict(zip(FEATURE_NAMES, model.feature_importances_.tolist()))
    top5 = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"[trainer] Top features: {top5}")

    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    try:
        import joblib
    except ImportError:
        print("[trainer] joblib not available — model not saved.")
        return {}

    artifact = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "cv_accuracy": float(cv_scores.mean()),
        "cv_std": float(cv_scores.std()),
        "training_seasons": seasons,
        "n_training_games": int(len(X)),
        "home_win_rate": float(y.mean()),
        "feature_importance": importance,
        "trained_at": datetime.datetime.utcnow().isoformat(),
    }
    joblib.dump(artifact, model_path)
    print(f"[trainer] Saved model to {model_path}")

    return {
        "cv_accuracy": float(cv_scores.mean()),
        "cv_std": float(cv_scores.std()),
        "n_games": int(len(X)),
        "trained_at": artifact["trained_at"],
    }


# ---------------------------------------------------------------------------
# Season example builder
# ---------------------------------------------------------------------------

def _build_season_examples(season: str) -> tuple[list[np.ndarray], list[int]]:
    """
    Build (feature_vectors, labels) for every regular-season and playoff game
    in `season`. label = 1 if home team won, 0 otherwise.
    """
    rows: list[np.ndarray] = []
    labels: list[int] = []

    for season_type, is_playoff in [("Regular Season", False), ("Playoffs", True)]:
        part_rows, part_labels = _build_examples_for_type(season, season_type, is_playoff)
        rows.extend(part_rows)
        labels.extend(part_labels)
        time.sleep(0.5)

    return rows, labels


def _build_examples_for_type(
    season: str, season_type: str, is_playoff: bool
) -> tuple[list[np.ndarray], list[int]]:
    game_log = nba_data.get_season_game_log(season, season_type)
    if game_log is None or game_log.empty:
        return [], []

    time.sleep(1.0)

    team_stats = nba_data.get_all_team_stats(season)
    if not team_stats:
        return [], []

    time.sleep(0.5)

    game_log = game_log.copy()
    game_log["is_home"] = game_log["MATCHUP"].str.contains(r" vs\. ")
    game_log["GAME_DATE"] = pd.to_datetime(game_log["GAME_DATE"])

    home_games = game_log[game_log["is_home"]].copy()
    away_games = game_log[~game_log["is_home"]].copy()

    merged = home_games.merge(
        away_games[["GAME_ID", "TEAM_ID", "WL", "PLUS_MINUS"]],
        on="GAME_ID",
        suffixes=("_home", "_away"),
    )

    rows: list[np.ndarray] = []
    labels: list[int] = []

    elo = EloSystem()
    elo.process_game_log(game_log)

    # Build the per-season availability index ONCE and reuse it across every
    # game in this season — this is the difference between training in 5 minutes
    # vs an hour.
    avail_index = player_availability.get_season_availability(season)

    for _, row in merged.iterrows():
        home_id = int(row["TEAM_ID_home"])
        away_id = int(row["TEAM_ID_away"])

        h = team_stats.get(home_id)
        a = team_stats.get(away_id)
        if h is None or a is None:
            continue

        game_date_str = str(row["GAME_DATE"].date())

        h_recent = nba_data.compute_team_recent_form(
            home_id, game_log, n_games=10, before_date=game_date_str
        )
        a_recent = nba_data.compute_team_recent_form(
            away_id, game_log, n_games=10, before_date=game_date_str
        )

        h_rest = nba_data.compute_rest_days(h_recent.get("last_game_date"), game_date_str)
        a_rest = nba_data.compute_rest_days(a_recent.get("last_game_date"), game_date_str)

        h_elo = elo.get(home_id)
        a_elo = elo.get(away_id)

        # Player availability — computed from games BEFORE this one (no leakage)
        h_avail = avail_index.get_features(home_id, before_date=game_date_str)
        a_avail = avail_index.get_features(away_id, before_date=game_date_str)

        features = build_features(
            h, a,
            h_recent, a_recent,
            h_elo, a_elo,
            h_rest, a_rest,
            is_playoff=is_playoff,
            home_avail=h_avail,
            away_avail=a_avail,
        )

        label = 1 if str(row["WL_home"]) == "W" else 0
        rows.append(features)
        labels.append(label)

    return rows, labels
