export interface BracketGame {
  game_id: string;
  date: string;
  home_team_id: number;
  away_team_id: number;
  home_team_name: string;
  away_team_name: string;
  home_pts: number | null;
  away_pts: number | null;
  actual_winner_id: number | null;
  predicted_winner_name: string | null;
  confidence: number | null;
  correct: boolean | null;
}

export interface BracketTeam {
  team_id: number;
  team_name: string;
  wins: number;
}

export interface BracketSeries {
  first_game_date: string;
  higher_seed: BracketTeam;
  lower_seed: BracketTeam;
  winner_team_id: number | null;
  games: BracketGame[];
}

export interface BracketRound {
  name: string;
  round_number: number;
  series: BracketSeries[];
}

export interface BracketSummary {
  total_games: number;
  games_with_prediction: number;
  correct_predictions: number;
  accuracy_pct: number;
}

export interface PlayoffBracket {
  season: string;
  rounds: BracketRound[];
  summary: BracketSummary;
}
