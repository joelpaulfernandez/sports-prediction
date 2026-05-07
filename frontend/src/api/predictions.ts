import axios from 'axios';
import type { GamePrediction, AccuracyStats } from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

// Send the client's local date (YYYY-MM-DD) so the backend uses the right day
// regardless of server timezone — same as how Google shows local game times.
function localDateStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export const getGames = (): Promise<GamePrediction[]> =>
  api.get<GamePrediction[]>('/api/predictions/games', { params: { date: localDateStr() } }).then((r) => r.data);

export const getGame = (id: string): Promise<GamePrediction> =>
  api.get<GamePrediction>(`/api/predictions/games/${id}`).then((r) => r.data);

export const getAccuracy = (): Promise<AccuracyStats> =>
  api.get<AccuracyStats>('/api/accuracy').then((r) => r.data);
