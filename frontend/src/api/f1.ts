import axios from 'axios';
import type { F1RaceSummary, F1RacePrediction, F1AccuracyStats, F1RecentResult } from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

export async function getF1Races(): Promise<F1RaceSummary[]> {
  const { data } = await api.get<F1RaceSummary[]>('/f1/races');
  return data;
}

export async function getF1RacePrediction(raceId: string): Promise<F1RacePrediction> {
  const { data } = await api.get<F1RacePrediction>(`/f1/races/${raceId}/predictions`);
  return data;
}

export async function getF1Accuracy(): Promise<F1AccuracyStats> {
  const { data } = await api.get<F1AccuracyStats>('/f1/accuracy');
  return data;
}

export async function getF1RecentResults(n = 5): Promise<F1RecentResult[]> {
  const { data } = await api.get<F1RecentResult[]>(`/f1/recent-results?n=${n}`);
  return data;
}
