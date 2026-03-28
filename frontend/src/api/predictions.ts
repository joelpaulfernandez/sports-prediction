import axios from 'axios';
import type { GamePrediction, AccuracyStats } from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

export const getGames = (): Promise<GamePrediction[]> =>
  api.get<GamePrediction[]>('/api/predictions/games').then((r) => r.data);

export const getGame = (id: string): Promise<GamePrediction> =>
  api.get<GamePrediction>(`/api/predictions/games/${id}`).then((r) => r.data);

export const getAccuracy = (): Promise<AccuracyStats> =>
  api.get<AccuracyStats>('/api/accuracy').then((r) => r.data);
