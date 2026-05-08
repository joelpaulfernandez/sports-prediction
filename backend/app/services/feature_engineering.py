"""
Feature engineering for NBA game prediction.

WHAT THIS FILE DOES (in plain English)
──────────────────────────────────────
Before our model can guess who'll win a game, we have to translate everything
we know about the two teams into a list of numbers. That list of numbers is
called the "feature vector," and this file is what builds it.

Think of it like filling out a scouting report card:
  • How good is each team overall?
  • How well have they played recently?
  • Is this a playoff game?
  • Are their stars healthy?
  • How many days of rest does each team have?

Every entry in the feature vector is a single comparison between the two
teams. We line them up so that a POSITIVE number always means "this is good
for the home team" — that way the model has a consistent signal: bigger
positive numbers → home team is more likely to win.

When the model trains, it learns which of these 38 numbers matter the most
and how to weigh them. When we use the model to predict a game, we hand it a
fresh feature vector for that matchup and it spits back a probability.

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

from __future__ import annotations

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


# Tiny helper: safely pulls a number out of a dictionary.
# If the key is missing, the value is None, or the value can't be converted
# to a float, we just return the `default` instead of crashing. This keeps
# the rest of the code clean — every stat lookup uses this so we never have
# to worry about half-missing data breaking a prediction.
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
    Build the 38-number scouting report for a single matchup.

    What we're handed:
      home_stats / away_stats — season-long averages (offense, defense, pace…)
      home_recent / away_recent — how each team has played in their last 10 games
      home_elo / away_elo — Elo rating (a single number summarizing each team's
                             strength, like a chess rating)
      home_rest / away_rest — days since each team's last game
      is_playoff — True for playoff games, False for regular season
      home_avail / away_avail — rotation strength (proxy for "are stars playing?")
      home_splits / away_splits — home record and road record separately
      h2h — head-to-head history between these two teams

    What we return: a list of 38 numbers, ready for the model.
    """
    # Short aliases so the math below is readable. h = home, a = away.
    h, a = home_stats, away_stats
    hr, ar = home_recent, away_recent

    # ── Pull every season-long stat we need, with sensible defaults. ──
    # Defaults are league-average values so missing data doesn't skew predictions.
    h_net  = _g(h, "net_rating")           # net rating: points scored minus allowed per 100 possessions
    a_net  = _g(a, "net_rating")           # the single best summary of team quality
    h_off  = _g(h, "off_rating", 110.0)    # offensive rating: points scored per 100 possessions
    a_off  = _g(a, "off_rating", 110.0)
    h_def  = _g(h, "def_rating", 110.0)    # defensive rating: points allowed per 100 possessions
    a_def  = _g(a, "def_rating", 110.0)    # (lower is better for defense)
    h_pace = _g(h, "pace", 100.0)          # pace: how many possessions per game (fast vs slow team)
    a_pace = _g(a, "pace", 100.0)
    h_efg  = _g(h, "efg_pct", 0.52)        # effective FG%: shooting accuracy that gives 3PT bonus weight
    a_efg  = _g(a, "efg_pct", 0.52)
    h_oefg = _g(h, "opp_efg_pct", 0.52)    # opponent eFG%: how well opponents shoot against you (low = good D)
    a_oefg = _g(a, "opp_efg_pct", 0.52)
    h_tov  = _g(h, "tov_pct", 13.0)        # turnover %: how often you cough up the ball
    a_tov  = _g(a, "tov_pct", 13.0)
    h_oreb = _g(h, "oreb_pct", 0.25)       # offensive rebound %: extra possessions you grab
    a_oreb = _g(a, "oreb_pct", 0.25)
    h_fta  = _g(h, "fta_rate", 0.25)       # free throw rate: how often you get to the line
    a_fta  = _g(a, "fta_rate", 0.25)
    h_wp   = _g(h, "w_pct", 0.5)           # season win %
    a_wp   = _g(a, "w_pct", 0.5)
    h_pm   = _g(h, "plus_minus")           # average point margin per game
    a_pm   = _g(a, "plus_minus")

    # ── Recent form (last 10 games) ──
    # Falls back to season averages if recent data isn't available.
    h_rwp  = _g(hr, "recent_win_pct", h_wp)   # win % over the last 10 games
    a_rwp  = _g(ar, "recent_win_pct", a_wp)
    h_rnr  = _g(hr, "recent_net_rtg", h_net)  # average point margin over last 10
    a_rnr  = _g(ar, "recent_net_rtg", a_net)

    # ── Player availability (proxy for injuries) ──
    # We can't easily get an injury report, so instead we look at recent minutes:
    #   star_minutes_ratio — what share of total minutes did the team's top
    #     scorer play recently? When a star is out, this drops near zero.
    #   top3_minutes_ratio — same idea for the top three scorers combined.
    #   rotation_size — how many players are getting real minutes? Drops when
    #     the team is missing depth.
    # If we don't have data, defaults assume a healthy normal rotation.
    h_avail = home_avail or {}
    a_avail = away_avail or {}
    h_star_ratio = _g(h_avail, "star_minutes_ratio", 0.20)
    a_star_ratio = _g(a_avail, "star_minutes_ratio", 0.20)
    h_top3_ratio = _g(h_avail, "top3_minutes_ratio", 0.45)
    a_top3_ratio = _g(a_avail, "top3_minutes_ratio", 0.45)
    h_rot_size = _g(h_avail, "rotation_size", 9.0)
    a_rot_size = _g(a_avail, "rotation_size", 9.0)

    # ─────────────────────────────────────────────────────────────────
    # Build the feature vector: 38 numbers, one row per matchup.
    #
    # Convention: a positive value means "good for the home team."
    # So the model can read every number the same way: "bigger = home wins."
    # ─────────────────────────────────────────────────────────────────
    features = np.array([
        h_net - a_net,                        #  0 net_rtg_diff — home strength minus away strength (the single best signal)
        h_off - a_off,                        #  1 off_rtg_diff — home offense minus away offense
        a_def - h_def,                        #  2 def_rtg_diff — flipped so positive means home plays better defense
        h_pace - a_pace,                      #  3 pace_diff — does home want a faster game than away?
        h_efg - a_efg,                        #  4 efg_pct_diff — home's shooting efficiency edge
        a_oefg - h_oefg,                      #  5 opp_efg_pct_diff — flipped so positive means home defends shooting better
        a_tov - h_tov,                        #  6 tov_pct_diff — flipped so positive means home protects the ball more
        h_oreb - a_oreb,                      #  7 oreb_pct_diff — home's edge on offensive rebounds (extra possessions)
        h_fta - a_fta,                        #  8 fta_rate_diff — home's edge in drawing free throws
        h_wp - a_wp,                          #  9 win_pct_diff — home's win rate edge over the season
        h_wp,                                 # 10 home_win_pct — absolute home win rate (also gives the model a level)
        a_wp,                                 # 11 away_win_pct — absolute away win rate
        h_rwp - a_rwp,                        # 12 recent_win_pct_diff — last 10 games hot-streak edge
        h_rnr - a_rnr,                        # 13 recent_net_rtg_diff — last 10 games margin edge
        (home_elo - away_elo) / 100.0,        # 14 elo_diff — Elo rating difference (divided by 100 to keep numbers small)
        float(home_rest) - float(away_rest),  # 15 rest_diff — home days of rest minus away
        float(home_rest),                     # 16 home_rest_days — home's actual rest (back-to-backs hurt)
        float(away_rest),                     # 17 away_rest_days — away's actual rest
        h_pm - a_pm,                          # 18 pts_margin_diff — home's average margin minus away's
        1.0,                                  # 19 home_court — always 1 (the model learns the typical home-court bonus)
        1.0 if is_playoff else 0.0,           # 20 is_playoff — flag so the model can adjust for playoff intensity
        h_star_ratio - a_star_ratio,          # 21 star_min_ratio_diff — home star availability minus away (proxy for star injuries)
        h_top3_ratio - a_top3_ratio,          # 22 top3_min_ratio_diff — same idea, but for the top three scorers combined
        h_rot_size - a_rot_size,              # 23 rotation_size_diff — depth edge (fewer guys playing = depleted team)
        h_star_ratio,                         # 24 home_star_min_ratio — absolute home star availability
        a_star_ratio,                         # 25 away_star_min_ratio — absolute away star availability
        # ── Style matchups (does each team's strength meet the other's weakness?) ──
        h_efg - a_oefg,                       # 26 home_efg_edge — home's shooting vs away's shooting defense
        a_efg - h_oefg,                       # 27 away_efg_edge — away's shooting vs home's shooting defense
        h_fta - _g(a, "opp_fta_rate", 0.25),  # 28 home_ft_edge — home draws fouls vs away allows fouls
        a_fta - _g(h, "opp_fta_rate", 0.25),  # 29 away_ft_edge — away draws fouls vs home allows fouls
        abs(h_pace - a_pace),                 # 30 pace_abs_diff — how mismatched are their tempos? (style clash)
        # ── Context: schedule and venue ──
        1.0 if int(home_rest) <= 1 else 0.0,  # 31 home_is_b2b — flag for "home played yesterday" (back-to-back fatigue)
        1.0 if int(away_rest) <= 1 else 0.0,  # 32 away_is_b2b — same for the away team
        _g(home_splits or {}, "home_w_pct", 0.5),   # 33 home_home_w_pct — home team's record specifically AT HOME
        _g(away_splits or {}, "road_w_pct", 0.5),   # 34 away_road_w_pct — away team's record specifically ON THE ROAD
        _g(home_splits or {}, "home_w_pct", 0.5)
            - _g(away_splits or {}, "road_w_pct", 0.5),  # 35 venue_w_pct_diff — venue-adjusted strength gap
        # ── Head-to-head and playoff series state ──
        _g(h2h or {}, "home_won_last", 0.0),    # 36 home_won_last_h2h — +1 if home won the most recent meeting, -1 if away did, 0 otherwise
        _g(h2h or {}, "series_lead", 0.0),      # 37 series_lead — current playoff series score (home wins minus away wins)
    ], dtype=np.float32)

    # Final result: a list of 38 floating-point numbers ready for the model.
    return features
