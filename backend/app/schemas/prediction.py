from pydantic import BaseModel, Field
from typing import Literal


class PredictionReason(BaseModel):
    text: str


class GamePrediction(BaseModel):
    game_id: str
    home_team: str
    away_team: str
    predicted_winner: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    predicted_home_score: int
    predicted_away_score: int
    reasons: list[PredictionReason]  # exactly 3
    game_date: str
    status: Literal["scheduled", "live", "finished"]


class AccuracyStats(BaseModel):
    total_predictions: int
    correct_predictions: int
    accuracy_percentage: float
    last_updated: str
