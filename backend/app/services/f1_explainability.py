"""
F1 SHAP-based explainability.

Generates 3 plain-English reasons for the predicted race leader
by mapping top SHAP features to human-readable templates.
"""

from typing import Optional
import numpy as np

from app.services.f1_features import F1_FEATURE_NAMES

# Template map: feature_name → callable(value, driver, team, **ctx) → str
def _tpl_quali_gap(value: float, driver: str, team: str, **_) -> str:
    if value <= 0.05:
        return f"{driver} starts on pole position"
    return f"{driver} qualified {value:.3f}s off pole — strong starting position"


def _tpl_grid(value: float, driver: str, team: str, overtaking_difficulty: float = 5.0, **_) -> str:
    pos = int(round(value))
    if overtaking_difficulty >= 8.0:
        return f"{driver} starts P{pos} — track position is critical at this circuit"
    if pos <= 3:
        return f"{driver} starts P{pos} — front row provides strong race pace advantage"
    return f"{driver} starts P{pos}"


def _tpl_track_pos(value: float, driver: str, team: str, grid_position: int = 1,
                   overtaking_difficulty: float = 5.0, **_) -> str:
    if overtaking_difficulty >= 8.5:
        return f"Overtaking is extremely difficult here — track position from P{grid_position} is decisive"
    return f"{driver} starts P{grid_position} — grid advantage amplified by low overtaking rate"


def _tpl_rolling_avg(value: float, driver: str, team: str, **_) -> str:
    avg = round(value, 1)
    if avg <= 3.0:
        return f"{driver} averaged P{avg:.0f} over the last 5 races — strong current form"
    if avg <= 6.0:
        return f"{driver} averaged P{avg:.1f} finishes over the last 5 races"
    return f"{driver} has averaged P{avg:.0f} over recent races — inconsistent form"


def _tpl_constructor_pace(value: float, driver: str, team: str, compound: str = "medium", **_) -> str:
    if value < -0.3:
        return f"{team} fastest in FP2 long runs on the {compound} compound ({abs(value):.2f}s ahead of field)"
    if value < 0.0:
        return f"{team} showed {abs(value):.2f}s advantage per lap in FP2 long runs"
    if value < 0.3:
        return f"{team} showed competitive FP2 long-run pace — near field median"
    return f"{team} FP2 long-run pace was {value:.2f}s off the field median"


def _tpl_dnf_risk(value: float, driver: str, team: str, **_) -> str:
    pct = round(value * 100)
    if value <= 0.05:
        return f"{team} has a low {pct}% DNF rate this season — mechanical reliability advantage"
    if value <= 0.12:
        return f"{team} has retired in {pct}% of races this season"
    return f"{team} has a high {pct}% DNF rate this season — reliability concern"


def _tpl_safety_car(value: float, driver: str, team: str, circuit: str = "this circuit", **_) -> str:
    pct = round(value * 100)
    if value >= 0.6:
        return f"{circuit} averages a safety car in {pct}% of races — high variance event likely"
    if value >= 0.4:
        return f"{circuit} has a {pct}% safety car probability — strategy could be disrupted"
    return f"{circuit} has a lower {pct}% safety car rate — clean race more likely"


def _tpl_tyre_deg(value: float, driver: str, team: str, compound: str = "medium", **_) -> str:
    if value <= 0.01:
        return f"{team} shows minimal tyre degradation on the {compound} compound — longer stint capability"
    if value <= 0.03:
        return f"{team} shows manageable {value:.3f}s/lap degradation on the {compound} compound"
    return f"{team} tyre degradation of {value:.3f}s/lap on the {compound} compound could force early stops"


def _tpl_teammate_gap(value: float, driver: str, team: str, **_) -> str:
    if value > 0.2:
        return f"{driver} outqualified teammate by {value:.3f}s — clear car setup advantage"
    if value > 0.0:
        return f"{driver} was marginally faster than teammate in qualifying"
    return f"{driver} was {abs(value):.3f}s behind teammate in qualifying"


def _tpl_high_variance(value: float, driver: str, team: str, circuit: str = "this circuit", **_) -> str:
    if value >= 0.5:
        return f"{circuit} is a high-variance circuit — safety cars and strategy swings increase uncertainty"
    return f"{circuit} favors consistent execution over raw pace"


