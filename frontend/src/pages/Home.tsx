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
      padding: '120px 0',
    }}>
      <div style={{
        width: '40px',
        height: '40px',
        border: '2px solid var(--border)',
        borderTop: '2px solid var(--primary)',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }} />
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        color: 'var(--text-muted)',
        letterSpacing: '0.1em',
      }}>
        LOADING PREDICTIONS
      </span>
    </div>
  );
}

function HeroAccuracyStat({ accuracy }: { accuracy: AccuracyStats | null }) {
  if (!accuracy || accuracy.total_predictions === 0) {
    return (
      <div style={{ textAlign: 'right' }}>
        <div style={{
          fontFamily: 'var(--font-display)',
          fontSize: '72px',
          fontWeight: 900,
          letterSpacing: '-0.02em',
          color: 'var(--border-bright)',
          lineHeight: 1,
        }}>—</div>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '10px',
          color: 'var(--text-muted)',
          letterSpacing: '0.1em',
          marginTop: '8px',
        }}>NO DATA YET</div>
      </div>
    );
  }

  const pct = accuracy.accuracy_percentage;
  const color = pct >= 65 ? 'var(--success)' : pct >= 50 ? 'var(--accent)' : 'var(--error)';

  return (
    <div style={{ textAlign: 'right', animation: 'fadeIn 0.6s ease both', animationDelay: '0.2s' }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px',
        color: 'var(--text-muted)',
        letterSpacing: '0.12em',
        marginBottom: '8px',
      }}>
        SEASON ACCURACY
      </div>
      <div style={{
        fontFamily: 'var(--font-display)',
        fontSize: '80px',
        fontWeight: 900,
        letterSpacing: '-0.02em',
        color,
        lineHeight: 1,
        textShadow: `0 0 40px ${color}44`,
      }}>
        {pct.toFixed(1)}%
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        color: 'var(--text-secondary)',
        marginTop: '10px',
        letterSpacing: '0.02em',
      }}>
        <span style={{ color: 'var(--success)', fontWeight: 600 }}>{accuracy.correct_predictions}</span>
        {' '}correct of{' '}
        <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{accuracy.total_predictions}</span>
        {' '}predicted
      </div>
    </div>
  );
}

