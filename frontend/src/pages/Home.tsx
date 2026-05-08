import { useEffect, useState } from 'react';
import type { GamePrediction, AccuracyStats, F1RaceSummary, F1RacePrediction } from '../types';
import { getGames, getAccuracy } from '../api/predictions';
import { getF1Races, getF1RacePrediction, getF1RecentResults } from '../api/f1';
import { PredictionCard } from '../components/PredictionCard';
import { AccuracyBanner } from '../components/AccuracyBanner';
import { F1RaceCard } from '../components/F1RaceCard';
import { F1RecentResults } from '../components/F1RecentResults';

type Tab = 'nba' | 'f1';

function Spinner({ color = 'var(--primary)' }: { color?: string }) {
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
        borderTop: `2px solid ${color}`,
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

// ── Tab bar ───────────────────────────────────────────────────────────────────

interface TabBarProps {
  active: Tab;
  onChange: (t: Tab) => void;
  hasLiveNba: boolean;
}

function TabBar({ active, onChange, hasLiveNba }: TabBarProps) {
  const tabs: { id: Tab; label: string; accent: string; dot?: boolean }[] = [
    { id: 'nba', label: 'NBA', accent: 'var(--primary)', dot: hasLiveNba },
    { id: 'f1',  label: 'F1',  accent: 'var(--error)' },
  ];

  return (
    <div style={{
      display: 'flex',
      gap: '4px',
      padding: '4px',
      background: 'rgba(0,0,0,0.3)',
      border: '1px solid var(--border)',
      borderRadius: '8px',
      width: 'fit-content',
    }}>
      {tabs.map(tab => {
        const isActive = active === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '7px',
              padding: '8px 20px',
              borderRadius: '5px',
              border: 'none',
              cursor: 'pointer',
              background: isActive ? 'rgba(255,255,255,0.07)' : 'transparent',
              boxShadow: isActive ? `inset 0 0 0 1px ${tab.accent}33` : 'none',
              transition: 'background 0.15s, box-shadow 0.15s',
            }}
          >
            {tab.dot && (
              <span style={{
                width: '5px', height: '5px', borderRadius: '50%',
                background: 'var(--success)',
                boxShadow: '0 0 5px var(--success)',
                display: 'inline-block',
                animation: 'pulse-dot 1.5s ease-in-out infinite',
                flexShrink: 0,
              }} />
            )}
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '0.1em',
              color: isActive ? tab.accent : 'var(--text-muted)',
              transition: 'color 0.15s',
            }}>
              {tab.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}

// ── Home ──────────────────────────────────────────────────────────────────────

interface HomeProps {
  initialTab?: Tab;
  onTabChange?: (tab: Tab) => void;
}

export function Home({ initialTab = 'nba', onTabChange }: HomeProps) {
  const [activeTab, setActiveTab] = useState<Tab>(initialTab);

  const handleTabChange = (tab: Tab) => {
    setActiveTab(tab);
    onTabChange?.(tab);
  };

  // NBA state
  const [games, setGames] = useState<GamePrediction[]>([]);
  const [accuracy, setAccuracy] = useState<AccuracyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  // F1 state
  const [f1Races, setF1Races] = useState<F1RaceSummary[]>([]);
  const [f1Predictions, setF1Predictions] = useState<Map<string, F1RacePrediction>>(new Map());
  const [f1RecentResults, setF1RecentResults] = useState<import('../types').F1RecentResult[]>([]);
  const [f1Loading, setF1Loading] = useState(false);
  const [f1Error, setF1Error] = useState<string | null>(null);

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

  // Load F1 when tab first activated
  useEffect(() => {
    if (activeTab !== 'f1') return;
    if (f1Races.length > 0 || f1Loading) return;

    let cancelled = false;
    async function loadF1() {
      try {
        setF1Loading(true);
        setF1Error(null);
        const races = await getF1Races();
        if (cancelled) return;
        const upcoming = races.slice(0, 3);
        setF1Races(upcoming);

        const [predResults, recentResults] = await Promise.allSettled([
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
        setF1Predictions(predMap);

        if (recentResults.status === 'fulfilled') {
          setF1RecentResults(recentResults.value);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setF1Error(err instanceof Error ? err.message : 'Failed to load F1 predictions.');
        }
      } finally {
        if (!cancelled) setF1Loading(false);
      }
    }
    loadF1();
    return () => { cancelled = true; };
  }, [activeTab]);

  // Auto-refresh NBA every 60s when games are live
  useEffect(() => {
    const hasLive = games.some(g => g.status === 'live');
    if (!hasLive) return;
    const id = setInterval(() => {
      Promise.all([getGames(), getAccuracy()])
        .then(([gamesData, accuracyData]) => {
          setGames(gamesData);
          setAccuracy(accuracyData);
          setLastRefreshed(new Date());
        })
        .catch(() => {});
    }, 60_000);
    return () => clearInterval(id);
  }, [games]);

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  });

  const hasLive = games.some(g => g.status === 'live');

  // Per-tab hero pill config
  const heroConfig = {
    nba: { accent: 'var(--primary)', accentDim: 'var(--primary-dim)', accentRgb: '59,130,246', label: 'NBA · 2025–26 SEASON' },
    f1:  { accent: 'var(--error)',   accentDim: 'rgba(239,68,68,0.08)', accentRgb: '239,68,68', label: `F1 · ${new Date().getFullYear()} SEASON` },
  };
  const hero = heroConfig[activeTab];

  return (
    <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 24px 96px', flex: 1 }}>

      {/* ── Hero ──────────────────────────────────────────────── */}
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
          {/* Left: title */}
          <div style={{ animation: 'fadeUp 0.5s ease both' }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: '8px',
              background: hero.accentDim,
              border: `1px solid rgba(${hero.accentRgb},0.2)`,
              borderRadius: '4px', padding: '4px 10px', marginBottom: '20px',
            }}>
              <span style={{
                width: '5px', height: '5px', borderRadius: '50%',
                background: hero.accent, boxShadow: `0 0 6px ${hero.accent}`,
                display: 'inline-block',
              }} />
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px',
                fontWeight: 600, color: hero.accent, letterSpacing: '0.1em',
              }}>
                {hero.label}
              </span>
            </div>

            <h1 style={{
              fontFamily: 'var(--font-display)',
              fontSize: 'clamp(40px, 5vw, 64px)',
              fontWeight: 900, color: 'var(--text-primary)',
              lineHeight: 1.0, letterSpacing: '0.02em',
              textTransform: 'uppercase', marginBottom: '16px',
            }}>
              {activeTab === 'nba'
                ? (games.length > 0 && games[0].game_date !== new Date().toISOString().slice(0, 10)
                    ? <>Upcoming<br />Predictions</>
                    : <>Today's<br />Predictions</>)
                : <>Race<br />Predictions</>
              }
            </h1>

            <p style={{
              fontFamily: 'var(--font-body)', fontSize: '14px',
              color: 'var(--text-muted)', marginBottom: '24px', letterSpacing: '0.01em',
            }}>
              {today}
            </p>

            {/* Tab bar */}
            <TabBar active={activeTab} onChange={handleTabChange} hasLiveNba={hasLive} />

            {/* NBA live indicator */}
            {activeTab === 'nba' && !loading && !error && games.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '16px' }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '12px',
                  color: 'var(--text-secondary)', letterSpacing: '0.05em',
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

            {/* F1 race count */}
            {activeTab === 'f1' && !f1Loading && f1Races.length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '12px',
                  color: 'var(--text-secondary)', letterSpacing: '0.05em',
                }}>
                  {f1Races.length} UPCOMING {f1Races.length === 1 ? 'RACE' : 'RACES'}
                </span>
              </div>
            )}
          </div>

          {/* Right: accuracy stat (NBA only) */}
          <div style={{ animation: 'fadeUp 0.5s ease both', animationDelay: '0.1s' }}>
            {activeTab === 'nba' && !loading && <HeroAccuracyStat accuracy={accuracy} />}
          </div>
        </div>

        <div style={{ height: '1px', background: 'linear-gradient(to right, transparent, var(--border) 20%, var(--border) 80%, transparent)' }} />
      </div>

      {/* ── NBA tab ───────────────────────────────────────────── */}
      {activeTab === 'nba' && (
        <>
          {!loading && !error && accuracy && (
            <div id="accuracy" style={{ paddingTop: '40px' }}>
              <AccuracyBanner stats={accuracy} />
            </div>
          )}

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
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--error)', letterSpacing: '0.08em', fontWeight: 600 }}>NETWORK ERROR</span>
              <span style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-secondary)' }}>{error}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Check that the backend is running at{' '}
                <code style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '3px', padding: '1px 5px', color: 'var(--primary)' }}>
                  {import.meta.env.VITE_API_URL || 'http://localhost:8000'}
                </code>
              </span>
            </div>
          )}

          {!loading && !error && games.length === 0 && (
            <div style={{ textAlign: 'center', padding: '120px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '64px', fontWeight: 900, color: 'var(--border)', letterSpacing: '0.04em' }}>OFF DAY</div>
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
                <PredictionCard key={game.game_id} prediction={game} index={i} />
              ))}
            </div>
          )}
        </>
      )}

      {/* ── F1 tab ────────────────────────────────────────────── */}
      {activeTab === 'f1' && (
        <>
          {f1Loading && <Spinner color="var(--error)" />}

          {!f1Loading && f1Error && (
            <div style={{
              margin: '40px 0',
              background: 'var(--error-dim)',
              border: '1px solid rgba(239,68,68,0.2)',
              borderRadius: '8px',
              padding: '20px 24px',
              display: 'flex', flexDirection: 'column', gap: '6px',
            }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--error)', letterSpacing: '0.08em', fontWeight: 600 }}>F1 DATA ERROR</span>
              <span style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-secondary)' }}>{f1Error}</span>
            </div>
          )}

          {!f1Loading && !f1Error && f1Predictions.size > 0 && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(420px, 1fr))',
              gap: '20px',
              paddingTop: '40px',
            }}>
              {Array.from(f1Predictions.values()).map((pred, i) => (
                <F1RaceCard key={pred.race_id} prediction={pred} index={i} />
              ))}
            </div>
          )}

          {!f1Loading && !f1Error && f1Races.length > 0 && f1Predictions.size === 0 && (
            <div style={{ textAlign: 'center', padding: '120px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '48px', fontWeight: 900, color: 'var(--border)', letterSpacing: '0.04em' }}>PRE-QUALI</div>
              <p style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-muted)' }}>
                Race predictions unlock after qualifying. Check back Saturday.
              </p>
            </div>
          )}

          {!f1Loading && !f1Error && f1Races.length === 0 && (
            <div style={{ textAlign: 'center', padding: '120px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '48px', fontWeight: 900, color: 'var(--border)', letterSpacing: '0.04em' }}>OFF SEASON</div>
              <p style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-muted)' }}>
                No upcoming races scheduled.
              </p>
            </div>
          )}

          {/* Past races results */}
          {!f1Loading && f1RecentResults.length > 0 && (
            <div style={{ marginTop: '56px' }}>
              <div style={{
                height: '1px',
                background: 'linear-gradient(to right, transparent, var(--border) 20%, var(--border) 80%, transparent)',
                marginBottom: '40px',
              }} />
              <F1RecentResults results={f1RecentResults} />
            </div>
          )}
        </>
      )}

    </main>
  );
}
