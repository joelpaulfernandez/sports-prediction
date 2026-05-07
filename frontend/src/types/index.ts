export interface PredictionReason {
  text: string;
}

export interface TeamStats {
  net_rating: number;
  off_rating: number;
  def_rating: number;
  efg_pct: number;
  tov_pct: number;
  oreb_pct: number;
  w_pct: number;
  elo: number;
  recent_win_pct: number;
  recent_net_rtg: number;
  rest_days: number;
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
  home_pts?: number | null;
  away_pts?: number | null;
  home_stats?: TeamStats;
  away_stats?: TeamStats;
  model_version?: string;
}

export interface AccuracyStats {
  total_predictions: number;
  correct_predictions: number;
  accuracy_percentage: number;
  last_updated: string;
  model_cv_accuracy?: number;
  model_version?: string;
}
