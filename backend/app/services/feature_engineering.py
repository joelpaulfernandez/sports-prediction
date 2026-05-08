"""
Feature engineering for NBA game prediction.

All features are framed so that a positive value is "good for the home team",
which aligns with the model label (1 = home team wins).

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
20  is_playoff            1.0 for playoff games, 0.0 for regular season

Player availability features (added in v2)
──────────────────────────────────────────
21  star_min_ratio_diff   home star_minutes_ratio - away star_minutes_ratio
22  top3_min_ratio_diff   home top3_minutes_ratio - away top3_minutes_ratio
23  rotation_size_diff    home rotation_size      - away rotation_size
24  home_star_min_ratio   absolute home star minutes share (last 3 games)
25  away_star_min_ratio   absolute away star minutes share

Style / matchup features (added in v3)
──────────────────────────────────────
26  home_efg_edge        h_efg - a_opp_efg   (home offense vs away defense eFG)
27  away_efg_edge        a_efg - h_opp_efg   (away offense vs home defense eFG)
28  home_ft_edge         h_fta_rate - a_opp_fta_rate
29  away_ft_edge         a_fta_rate - h_opp_fta_rate
30  pace_abs_diff        |h_pace - a_pace|   (high-friction matchup signal)

Context features (added in v4)
──────────────────────────────
31  home_is_b2b          1.0 if home team played yesterday, else 0.0
32  away_is_b2b          1.0 if away team played yesterday, else 0.0
33  home_home_w_pct      home team's win % in home games this season
34  away_road_w_pct      away team's win % in road games this season
35  venue_w_pct_diff     home_home_w_pct - away_road_w_pct

Playoff / matchup history features (added in v5)
────────────────────────────────────────────────
36  home_won_last_h2h    +1.0 if home won most recent prior meeting,
                         -1.0 if away won it, 0.0 if no prior meetings
37  series_lead          (home_wins - away_wins) in current playoff series
                         before this game; 0.0 for non-playoff games
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
    "is_playoff",
    "star_min_ratio_diff",
    "top3_min_ratio_diff",
    "rotation_size_diff",
    "home_star_min_ratio",
    "away_star_min_ratio",
    "home_efg_edge",
    "away_efg_edge",
    "home_ft_edge",
    "away_ft_edge",
    "pace_abs_diff",
    "home_is_b2b",
    "away_is_b2b",
    "home_home_w_pct",
    "away_road_w_pct",
    "venue_w_pct_diff",
    "home_won_last_h2h",
    "series_lead",
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
    is_playoff: bool = False,
    home_avail: dict | None = None,
    away_avail: dict | None = None,
    home_splits: dict | None = None,
    away_splits: dict | None = None,
    h2h: dict | None = None,
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

    # Player availability — falls back to neutral defaults when missing
    h_avail = home_avail or {}
    a_avail = away_avail or {}
    h_star_ratio = _g(h_avail, "star_minutes_ratio", 0.20)
    a_star_ratio = _g(a_avail, "star_minutes_ratio", 0.20)
    h_top3_ratio = _g(h_avail, "top3_minutes_ratio", 0.45)
    a_top3_ratio = _g(a_avail, "top3_minutes_ratio", 0.45)
    h_rot_size = _g(h_avail, "rotation_size", 9.0)
    a_rot_size = _g(a_avail, "rotation_size", 9.0)

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
        1.0 if is_playoff else 0.0,           # 20 is_playoff
        h_star_ratio - a_star_ratio,          # 21 star_min_ratio_diff
        h_top3_ratio - a_top3_ratio,          # 22 top3_min_ratio_diff
        h_rot_size - a_rot_size,              # 23 rotation_size_diff
        h_star_ratio,                         # 24 home_star_min_ratio
        a_star_ratio,                         # 25 away_star_min_ratio
        h_efg - a_oefg,                       # 26 home_efg_edge (offense vs defense)
        a_efg - h_oefg,                       # 27 away_efg_edge
        h_fta - _g(a, "opp_fta_rate", 0.25),  # 28 home_ft_edge
        a_fta - _g(h, "opp_fta_rate", 0.25),  # 29 away_ft_edge
        abs(h_pace - a_pace),                 # 30 pace_abs_diff
        # Context features (B2B + venue splits)
        1.0 if int(home_rest) <= 1 else 0.0,  # 31 home_is_b2b
        1.0 if int(away_rest) <= 1 else 0.0,  # 32 away_is_b2b
        _g(home_splits or {}, "home_w_pct", 0.5),   # 33 home_home_w_pct
        _g(away_splits or {}, "road_w_pct", 0.5),   # 34 away_road_w_pct
        _g(home_splits or {}, "home_w_pct", 0.5)
            - _g(away_splits or {}, "road_w_pct", 0.5),  # 35 venue_w_pct_diff
        _g(h2h or {}, "home_won_last", 0.0),    # 36 home_won_last_h2h
        _g(h2h or {}, "series_lead", 0.0),      # 37 series_lead
    ], dtype=np.float32)

    return features
