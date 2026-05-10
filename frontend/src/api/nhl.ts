import http from './http';
import type { NHLGamePrediction, NHLAccuracyStats } from '../types';

const api = http;

export async function getNHLGames(): Promise<NHLGamePrediction[]> {
  const { data } = await api.get<NHLGamePrediction[]>('/nhl/games');
  return data;
}

export async function getNHLGame(gameId: string): Promise<NHLGamePrediction> {
  const { data } = await api.get<NHLGamePrediction>(`/nhl/games/${gameId}`);
  return data;
}

export async function getNHLAccuracy(): Promise<NHLAccuracyStats> {
  const { data } = await api.get<NHLAccuracyStats>('/nhl/accuracy');
  return data;
}
