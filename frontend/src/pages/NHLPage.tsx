import { useEffect, useState } from 'react';
import type { NHLGamePrediction } from '../types';
import { getNHLGames } from '../api/nhl';
import { NHLGameCard } from '../components/NHLGameCard';

function Spinner() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', gap: '16px', padding: '120px 0',
    }}>
      <div style={{
        width: '40px', height: '40px',
        border: '2px solid var(--border)',
        borderTop: '2px solid #38bdf8',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }} />
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '11px',
        color: 'var(--text-muted)', letterSpacing: '0.1em',
      }}>
        LOADING PREDICTIONS
      </span>
    </div>
  );
}

export function NHLPage() {
  const [games, setGames] = useState<NHLGamePrediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  });

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const data = await getNHLGames();
        if (!cancelled) setGames(data);
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load NHL predictions.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const liveCount = games.filter(g => g.status === 'live').length;

  return (
    <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 24px 96px', flex: 1 }}>

      {/* Hero */}
      <div style={{ position: 'relative', overflow: 'hidden' }}>
        <div className="dot-grid" style={{
          position: 'absolute', inset: 0, opacity: 0.6,
          maskImage: 'linear-gradient(to bottom, transparent 0%, black 20%, black 80%, transparent 100%)',
          WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 20%, black 80%, transparent 100%)',
        }} />

        <div style={{
          position: 'relative',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '48px',
          padding: '56px 0 52px',
          alignItems: 'center',
        }}>
          <div style={{ animation: 'fadeUp 0.5s ease both' }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: '8px',
              background: 'rgba(56,189,248,0.1)',
              border: '1px solid rgba(56,189,248,0.25)',
              borderRadius: '4px', padding: '4px 10px', marginBottom: '20px',
            }}>
              <span style={{
                width: '5px', height: '5px', borderRadius: '50%',
                background: '#38bdf8', boxShadow: '0 0 6px #38bdf8',
                display: 'inline-block',
              }} />
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px',
                fontWeight: 600, color: '#38bdf8', letterSpacing: '0.1em',
              }}>
                NHL · {new Date().getFullYear()}-{String(new Date().getFullYear() + 1).slice(2)} SEASON
              </span>
            </div>

            <h1 style={{
              fontFamily: 'var(--font-display)',
              fontSize: 'clamp(40px, 5vw, 64px)',
              fontWeight: 900, color: 'var(--text-primary)',
              lineHeight: 1.0, letterSpacing: '0.02em',
              textTransform: 'uppercase', marginBottom: '16px',
            }}>
              Game<br />Predictions
            </h1>

            <p style={{
              fontFamily: 'var(--font-body)', fontSize: '14px',
              color: 'var(--text-muted)', letterSpacing: '0.01em',
            }}>
              {today}
            </p>

            {!loading && !error && (
              <div style={{ marginTop: '16px', display: 'flex', gap: '16px', alignItems: 'center' }}>
                {games.length > 0 && (
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: '12px',
                    color: 'var(--text-secondary)', letterSpacing: '0.05em',
                  }}>
                    {games.length} {games.length === 1 ? 'GAME' : 'GAMES'} TODAY
                  </span>
                )}
                {liveCount > 0 && (
                  <span style={{
                    display: 'inline-flex', alignItems: 'center', gap: '5px',
                    fontFamily: 'var(--font-mono)', fontSize: '11px',
                    fontWeight: 700, color: 'var(--success)',
                    letterSpacing: '0.06em',
                  }}>
                    <span style={{
                      width: '6px', height: '6px', borderRadius: '50%',
                      background: 'var(--success)', boxShadow: '0 0 6px var(--success)',
                      animation: 'pulse-dot 2.5s ease-in-out infinite',
                    }} />
                    {liveCount} LIVE
                  </span>
                )}
              </div>
            )}
          </div>

          <div style={{ animation: 'fadeUp 0.5s ease both', animationDelay: '0.1s' }} />
        </div>

        <div style={{ height: '1px', background: 'linear-gradient(to right, transparent, var(--border) 20%, var(--border) 80%, transparent)' }} />
      </div>

      {/* Content */}
      {loading && <Spinner />}

      {!loading && error && (
        <div style={{
          margin: '40px 0',
          background: 'var(--error-dim)',
          border: '1px solid rgba(239,68,68,0.2)',
          borderRadius: '8px', padding: '20px 24px',
          display: 'flex', flexDirection: 'column', gap: '6px',
        }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--error)', letterSpacing: '0.08em', fontWeight: 600 }}>
            NHL DATA ERROR
          </span>
          <span style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-secondary)' }}>
            {error}
          </span>
        </div>
      )}

      {!loading && !error && games.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))',
          gap: '20px',
          paddingTop: '40px',
        }}>
          {games.map((game, i) => (
            <NHLGameCard key={game.game_id} game={game} index={i} />
          ))}
        </div>
      )}

      {!loading && !error && games.length === 0 && (
        <div style={{
          textAlign: 'center', padding: '120px 0',
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px',
        }}>
          <div style={{
            fontFamily: 'var(--font-display)', fontSize: '48px',
            fontWeight: 900, color: 'var(--border)', letterSpacing: '0.04em',
          }}>
            NO GAMES
          </div>
          <p style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-muted)' }}>
            No NHL games scheduled for today. Check back tomorrow.
          </p>
        </div>
      )}

    </main>
  );
}
