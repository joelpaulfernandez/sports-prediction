export interface PredictionReason {
  text: string;
}

export interface GamePrediction {
  game_id: string;
  home_team: string;
  away_team: string;
  predicted_winner: string;
  confidence: number;
  predicted_home_score: number;
  predicted_away_score: number;
  reasons: PredictionReason[];
  game_date: string;
  status: string;
}

export interface AccuracyStats {
  total_predictions: number;
  correct_predictions: number;
  accuracy_percentage: number;
  last_updated: string;
}
