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
  home_team_id?: number | null;
  away_team_id?: number | null;
  predicted_winner: string;
  confidence: number;
  predicted_home_score: number;
  predicted_away_score: number;
  reasons: PredictionReason[];
  game_date: string;
  status: string;
  home_pts?: number | null;
  away_pts?: number | null;
  game_time_utc?: string | null;
  pregame_locked?: boolean;
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

// ── F1 types ──────────────────────────────────────────────────────────────────

export interface F1DriverPrediction {
  position: number;
  driver: string;
  driver_id: string;
  team: string;
  driver_number?: string | null;
  win_prob: number;
  podium_prob: number;
  confidence_score: number;
  reasons: PredictionReason[];
  quali_position?: number | null;
  grid_position?: number | null;
}

export interface F1RacePrediction {
  race_id: string;
  event: string;
  circuit: string;
  circuit_key: string;
  circuit_country: string;
  race_date: string;
  race_time_utc?: string | null;
  season: number;
  round: number;
  predictions: F1DriverPrediction[];
  circuit_variance: 'high' | 'normal';
  model_confidence: 'high' | 'medium' | 'low';
  model_version?: string;
  data_freshness: string;
}

export interface F1RaceSummary {
  race_id: string;
  event: string;
  circuit: string;
  circuit_country: string;
  circuit_variance: 'high' | 'normal';
  race_date: string;
  race_time_utc?: string | null;
  round: number;
  season: number;
}

export interface F1AccuracyBreakdown {
  total: number;
  winner_correct: number;
  podium_2of3: number;
  winner_accuracy: number;
  podium_accuracy: number;
  avg_rank_correlation?: number | null;
}

export interface F1ResultDriver {
  position: number;
  driver: string;
  driver_id: string;
  team: string;
  win_prob?: number;
  podium_prob?: number;
  status?: string;
}

export interface F1RecentResult {
  race_id: string;
  event: string;
  circuit: string;
  circuit_country: string;
  circuit_variance: 'high' | 'normal';
  race_date: string;
  round: number;
  season: number;
  winner_correct: boolean;
  podium_overlap: number;
  spearman: number | null;
  model_version: string;
  predicted: F1ResultDriver[];
  actual: F1ResultDriver[];
}

export interface F1AccuracyStats {
  last_3_races: F1AccuracyBreakdown;
  current_season: F1AccuracyBreakdown;
  permanent_circuits: F1AccuracyBreakdown;
  street_circuits: F1AccuracyBreakdown;
  high_confidence: F1AccuracyBreakdown;
  low_confidence: F1AccuracyBreakdown;
  last_updated: string;
  model_version?: string;
}