_TEMPLATES = {
    "quali_gap_to_pole":       _tpl_quali_gap,
    "grid_position":           _tpl_grid,
    "track_position_value":    _tpl_track_pos,
    "rolling_avg_finish_5":    _tpl_rolling_avg,
    "constructor_pace_delta":  _tpl_constructor_pace,
    "dnf_risk_score":          _tpl_dnf_risk,
    "safety_car_probability":  _tpl_safety_car,
    "tyre_deg_rate":           _tpl_tyre_deg,
    "teammate_quali_gap":      _tpl_teammate_gap,
    "is_high_variance_circuit": _tpl_high_variance,
}

_SHAP_THRESHOLD = 0.01


def generate_f1_reasons(
    driver: str,
    team: str,
    features: np.ndarray,
    model,
    circuit_name: str = "this circuit",
    compound: str = "medium",
    overtaking_difficulty: float = 5.0,
    n_reasons: int = 3,
) -> list[str]:
    """
    Run SHAP on model for this driver's features.
    Return top n_reasons plain-English strings.
    """
    reasons = []

    try:
        import shap
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(features.reshape(1, -1))[0]

        # Sort features by abs SHAP value descending
        abs_shap = np.abs(shap_vals)
        ranked_indices = np.argsort(-abs_shap)

        grid_pos = int(round(float(features[1])))

        for idx in ranked_indices:
            if len(reasons) >= n_reasons:
                break
            fname = F1_FEATURE_NAMES[idx]
            fval = float(features[idx])
            tpl = _TEMPLATES.get(fname)
            if tpl is None:
                continue
            try:
                text = tpl(
                    fval, driver, team,
                    circuit=circuit_name,
                    compound=compound,
                    overtaking_difficulty=overtaking_difficulty,
                    grid_position=grid_pos,
                )
                reasons.append(text)
            except Exception:
                continue

        # Pad with fallbacks if fewer than n_reasons meaningful SHAP values
        if len(reasons) < n_reasons:
            for idx in ranked_indices:
                if len(reasons) >= n_reasons:
                    break
                fname = F1_FEATURE_NAMES[idx]
                fval = float(features[idx])
                tpl = _TEMPLATES.get(fname)
                if tpl is None:
                    continue
                try:
                    text = tpl(fval, driver, team,
                               circuit=circuit_name, compound=compound,
                               overtaking_difficulty=overtaking_difficulty,
                               grid_position=grid_pos)
                    if text not in reasons:
                        reasons.append(text)
                except Exception:
                    continue

    except ImportError:
        # SHAP not available — fall back to rule-based reasons
        reasons = _rule_based_reasons(driver, team, features, circuit_name, compound, overtaking_difficulty)

    except Exception as exc:
        print(f"[f1_explainability] SHAP failed: {exc}")
        reasons = _rule_based_reasons(driver, team, features, circuit_name, compound, overtaking_difficulty)

    return reasons[:n_reasons]


def _rule_based_reasons(
    driver: str,
    team: str,
    features: np.ndarray,
    circuit_name: str,
    compound: str,
    overtaking_difficulty: float,
) -> list[str]:
    """Fallback when SHAP is unavailable. Prioritize strongest features."""
    reasons = []

    quali_gap = float(features[0])
    grid_pos = int(round(float(features[1])))
    rolling_avg = float(features[3])
    pace_delta = float(features[4])
    dnf_risk = float(features[5])
    sc_prob = float(features[6])

    if quali_gap <= 0.05:
        reasons.append(f"{driver} starts on pole position")
    elif quali_gap < 0.3:
        reasons.append(f"{driver} qualified {quali_gap:.3f}s off pole — front row start")
    else:
        reasons.append(f"{driver} starts P{grid_pos}")

    if pace_delta < -0.2:
        reasons.append(f"{team} fastest in FP2 long runs on the {compound} compound")
    elif rolling_avg <= 4.0:
        reasons.append(f"{driver} averaged P{rolling_avg:.0f} over the last 5 races — strong form")
    elif overtaking_difficulty >= 8.0:
        reasons.append(f"Track position is decisive at {circuit_name} — overtaking is very difficult")
    else:
        reasons.append(f"{driver} starts P{grid_pos} — clean air from race start critical")

    if sc_prob >= 0.6:
        reasons.append(f"{circuit_name} averages a safety car in {round(sc_prob*100)}% of races")
    elif dnf_risk <= 0.05:
        reasons.append(f"{team} has a strong reliability record this season")
    else:
        reasons.append(f"{team} showed competitive pace in FP2 long runs")

    return reasons[:3]
