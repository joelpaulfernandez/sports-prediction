def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _win_pct(stats: dict) -> float:
    wins = _safe_float(stats.get("wins", {}).get("all", {}).get("total", 0))
    losses = _safe_float(stats.get("losses", {}).get("all", {}).get("total", 0))
    total = wins + losses
    return wins / total if total > 0 else 0.5


def _avg_ppg(stats: dict) -> float:
    return _safe_float(
        stats.get("points", {}).get("for", {}).get("average", {}).get("all", 105)
    )


def _home_record(stats: dict) -> tuple[int, int]:
    hw = int(_safe_float(stats.get("wins", {}).get("home", {}).get("total", 0)))
    hl = int(_safe_float(stats.get("losses", {}).get("home", {}).get("total", 0)))
    return hw, hl


def generate_reasons(
    home_team: str,
    away_team: str,
    home_stats: dict,
    away_stats: dict,
    predicted_winner: str,
) -> list[str]:
    """Generate exactly 3 plain-English reasons for a prediction.

    Args:
        home_team: Display name of the home team.
        away_team: Display name of the away team.
        home_stats: Stats dict from sports_api.get_team_stats().
        away_stats: Stats dict from sports_api.get_team_stats().
        predicted_winner: Display name of the predicted winner.

    Returns:
        A list of 3 reason strings.
    """
    home_ppg = _avg_ppg(home_stats)
    away_ppg = _avg_ppg(away_stats)
    home_wp = _win_pct(home_stats)
    away_wp = _win_pct(away_stats)
    home_hw, home_hl = _home_record(home_stats)

    # Reason 1 — Recent scoring form
    if home_ppg >= away_ppg:
        leader, leader_ppg, trailer, trailer_ppg = home_team, home_ppg, away_team, away_ppg
    else:
        leader, leader_ppg, trailer, trailer_ppg = away_team, away_ppg, home_team, home_ppg

    reason_1 = (
        f"{leader} averaged {leader_ppg:.1f} points per game this season, "
        f"outscoring {trailer} who average {trailer_ppg:.1f} ppg."
    )

    # Reason 2 — Win percentage comparison
    home_wp_pct = round(home_wp * 100)
    away_wp_pct = round(away_wp * 100)
    if home_wp >= away_wp:
        reason_2 = (
            f"{home_team} hold a {home_wp_pct}% win rate this season "
            f"compared to {away_team}'s {away_wp_pct}%, giving the home side the statistical edge."
        )
    else:
        reason_2 = (
            f"{away_team} enter this game with a {away_wp_pct}% win rate "
            f"vs {home_team}'s {home_wp_pct}%, making them the slight favorites despite being on the road."
        )

    # Reason 3 — Home court factor
    if predicted_winner == home_team:
        reason_3 = (
            f"{home_team} are {home_hw}-{home_hl} at home this season, "
            "and home-court advantage is a strong factor in tonight's matchup."
        )
    else:
        reason_3 = (
            f"Despite {home_team} being {home_hw}-{home_hl} at home, "
            f"{away_team}'s road form and superior overall record make them the pick tonight."
        )

    return [reason_1, reason_2, reason_3]
