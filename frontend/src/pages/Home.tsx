import { useEffect, useState } from 'react';
import type { GamePrediction, AccuracyStats } from '../types';
import { getGames, getAccuracy } from '../api/predictions';
import { PredictionCard } from '../components/PredictionCard';
import { AccuracyBanner } from '../components/AccuracyBanner';

function Spinner() {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '16px',
      padding: '100px 0',
    }}>
      <div style={{
        width: '44px',
        height: '44px',
        border: '3px solid #1e2d40',
        borderTop: '3px solid #00e87a',
        borderRadius: '50%',
        animation: 'spin 0.7s linear infinite',
        boxShadow: '0 0 16px rgba(0,232,122,0.2)',
      }} />
      <span style={{ color: '#4a6075', fontSize: '14px' }}>Loading predictions…</span>
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
          const message = err instanceof Error ? err.message : 'Failed to load predictions. Is the backend running?';
          setError(message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  });

  return (
    <main style={{
      maxWidth: '1180px',
      margin: '0 auto',
      padding: '0 24px 80px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Hero section */}
      <div style={{
        padding: '52px 0 40px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        position: 'relative',
      }}>
        {/* Background radial glow */}
        <div style={{
          position: 'absolute',
          top: '0',
          left: '-100px',
          width: '500px',
          height: '300px',
          background: 'radial-gradient(ellipse, rgba(0,232,122,0.06) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', position: 'relative' }}>
          <div style={{
            background: 'rgba(0,232,122,0.1)',
            border: '1px solid rgba(0,232,122,0.2)',
            borderRadius: '6px',
            padding: '4px 10px',
            fontSize: '11px',
            fontWeight: 700,
            color: '#00e87a',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}>
            <span style={{
              width: '6px', height: '6px',
              background: '#00e87a',
              borderRadius: '50%',
              boxShadow: '0 0 6px #00e87a',
              display: 'inline-block',
            }} />
            NBA · 2025–26 Season
          </div>
        </div>

        <h1 style={{
          margin: 0,
          fontSize: 'clamp(28px, 4vw, 42px)',
          fontWeight: 900,
          color: '#f0f6ff',
          lineHeight: 1.1,
          letterSpacing: '-0.03em',
          position: 'relative',
        }}>
          Today's Game Predictions
        </h1>
        <p style={{
          margin: 0,
          color: '#4a6075',
          fontSize: '15px',
          position: 'relative',
        }}>
          {today} · AI-powered, fully transparent
        </p>
      </div>

      {/* Accuracy banner */}
      {accuracy && (
        <div style={{ marginBottom: '40px' }}>
          <AccuracyBanner stats={accuracy} />
        </div>
      )}

      {/* Content */}
      {loading && <Spinner />}

      {!loading && error && (
        <div style={{
          background: 'rgba(248,113,113,0.06)',
          border: '1px solid rgba(248,113,113,0.2)',
          borderRadius: '12px',
          padding: '20px 24px',
          color: '#fca5a5',
          fontSize: '14px',
          lineHeight: 1.6,
        }}>
          <strong>Error:</strong> {error}
          <br />
          <span style={{ color: '#4a6075', fontSize: '13px' }}>
            Make sure the backend is running at{' '}
            <code>http://localhost:8000</code>
          </span>
        </div>
      )}

      {!loading && !error && games.length === 0 && (
        <div style={{
          textAlign: 'center',
          padding: '100px 0',
          color: '#2d4060',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
          alignItems: 'center',
        }}>
          <span style={{ fontSize: '52px', filter: 'grayscale(0.3)' }}>🏀</span>
          <p style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: '#4a6075' }}>
            No games scheduled today
          </p>
          <p style={{ margin: 0, fontSize: '14px', color: '#2d4060' }}>
            Check back tomorrow for new predictions.
          </p>
        </div>
      )}

      {!loading && !error && games.length > 0 && (
        <>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '20px',
          }}>
            <span style={{ color: '#4a6075', fontSize: '13px', fontWeight: 600 }}>
              {games.length} {games.length === 1 ? 'game' : 'games'} today
            </span>
          </div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
            gap: '20px',
          }}>
            {games.map((game, i) => (
              <div key={game.game_id} style={{ animationDelay: `${i * 80}ms` }}>
                <PredictionCard prediction={game} />
              </div>
            ))}
          </div>
        </>
      )}
    </main>
  );
}
