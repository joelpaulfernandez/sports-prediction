"""
Elo rating system for NBA teams.

Uses the standard chess Elo formula with:
  - Initial rating: 1500
  - K-factor: 20 (responsive to recent results)
  - Home-court adjustment: +100 rating points in the win-expectancy calculation
    (equivalent to ~3-4 point spread, matching historical NBA home-court data)

Ratings are computed by replaying all games in chronological order from the
season game log. Process multiple seasons sequentially for continuity.
"""

import pandas as pd

INITIAL_RATING = 1500.0
K_FACTOR = 20.0
HOME_ADVANTAGE = 100.0  # effective Elo points added to home team's rating


class EloSystem:
    def __init__(self) -> None:
        self.ratings: dict[int, float] = {}

    def get(self, team_id: int) -> float:
        return self.ratings.get(team_id, INITIAL_RATING)

    def _expected(self, rating_a: float, rating_b: float) -> float:
        """Probability that team A beats team B given their ratings."""
        return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))

    def update(self, home_id: int, away_id: int, home_won: bool) -> None:
        """Update ratings after one game."""
        home_r = self.get(home_id)
        away_r = self.get(away_id)

        # Home team gets the advantage bonus in the expectation calculation
        home_exp = self._expected(home_r + HOME_ADVANTAGE, away_r)
        away_exp = 1.0 - home_exp

        home_actual = 1.0 if home_won else 0.0
        away_actual = 1.0 - home_actual

        self.ratings[home_id] = home_r + K_FACTOR * (home_actual - home_exp)
        self.ratings[away_id] = away_r + K_FACTOR * (away_actual - away_exp)

    def process_game_log(self, game_log: pd.DataFrame) -> "EloSystem":
        """
        Replay all games in `game_log` chronologically to compute final Elo ratings.
        Each game must appear twice (one row per team). Home rows have "vs." in MATCHUP;
        away rows have "@".
        Returns self for chaining.
        """
        if game_log is None or game_log.empty:
            return self

        gl = game_log.copy()
        gl["is_home"] = gl["MATCHUP"].str.contains(r" vs\. ")
        gl["GAME_DATE"] = pd.to_datetime(gl["GAME_DATE"])

        # Pair home/away rows for each game, process in date order
        unique_game_ids = (
            gl.drop_duplicates("GAME_ID")
            .sort_values("GAME_DATE")["GAME_ID"]
            .tolist()
        )

        for gid in unique_game_ids:
            rows = gl[gl["GAME_ID"] == gid]
            home_rows = rows[rows["is_home"]]
            away_rows = rows[~rows["is_home"]]

            if home_rows.empty or away_rows.empty:
                continue

            home_id = int(home_rows.iloc[0]["TEAM_ID"])
            away_id = int(away_rows.iloc[0]["TEAM_ID"])
            home_won = str(home_rows.iloc[0]["WL"]) == "W"

            self.update(home_id, away_id, home_won)

        return self

    def snapshot_at(self, game_log: pd.DataFrame, before_date: str) -> "EloSystem":
        """
        Return a new EloSystem with ratings computed only from games before `before_date`.
        Useful for building leak-free training features.
        """
        cutoff = pd.Timestamp(before_date)
        filtered = game_log[pd.to_datetime(game_log["GAME_DATE"]) < cutoff]
        snapshot = EloSystem()
        snapshot.process_game_log(filtered)
        return snapshot
