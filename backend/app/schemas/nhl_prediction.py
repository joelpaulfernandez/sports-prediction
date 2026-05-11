from typing import Literal, Optional
from pydantic import BaseModel, Field


class NHLPredictionReason(BaseModel):
    text: str


class NHLTeamStats(BaseModel):
    wins: int
    losses: int
    ot_losses: int
    points: int
    points_pct: float
    goals_for_per_game: float
    goals_against_per_game: float
    pp_pct: float
    pk_pct: float
    save_pct: float
    shots_for_per_game: float
    shots_against_per_game: float


class NHLGamePrediction(BaseModel):
    game_id: str
    home_team: str
    home_team_abbrev: str
    away_team: str
    away_team_abbrev: str
    game_date: str
    game_time_utc: Optional[str] = None
    status: Literal["scheduled", "live", "finished"]
    predicted_winner: str
    predicted_winner_abbrev: str
    home_win_prob: float = Field(..., ge=0.0, le=1.0)
    confidence: int = Field(..., ge=0, le=100)
    model_confidence: Literal["high", "medium", "low"]
    reasons: list[NHLPredictionReason]
    home_stats: Optional[NHLTeamStats] = None
    away_stats: Optional[NHLTeamStats] = None
    # actual result (populated after game completes)
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    model_version: str = "nhl-stats-v1"


class NHLAccuracyStats(BaseModel):
    total_predictions: int
    correct_predictions: int
    accuracy_percentage: float
    last_updated: str
    model_version: str = "nhl-stats-v1"
    backtest_accuracy: float = 0.586
    backtest_games: int = 1324
