import { useEffect, useState } from 'react';
import { GamePrediction, AccuracyStats } from '../types';
import { getGames, getAccuracy } from '../api/predictions';
import { PredictionCard } from '../components/PredictionCard';
import { AccuracyBanner } from '../components/AccuracyBanner';

function Spinner() {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '16px',
        padding: '80px 0',
      }}
    >
      <div
        style={{
          width: '40px',
          height: '40px',
          border: '3px solid #2d3f55',
          borderTop: '3px solid #4ade80',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }}
      />
      <span style={{ color: '#64748b', fontSize: '14px' }}>Loading today's games…</span>
    </div>
  );
}

export function Home() {
  const [games, setGames] = useState<GamePrediction[]>([]);
  const [accuracy, setAccuracy] = useState<AccuracyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);

        const [gamesData, accuracyData] = await Promise.all([getGames(), getAccuracy()]);

        if (!cancelled) {
          setGames(gamesData);
          setAccuracy(accuracyData);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          const message =
            err instanceof Error ? err.message : 'Failed to load predictions. Is the backend running?';
          setError(message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main
      style={{
        maxWidth: '1100px',
        margin: '0 auto',
        padding: '32px 20px 64px',
        display: 'flex',
        flexDirection: 'column',
        gap: '32px',
      }}
    >
      {/* Page title */}
      <div>
        <h1 style={{ margin: '0 0 6px', fontSize: '26px', fontWeight: 800, color: '#f1f5f9' }}>
          Today's NBA Predictions
        </h1>
        <p style={{ margin: 0, color: '#64748b', fontSize: '14px' }}>
          {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
        </p>
      </div>

      {/* Accuracy banner */}
      {accuracy && <AccuracyBanner stats={accuracy} />}

      {/* Content area */}
      {loading && <Spinner />}

      {!loading && error && (
        <div
          style={{
            background: 'rgba(248, 113, 113, 0.08)',
            border: '1px solid rgba(248, 113, 113, 0.3)',
            borderRadius: '10px',
            padding: '20px 24px',
            color: '#fca5a5',
            fontSize: '14px',
            lineHeight: 1.6,
          }}
        >
          <strong>Error:</strong> {error}
          <br />
          <span style={{ color: '#94a3b8', fontSize: '13px' }}>
            Make sure the backend is running at{' '}
            <code style={{ background: '#1e293b', padding: '1px 6px', borderRadius: '4px' }}>
              http://localhost:8000
            </code>
          </span>
        </div>
      )}

      {!loading && !error && games.length === 0 && (
        <div
          style={{
            textAlign: 'center',
            padding: '80px 0',
            color: '#475569',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            alignItems: 'center',
          }}
        >
          <span style={{ fontSize: '48px' }}>🏀</span>
          <p style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: '#64748b' }}>
            No games scheduled today
          </p>
          <p style={{ margin: 0, fontSize: '14px' }}>Check back tomorrow for new predictions.</p>
        </div>
      )}

      {!loading && !error && games.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
            gap: '20px',
          }}
        >
          {games.map((game) => (
            <PredictionCard key={game.game_id} prediction={game} />
          ))}
        </div>
      )}
    </main>
  );
}
