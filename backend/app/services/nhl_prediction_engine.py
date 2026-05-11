"""
NHL game prediction engine.

Uses a logistic model built from publicly available team stats:
  - home ice advantage baseline
  - points percentage differential
  - goal differential per game
  - power play % differential
  - save % differential
  - recent form (L10 win%)

No training data required — coefficients are derived from NHL historical
home-win distributions and published sabermetric research.
"""

from __future__ import annotations

import math
from typing import Optional

_MODEL_VERSION = "nhl-stats-v1"

# Logistic coefficients (tuned to produce calibrated probabilities in 0.45-0.70 range)
_W_HOME_ADV    =  0.30   # raw home ice baseline ~54-55% home wins in NHL
_W_POINTS_PCT  =  1.80   # points% is most predictive single stat
_W_GOAL_DIFF   =  0.25   # goal differential per game
_W_PP          =  0.00   # PP% not available from public NHL API — disabled
_W_SV          =  3.50   # save % is highly predictive (goaltending)
_W_L10         =  0.60   # recent form (last 10 games win%)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def predict_game(home: dict, away: dict) -> dict:
    """
    Predict home win probability given home and away team stat dicts
    (as returned by nhl_data.get_standings()).

    Returns a dict with:
      home_win_prob, confidence (0-100), model_confidence, reasons
    """
    # Feature deltas (home - away)
    pts_diff  = home.get("points_pct", 0.0)   - away.get("points_pct", 0.0)
    gd_diff   = home.get("goal_diff_per_game", 0.0) - away.get("goal_diff_per_game", 0.0)
    pp_diff   = home.get("pp_pct", 0.0)        - away.get("pp_pct", 0.0)
    sv_diff   = home.get("save_pct", 0.0)      - away.get("save_pct", 0.0)

    home_l10_wins = home.get("l10_wins", 5)
    home_l10_gp   = (home.get("l10_wins", 0) + home.get("l10_losses", 0) + home.get("l10_ot", 0)) or 10
    away_l10_wins = away.get("l10_wins", 5)
    away_l10_gp   = (away.get("l10_wins", 0) + away.get("l10_losses", 0) + away.get("l10_ot", 0)) or 10
    form_diff = (home_l10_wins / home_l10_gp) - (away_l10_wins / away_l10_gp)

    logit = (
        _W_HOME_ADV
        + _W_POINTS_PCT * pts_diff
        + _W_GOAL_DIFF  * gd_diff
        + _W_PP         * pp_diff
        + _W_SV         * sv_diff
        + _W_L10        * form_diff
    )

    home_win_prob = round(_sigmoid(logit), 4)

    # Confidence: distance from 0.5, scaled to 0-100
    raw_conf = abs(home_win_prob - 0.5) * 200
    confidence = min(100, max(0, int(raw_conf)))

    if confidence >= 60:
        model_confidence = "high"
    elif confidence >= 35:
        model_confidence = "medium"
    else:
        model_confidence = "low"

    reasons = _build_reasons(home, away, home_win_prob, pts_diff, gd_diff, pp_diff, sv_diff, form_diff)

    return {
        "home_win_prob":    home_win_prob,
        "confidence":       confidence,
        "model_confidence": model_confidence,
        "reasons":          reasons,
        "model_version":    _MODEL_VERSION,
    }


def _build_reasons(
    home: dict,
    away: dict,
    home_win_prob: float,
    pts_diff: float,
    gd_diff: float,
    pp_diff: float,
    sv_diff: float,
    form_diff: float,
) -> list[str]:
    winner_name  = home.get("team_name", "Home") if home_win_prob >= 0.5 else away.get("team_name", "Away")
    loser_name   = away.get("team_name", "Away") if home_win_prob >= 0.5 else home.get("team_name", "Home")
    home_name    = home.get("team_name", "Home")
    away_name    = away.get("team_name", "Away")
    reasons: list[str] = []

    # Points percentage
    if abs(pts_diff) > 0.03:
        better = home_name if pts_diff > 0 else away_name
        worse  = away_name if pts_diff > 0 else home_name
        reasons.append(
            f"{better} holds a superior points percentage ({home.get('points_pct', 0):.3f} vs {away.get('points_pct', 0):.3f}), "
            f"indicating stronger overall season performance."
        )

    # Save percentage
    if abs(sv_diff) > 0.002:
        better = home_name if sv_diff > 0 else away_name
        h_sv = home.get("save_pct", 0.0)
        a_sv = away.get("save_pct", 0.0)
        reasons.append(
            f"{better} has the goaltending edge — "
            f"{home_name} .{int(h_sv * 1000):03d} vs {away_name} .{int(a_sv * 1000):03d} save percentage."
        )

    # Goal differential
    if abs(gd_diff) > 0.15:
        better = home_name if gd_diff > 0 else away_name
        h_gd = home.get("goal_diff_per_game", 0.0)
        a_gd = away.get("goal_diff_per_game", 0.0)
        reasons.append(
            f"{better} leads in goals differential per game "
            f"({h_gd:+.2f} vs {a_gd:+.2f}), reflecting stronger two-way play."
        )

    # Recent form
    if abs(form_diff) > 0.1:
        better = home_name if form_diff > 0 else away_name
        reasons.append(
            f"{better} is the hotter team, with a better L10 record entering this matchup."
        )

    # Power play
    if abs(pp_diff) > 0.01:
        better = home_name if pp_diff > 0 else away_name
        h_pp = home.get("pp_pct", 0.0)
        a_pp = away.get("pp_pct", 0.0)
        reasons.append(
            f"{better} has the power play advantage ({h_pp:.1%} vs {a_pp:.1%})."
        )

    # Home ice
    reasons.append(f"{home_name} benefits from home ice advantage.")

    return reasons[:4]
