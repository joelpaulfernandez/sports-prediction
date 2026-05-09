import http from './http';
import type { GamePrediction, AccuracyStats } from '../types';

const api = http;

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

import type { PlayoffBracket } from '../types/bracket';
export const getBracket = (): Promise<PlayoffBracket> =>
  api.get<PlayoffBracket>('/api/bracket').then((r) => r.data);
