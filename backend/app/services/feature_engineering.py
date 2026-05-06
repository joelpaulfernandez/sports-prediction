"""
Feature engineering for NBA game prediction.

Builds a 20-element feature vector for each matchup.  All features are framed
so that a positive value is "good for the home team", which aligns with the
model label (1 = home team wins).

Feature index map
─────────────────
 0  net_rtg_diff          home_net - away_net  (most predictive single stat)
 1  off_rtg_diff          home_off - away_off
 2  def_rtg_diff          away_def - home_def  (positive = home has better defense)
 3  pace_diff             home_pace - away_pace
 4  efg_pct_diff          home_efg - away_efg
 5  opp_efg_pct_diff      away_opp_efg - home_opp_efg  (defensive eFG allowed)
 6  tov_pct_diff          away_tov - home_tov  (positive = home forces more TOs)
 7  oreb_pct_diff         home_oreb - away_oreb
 8  fta_rate_diff         home_fta - away_fta
 9  win_pct_diff          home_wp - away_wp
10  home_win_pct          absolute home season W%
11  away_win_pct          absolute away season W%
12  recent_win_pct_diff   last-10 W% (home) - last-10 W% (away)
13  recent_net_rtg_diff   last-10 avg point diff (home) - (away)
14  elo_diff              (home_elo - away_elo) / 100  (normalized)
15  rest_diff             home_rest_days - away_rest_days
16  home_rest_days        capped at 7
17  away_rest_days        capped at 7
18  pts_margin_diff       home avg point margin - away avg point margin
19  home_court            always 1.0  (constant, learned weight = home advantage)
"""

import numpy as np

FEATURE_NAMES = [
    "net_rtg_diff",
    "off_rtg_diff",
    "def_rtg_diff",
    "pace_diff",
    "efg_pct_diff",
    "opp_efg_pct_diff",
    "tov_pct_diff",
    "oreb_pct_diff",
    "fta_rate_diff",
    "win_pct_diff",
    "home_win_pct",
    "away_win_pct",
    "recent_win_pct_diff",
    "recent_net_rtg_diff",
    "elo_diff",
    "rest_diff",
    "home_rest_days",
    "away_rest_days",
    "pts_margin_diff",
    "home_court",
]

N_FEATURES = len(FEATURE_NAMES)


def _g(d: dict, key: str, default: float = 0.0) -> float:
    try:
        v = d.get(key, default)
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def build_features(
    home_stats: dict,
    away_stats: dict,
    home_recent: dict,
    away_recent: dict,
    home_elo: float,
    away_elo: float,
    home_rest: int,
    away_rest: int,
) -> np.ndarray:
    """
    Return a float32 array of shape (N_FEATURES,) for a single matchup.

    Parameters
    ----------
    home_stats / away_stats : dicts from nba_data.get_all_team_stats()
    home_recent / away_recent : dicts from nba_data.compute_team_recent_form()
    home_elo / away_elo : current Elo ratings from EloSystem
    home_rest / away_rest : days since last game (1-7)
    """
    h, a = home_stats, away_stats
    hr, ar = home_recent, away_recent

    h_net  = _g(h, "net_rating")
    a_net  = _g(a, "net_rating")
    h_off  = _g(h, "off_rating", 110.0)
    a_off  = _g(a, "off_rating", 110.0)
    h_def  = _g(h, "def_rating", 110.0)
    a_def  = _g(a, "def_rating", 110.0)
    h_pace = _g(h, "pace", 100.0)
    a_pace = _g(a, "pace", 100.0)
    h_efg  = _g(h, "efg_pct", 0.52)
    a_efg  = _g(a, "efg_pct", 0.52)
    h_oefg = _g(h, "opp_efg_pct", 0.52)   # defensive eFG allowed
    a_oefg = _g(a, "opp_efg_pct", 0.52)
    h_tov  = _g(h, "tov_pct", 13.0)
    a_tov  = _g(a, "tov_pct", 13.0)
    h_oreb = _g(h, "oreb_pct", 0.25)
    a_oreb = _g(a, "oreb_pct", 0.25)
    h_fta  = _g(h, "fta_rate", 0.25)
    a_fta  = _g(a, "fta_rate", 0.25)
    h_wp   = _g(h, "w_pct", 0.5)
    a_wp   = _g(a, "w_pct", 0.5)
    h_pm   = _g(h, "plus_minus")   # avg point margin
    a_pm   = _g(a, "plus_minus")

    h_rwp  = _g(hr, "recent_win_pct", h_wp)
    a_rwp  = _g(ar, "recent_win_pct", a_wp)
    h_rnr  = _g(hr, "recent_net_rtg", h_net)
    a_rnr  = _g(ar, "recent_net_rtg", a_net)

    features = np.array([
        h_net - a_net,                        #  0 net_rtg_diff
        h_off - a_off,                        #  1 off_rtg_diff
        a_def - h_def,                        #  2 def_rtg_diff (pos = home better D)
        h_pace - a_pace,                      #  3 pace_diff
        h_efg - a_efg,                        #  4 efg_pct_diff
        a_oefg - h_oefg,                      #  5 opp_efg_pct_diff (pos = home better D)
        a_tov - h_tov,                        #  6 tov_pct_diff (pos = home forces more)
        h_oreb - a_oreb,                      #  7 oreb_pct_diff
        h_fta - a_fta,                        #  8 fta_rate_diff
        h_wp - a_wp,                          #  9 win_pct_diff
        h_wp,                                 # 10 home_win_pct
        a_wp,                                 # 11 away_win_pct
        h_rwp - a_rwp,                        # 12 recent_win_pct_diff
        h_rnr - a_rnr,                        # 13 recent_net_rtg_diff
        (home_elo - away_elo) / 100.0,        # 14 elo_diff (normalized)
        float(home_rest) - float(away_rest),  # 15 rest_diff
        float(home_rest),                     # 16 home_rest_days
        float(away_rest),                     # 17 away_rest_days
        h_pm - a_pm,                          # 18 pts_margin_diff
        1.0,                                  # 19 home_court
    ], dtype=np.float32)

    return features
