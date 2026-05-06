"""
Plain-English reason generation using advanced stats.

Produces exactly 3 reasons per prediction, ordered by signal strength:
  1. Net Rating — the most predictive single metric (points per 100 possessions)
  2. Elo + recent form — momentum and historical strength
  3. Four Factors edge — shooting efficiency, turnovers, and rest advantage
"""


def generate_reasons(
    home_team: str,
    away_team: str,
    home_stats: dict,
    away_stats: dict,
    home_recent: dict,
    away_recent: dict,
    home_elo: float,
    away_elo: float,
    home_rest: int,
    away_rest: int,
    predicted_winner: str,
) -> list[str]:
    """Return exactly 3 plain-English reason strings."""

    reasons = []

    # ------------------------------------------------------------------ #
    # Helper
    # ------------------------------------------------------------------ #
    def g(d, k, default=0.0):
        try:
            v = d.get(k, default)
            return float(v) if v is not None else default
        except (TypeError, ValueError):
            return default

    h_net  = g(home_stats, "net_rating")
    a_net  = g(away_stats, "net_rating")
    h_off  = g(home_stats, "off_rating", 110.0)
    a_off  = g(away_stats, "off_rating", 110.0)
    h_def  = g(home_stats, "def_rating", 110.0)
    a_def  = g(away_stats, "def_rating", 110.0)
    h_efg  = g(home_stats, "efg_pct", 0.52)
    a_efg  = g(away_stats, "efg_pct", 0.52)
    h_tov  = g(home_stats, "tov_pct", 13.0)
    a_tov  = g(away_stats, "tov_pct", 13.0)
    h_oreb = g(home_stats, "oreb_pct", 0.25)
    a_oreb = g(away_stats, "oreb_pct", 0.25)
    h_wp   = g(home_stats, "w_pct", 0.5)
    a_wp   = g(away_stats, "w_pct", 0.5)

    h_rwp  = g(home_recent, "recent_win_pct", h_wp)
    a_rwp  = g(away_recent, "recent_win_pct", a_wp)
    h_rnr  = g(home_recent, "recent_net_rtg", h_net)
    a_rnr  = g(away_recent, "recent_net_rtg", a_net)

    elo_diff = home_elo - away_elo
    net_diff = h_net - a_net

    # ------------------------------------------------------------------ #
    # Reason 1 — Net Rating (points per 100 possessions)
    # ------------------------------------------------------------------ #
    if abs(net_diff) >= 1.0:
        leader   = home_team if net_diff > 0 else away_team
        trailer  = away_team if net_diff > 0 else home_team
        l_net    = h_net if net_diff > 0 else a_net
        t_net    = a_net if net_diff > 0 else h_net
        l_off    = h_off if net_diff > 0 else a_off
        l_def    = h_def if net_diff > 0 else a_def
        reasons.append(
            f"{leader} holds a {l_net:+.1f} net rating (Off {l_off:.1f}, Def {l_def:.1f}) "
            f"vs {trailer}'s {t_net:+.1f} — a {abs(net_diff):.1f}-point-per-100-possession "
            f"edge that is the strongest predictor of NBA outcomes."
        )
    else:
        reasons.append(
            f"Net ratings are nearly identical ({home_team}: {h_net:+.1f}, "
            f"{away_team}: {a_net:+.1f}), so home-court advantage and "
            f"Elo ({home_elo:.0f} vs {away_elo:.0f}) become the decisive factors."
        )

    # ------------------------------------------------------------------ #
    # Reason 2 — Elo rating + recent form
    # ------------------------------------------------------------------ #
    rec_diff = h_rwp - a_rwp
    elo_leader = home_team if elo_diff >= 0 else away_team
    elo_trailer = away_team if elo_diff >= 0 else home_team

    if abs(rec_diff) >= 0.10:
        form_leader  = home_team if rec_diff > 0 else away_team
        form_trailer = away_team if rec_diff > 0 else home_team
        fl_pct = max(h_rwp, a_rwp)
        ft_pct = min(h_rwp, a_rwp)
        reasons.append(
            f"{form_leader} is the hotter team, winning {fl_pct:.0%} of their last 10 "
            f"games vs {form_trailer}'s {ft_pct:.0%}. "
            f"Elo ratings also favour {elo_leader} "
            f"({home_elo:.0f} vs {away_elo:.0f}, gap: {abs(elo_diff):.0f} pts)."
        )
    else:
        reasons.append(
            f"Recent form is evenly matched ({home_team}: {h_rwp:.0%}, "
            f"{away_team}: {a_rwp:.0%} last 10 games). "
            f"Elo gives {elo_leader} a {abs(elo_diff):.0f}-point edge "
            f"({home_elo:.0f} vs {away_elo:.0f})."
        )

    # ------------------------------------------------------------------ #
    # Reason 3 — Four Factors (eFG, TOV, OREB) and rest
    # ------------------------------------------------------------------ #
    rest_diff = home_rest - away_rest
    efg_diff  = h_efg - a_efg
    oreb_diff = h_oreb - a_oreb

    shooting_leader  = home_team if efg_diff >= 0 else away_team
    sl_efg = max(h_efg, a_efg)
    st_efg = min(h_efg, a_efg)

    if abs(rest_diff) >= 1:
        rested_team   = home_team if rest_diff > 0 else away_team
        fatigued_team = away_team if rest_diff > 0 else home_team
        rested_days   = max(home_rest, away_rest)
        fatigued_days = min(home_rest, away_rest)
        reasons.append(
            f"{rested_team} ({rested_days}d rest) has a fatigue edge over "
            f"{fatigued_team} ({fatigued_days}d rest). "
            f"Shooting efficiency: {shooting_leader} leads on eFG% "
            f"({sl_efg:.1%} vs {st_efg:.1%}). "
            f"Turnover rates: {home_team} {h_tov:.1f}% vs {away_team} {a_tov:.1f}%."
        )
    else:
        reasons.append(
            f"Both teams are equally rested ({home_rest}d). "
            f"{shooting_leader} holds the shooting edge: eFG% {sl_efg:.1%} vs {st_efg:.1%}. "
            f"Off. rebound rate: {home_team} {h_oreb:.1%} vs {away_team} {a_oreb:.1%}; "
            f"turnovers: {home_team} {h_tov:.1f}% vs {away_team} {a_tov:.1f}%."
        )

    return reasons
