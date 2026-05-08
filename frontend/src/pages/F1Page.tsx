import { useEffect, useState } from 'react';
import type { F1RaceSummary, F1RacePrediction, F1RecentResult } from '../types';
import { getF1Races, getF1RacePrediction, getF1RecentResults } from '../api/f1';
import { F1RaceCard } from '../components/F1RaceCard';
import { F1RecentResults } from '../components/F1RecentResults';

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
        borderTop: '2px solid var(--error)',
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

export function F1Page() {
  const [races, setRaces] = useState<F1RaceSummary[]>([]);
  const [predictions, setPredictions] = useState<Map<string, F1RacePrediction>>(new Map());
  const [recentResults, setRecentResults] = useState<F1RecentResult[]>([]);
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
        const allRaces = await getF1Races();
        if (cancelled) return;
        const upcoming = allRaces.slice(0, 3);
        setRaces(upcoming);

        const [predResults, recentRes] = await Promise.allSettled([
          Promise.allSettled(
            upcoming.map(async race => {
              try {
                const pred = await getF1RacePrediction(race.race_id);
                return { id: race.race_id, pred };
              } catch { return null; }
            })
          ),
          getF1RecentResults(5),
        ]);

        if (cancelled) return;

        const predMap = new Map<string, F1RacePrediction>();
        if (predResults.status === 'fulfilled') {
          for (const r of predResults.value) {
            if (r.status === 'fulfilled' && r.value) {
              predMap.set(r.value.id, r.value.pred);
            }
          }
        }
        setPredictions(predMap);

        if (recentRes.status === 'fulfilled') {
          setRecentResults(recentRes.value);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load F1 predictions.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  return (
    <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 24px 96px', flex: 1 }}>

      {/* ── Hero ── */}
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
              background: 'rgba(239,68,68,0.1)',
              border: '1px solid rgba(239,68,68,0.2)',
              borderRadius: '4px', padding: '4px 10px', marginBottom: '20px',
            }}>
              <span style={{
                width: '5px', height: '5px', borderRadius: '50%',
                background: 'var(--error)', boxShadow: '0 0 6px var(--error)',
                display: 'inline-block',
              }} />
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px',
                fontWeight: 600, color: 'var(--error)', letterSpacing: '0.1em',
              }}>
                F1 · 2026 SEASON
              </span>
            </div>

            <h1 style={{
              fontFamily: 'var(--font-display)',
              fontSize: 'clamp(40px, 5vw, 64px)',
              fontWeight: 900, color: 'var(--text-primary)',
              lineHeight: 1.0, letterSpacing: '0.02em',
              textTransform: 'uppercase', marginBottom: '16px',
            }}>
              Race<br />Predictions
            </h1>

            <p style={{
              fontFamily: 'var(--font-body)', fontSize: '14px',
              color: 'var(--text-muted)', letterSpacing: '0.01em',
            }}>
              {today}
            </p>

            {!loading && !error && races.length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '12px',
                  color: 'var(--text-secondary)', letterSpacing: '0.05em',
                }}>
                  {races.length} UPCOMING {races.length === 1 ? 'RACE' : 'RACES'}
                </span>
              </div>
            )}
          </div>

          <div style={{ animation: 'fadeUp 0.5s ease both', animationDelay: '0.1s' }} />
        </div>

        <div style={{ height: '1px', background: 'linear-gradient(to right, transparent, var(--border) 20%, var(--border) 80%, transparent)' }} />
      </div>

      {/* ── Content ── */}
      {loading && <Spinner />}

      {!loading && error && (
        <div style={{
          margin: '40px 0',
          background: 'var(--error-dim)',
          border: '1px solid rgba(239,68,68,0.2)',
          borderRadius: '8px',
          padding: '20px 24px',
          display: 'flex', flexDirection: 'column', gap: '6px',
        }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--error)', letterSpacing: '0.08em', fontWeight: 600 }}>F1 DATA ERROR</span>
          <span style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-secondary)' }}>{error}</span>
        </div>
      )}

      {!loading && !error && predictions.size > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))',
          gap: '20px',
          paddingTop: '40px',
        }}>
          {Array.from(predictions.values()).map((pred, i) => (
            <F1RaceCard key={pred.race_id} prediction={pred} index={i} />
          ))}
        </div>
      )}

      {!loading && !error && races.length > 0 && predictions.size === 0 && (
        <div style={{ textAlign: 'center', padding: '120px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '48px', fontWeight: 900, color: 'var(--border)', letterSpacing: '0.04em' }}>PRE-QUALI</div>
          <p style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-muted)' }}>
            Race predictions unlock after qualifying. Check back Saturday.
          </p>
        </div>
      )}

      {!loading && !error && races.length === 0 && (
        <div style={{ textAlign: 'center', padding: '120px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '48px', fontWeight: 900, color: 'var(--border)', letterSpacing: '0.04em' }}>OFF SEASON</div>
          <p style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-muted)' }}>
            No upcoming races scheduled.
          </p>
        </div>
      )}

      {!loading && recentResults.length > 0 && (
        <div style={{ marginTop: '56px' }}>
          <div style={{
            height: '1px',
            background: 'linear-gradient(to right, transparent, var(--border) 20%, var(--border) 80%, transparent)',
            marginBottom: '40px',
          }} />
          <F1RecentResults results={recentResults} />
        </div>
      )}

    </main>
  );
}