export function Home() {
  const [games, setGames] = useState<GamePrediction[]>([]);
  const [accuracy, setAccuracy] = useState<AccuracyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

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
          setLastRefreshed(new Date());
        }
      } catch (err: unknown) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Failed to load predictions.';
          setError(message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  // Auto-refresh every 60s when any game is live
  useEffect(() => {
    const hasLive = games.some(g => g.status === 'live');
    if (!hasLive) return;
    const id = setInterval(() => {
      getGames().then(data => {
        setGames(data);
        setLastRefreshed(new Date());
      }).catch(() => {});
    }, 60_000);
    return () => clearInterval(id);
  }, [games]);

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  });

  const hasLive = games.some(g => g.status === 'live');

  return (
    <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 24px 96px', flex: 1 }}>

      {/* ── Hero ─────────────────────────────────────────────── */}
      <div style={{ position: 'relative', overflow: 'hidden' }}>
        {/* Dot grid */}
        <div className="dot-grid" style={{
          position: 'absolute',
          inset: 0,
          opacity: 0.6,
          maskImage: 'linear-gradient(to bottom, transparent 0%, black 20%, black 80%, transparent 100%)',
          WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 20%, black 80%, transparent 100%)',
        }} />

        {/* Vertical rule */}
        <div style={{
          position: 'absolute',
          top: 0,
          bottom: 0,
          left: '50%',
          width: '1px',
          background: 'linear-gradient(to bottom, transparent, var(--border) 30%, var(--border) 70%, transparent)',
          display: 'none',
        }} />

        <div style={{
          position: 'relative',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '48px',
          padding: '56px 0 52px',
          alignItems: 'center',
        }}>
          {/* Left: title */}
          <div style={{ animation: 'fadeUp 0.5s ease both' }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              background: 'var(--primary-dim)',
              border: '1px solid rgba(59,130,246,0.2)',
              borderRadius: '4px',
              padding: '4px 10px',
              marginBottom: '20px',
            }}>
              <span style={{
                width: '5px', height: '5px', borderRadius: '50%',
                background: 'var(--primary)', boxShadow: '0 0 6px var(--primary)',
                display: 'inline-block',
              }} />
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '10px',
                fontWeight: 600,
                color: 'var(--primary)',
                letterSpacing: '0.1em',
              }}>
                NBA · 2025–26 SEASON
              </span>
            </div>

            <h1 style={{
              fontFamily: 'var(--font-display)',
              fontSize: 'clamp(40px, 5vw, 64px)',
              fontWeight: 900,
              color: 'var(--text-primary)',
              lineHeight: 1.0,
              letterSpacing: '0.02em',
              textTransform: 'uppercase',
              marginBottom: '16px',
            }}>
              {games.length > 0 && games[0].game_date !== new Date().toISOString().slice(0, 10)
                ? <>Upcoming<br />Predictions</>
                : <>Today's<br />Predictions</>}
            </h1>

            <p style={{
              fontFamily: 'var(--font-body)',
              fontSize: '14px',
              color: 'var(--text-muted)',
              marginBottom: '24px',
              letterSpacing: '0.01em',
            }}>
              {today}
            </p>

            {!loading && !error && games.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
                  letterSpacing: '0.05em',
                }}>
                  {games.length} {games.length === 1 ? 'GAME' : 'GAMES'} TODAY
                </span>
                {hasLive && (
                  <>
                    <span style={{ width: '3px', height: '3px', borderRadius: '50%', background: 'var(--border-bright)', display: 'inline-block' }} />
                    <span style={{
                      display: 'flex', alignItems: 'center', gap: '5px',
                      fontFamily: 'var(--font-mono)', fontSize: '12px',
                      color: 'var(--success)', letterSpacing: '0.08em', fontWeight: 600,
                    }}>
                      <span style={{
                        width: '5px', height: '5px', borderRadius: '50%',
                        background: 'var(--success)', animation: 'pulse-dot 1.5s ease-in-out infinite',
                        display: 'inline-block',
                      }} />
                      LIVE NOW
                    </span>
                    {lastRefreshed && (
                      <>
                        <span style={{ width: '3px', height: '3px', borderRadius: '50%', background: 'var(--border-bright)', display: 'inline-block' }} />
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
                          {lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </>
                    )}
                  </>
                )}
              </div>
            )}
          </div>

          {/* Right: accuracy stat */}
          <div style={{ animation: 'fadeUp 0.5s ease both', animationDelay: '0.1s' }}>
            {!loading && <HeroAccuracyStat accuracy={accuracy} />}
          </div>
        </div>

        {/* Bottom rule */}
        <div style={{ height: '1px', background: 'linear-gradient(to right, transparent, var(--border) 20%, var(--border) 80%, transparent)' }} />
      </div>

      {/* ── Accuracy Banner ───────────────────────────────────── */}
      {!loading && !error && accuracy && (
        <div id="accuracy" style={{ paddingTop: '40px' }}>
          <AccuracyBanner stats={accuracy} />
        </div>
      )}

      {/* ── Content ───────────────────────────────────────────── */}
      {loading && <Spinner />}

      {!loading && error && (
        <div style={{
          margin: '40px 0',
          background: 'var(--error-dim)',
          border: '1px solid rgba(239,68,68,0.2)',
          borderRadius: '8px',
          padding: '20px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            color: 'var(--error)',
            letterSpacing: '0.08em',
            fontWeight: 600,
          }}>NETWORK ERROR</span>
          <span style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-secondary)' }}>
            {error}
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Check that the backend is running at{' '}
            <code style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid var(--border)',
              borderRadius: '3px',
              padding: '1px 5px',
              color: 'var(--primary)',
            }}>
              {import.meta.env.VITE_API_URL || 'http://localhost:8000'}
            </code>
          </span>
        </div>
      )}

      {!loading && !error && games.length === 0 && (
        <div style={{
          textAlign: 'center',
          padding: '120px 0',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '12px',
        }}>
          <div style={{
            fontFamily: 'var(--font-display)',
            fontSize: '64px',
            fontWeight: 900,
            color: 'var(--border)',
            letterSpacing: '0.04em',
          }}>OFF DAY</div>
          <p style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-muted)' }}>
            No games scheduled today. Check back tomorrow.
          </p>
        </div>
      )}

      {!loading && !error && games.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))',
          gap: '20px',
          paddingTop: '40px',
        }}>
          {games.map((game, i) => (
            <PredictionCard
              key={game.game_id}
              prediction={game}
              index={i}
            />
          ))}
        </div>
      )}
    </main>
  );
}
