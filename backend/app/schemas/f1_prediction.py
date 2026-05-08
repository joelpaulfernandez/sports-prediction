from typing import Literal, Optional
from pydantic import BaseModel, Field


class F1PredictionReason(BaseModel):
    text: str


class F1DriverPrediction(BaseModel):
    position: int
    driver: str
    driver_id: str
    team: str
    driver_number: Optional[str] = None
    win_prob: float = Field(..., ge=0.0, le=1.0)
    podium_prob: float = Field(..., ge=0.0, le=1.0)
    confidence_score: int = Field(..., ge=0, le=100)
    reasons: list[F1PredictionReason]
    quali_position: Optional[int] = None
    grid_position: Optional[int] = None


class F1RacePrediction(BaseModel):
    race_id: str
    event: str
    circuit: str
    circuit_key: str
    circuit_country: str
    race_date: str
    race_time_utc: Optional[str] = None
    season: int
    round: int
    predictions: list[F1DriverPrediction]
    circuit_variance: Literal["high", "normal"]
    model_confidence: Literal["high", "medium", "low"]
    model_version: str = "rule-based"
    data_freshness: str


class F1AccuracyBreakdown(BaseModel):
    total: int
    winner_correct: int
    podium_2of3: int
    winner_accuracy: float
    podium_accuracy: float
    avg_rank_correlation: Optional[float] = None


class F1AccuracyStats(BaseModel):
    last_3_races: F1AccuracyBreakdown
    current_season: F1AccuracyBreakdown
    permanent_circuits: F1AccuracyBreakdown
    street_circuits: F1AccuracyBreakdown
    high_confidence: F1AccuracyBreakdown
    low_confidence: F1AccuracyBreakdown
    last_updated: str
    model_version: str = "rule-based"
