from typing import Literal, Optional
from pydantic import BaseModel, Field


class PredictionReason(BaseModel):
    text: str


class TeamStats(BaseModel):
    """Advanced stats for one team in a matchup — sent to the frontend for display."""
    net_rating: float
    off_rating: float
    def_rating: float
    efg_pct: float
    tov_pct: float
    oreb_pct: float
    w_pct: float
    elo: float
    recent_win_pct: float   # last 10 games
    recent_net_rtg: float   # avg point diff over last 10 games
    rest_days: int


class GamePrediction(BaseModel):
    game_id: str
    home_team: str
    away_team: str
    predicted_winner: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    predicted_home_score: int
    predicted_away_score: int
    reasons: list[PredictionReason]
    game_date: str
    status: Literal["scheduled", "live", "finished"]
    home_pts: Optional[int] = None
    away_pts: Optional[int] = None
    home_stats: Optional[TeamStats] = None
    away_stats: Optional[TeamStats] = None
    model_version: str = "rule-based"


class AccuracyStats(BaseModel):
    total_predictions: int
    correct_predictions: int
    accuracy_percentage: float
    last_updated: str
    model_cv_accuracy: Optional[float] = None
    model_version: str = "rule-based"
