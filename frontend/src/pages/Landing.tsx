import { useEffect, useState } from 'react';
import { getGames, getAccuracy } from '../api/predictions';

interface Sport {
  key: string;
  name: string;
  tagline: string;
  status: 'live' | 'coming-soon';
  emoji: string;
  accent: string;
  logoUrl?: string; // optional external SVG; falls back to inline F1Logo or emoji
}

const SPORTS: Sport[] = [
  {
    key: 'nba',
    name: 'NBA',
    tagline: 'Basketball — playoffs in progress',
    status: 'live',
    emoji: '🏀',
    accent: '#f59e0b',
    logoUrl: 'https://upload.wikimedia.org/wikipedia/en/0/03/National_Basketball_Association_logo.svg',
  },
  {
    key: 'f1',
    name: 'F1',
    tagline: 'Formula 1 — race winner predictions',
    status: 'live',
    emoji: '🏎️',
    accent: '#ef4444',
  },
];

// Inline F1 wordmark — stylized italic "F1" in the F1 red. Used when no
// external logo is provided so we don't rely on a CDN that might 404.
function F1Logo({ size = 32 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size * 0.75}
      viewBox="0 0 100 75"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <text
        x="0"
        y="56"
        fontFamily="var(--font-display), sans-serif"
        fontSize="64"
        fontWeight="900"
        fontStyle="italic"
        fill="#e10600"
        letterSpacing="-2"
      >
        F1
      </text>
    </svg>
  );
}

function SportIcon({ sport, size = 32 }: { sport: Sport; size?: number }) {
  const [imgFailed, setImgFailed] = useState(false);

  if (sport.logoUrl && !imgFailed) {
    return (
      <img
        src={sport.logoUrl}
        alt={sport.name}
        style={{ width: size, height: size, objectFit: 'contain', filter: 'brightness(1.05)' }}
        onError={() => setImgFailed(true)}
      />
    );
  }
  if (sport.key === 'f1') return <F1Logo size={size} />;
  return <span style={{ fontSize: size * 0.85 }}>{sport.emoji}</span>;
}

interface Props {
  onSelectSport: (key: string) => void;
}

export function Landing({ onSelectSport }: Props) {
  const [nbaGameCount, setNbaGameCount] = useState<number | null>(null);
  const [nbaLiveCount, setNbaLiveCount] = useState<number>(0);
  const [accuracyPct, setAccuracyPct] = useState<number | null>(null);
  const [totalPredictions, setTotalPredictions] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    // Run independently so a failed accuracy call doesn't blank out game
    // counts (or vice versa). Both endpoints can fail without crashing the page.
    getGames()
      .then((games) => {
        if (cancelled || !Array.isArray(games)) return;
        setNbaGameCount(games.length);
        setNbaLiveCount(games.filter((g) => g?.status === 'live').length);
      })
      .catch(() => {});
    getAccuracy()
      .then((acc) => {
        if (cancelled || !acc) return;
        if (typeof acc.accuracy_percentage === 'number') {
          setAccuracyPct(acc.accuracy_percentage);
        }
        if (typeof acc.total_predictions === 'number') {
          setTotalPredictions(acc.total_predictions);
        }
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  return (
    <main style={{
      maxWidth: '1200px',
      margin: '0 auto',
      padding: '0 24px 80px',
      width: '100%',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Hero */}
      <div style={{
        padding: '80px 0 56px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        alignItems: 'flex-start',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)',
          background: 'var(--primary-dim)',
          border: '1px solid rgba(59,130,246,0.22)',
          borderRadius: '4px',
          padding: '4px 10px',
          fontSize: '10px',
          fontWeight: 600,
          color: 'var(--primary)',
          textTransform: 'uppercase',
          letterSpacing: '0.14em',
        }}>
          AI Sports Prediction
        </span>
        <h1 style={{
          margin: 0,
          fontFamily: 'var(--font-display)',
          fontSize: 'clamp(48px, 7vw, 96px)',
          fontWeight: 800,
          color: 'var(--text-primary)',
          lineHeight: 0.95,
          letterSpacing: '-0.025em',
          textTransform: 'uppercase',
        }}>
          Pick the<br />
          <span style={{ color: 'var(--primary)' }}>winner.</span>{' '}
          <span style={{ color: 'var(--text-secondary)' }}>Show the math.</span>
        </h1>
        <p style={{
          margin: 0,
          maxWidth: '640px',
          fontFamily: 'var(--font-body)',
          color: 'var(--text-secondary)',
          fontSize: '17px',
          lineHeight: 1.55,
        }}>
          Transparent ML predictions for every game, with the model's reasoning and confidence on the table.
          Pick a sport to explore today's matchups.
        </p>
      </div>

      {/* Sport cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '20px',
      }}>
        {SPORTS.map((sport) => (
          <SportCard
            key={sport.key}
            sport={sport}
            nbaStats={sport.key === 'nba' ? {
              gameCount: nbaGameCount,
              liveCount: nbaLiveCount,
              accuracyPct,
              totalPredictions,
            } : null}
            onClick={() => sport.status === 'live' && onSelectSport(sport.key)}
          />
        ))}
      </div>
    </main>
  );
}

function SportCard({
  sport,
  nbaStats,
  onClick,
}: {
  sport: Sport;
  nbaStats: { gameCount: number | null; liveCount: number; accuracyPct: number | null; totalPredictions: number | null } | null;
  onClick: () => void;
}) {
  const isActive = sport.status === 'live';
  return (
    <button
      onClick={onClick}
      disabled={!isActive}
      style={{
        position: 'relative',
        background: 'var(--card)',
        border: '1px solid var(--border)',
        borderRadius: '12px',
        padding: '24px',
        textAlign: 'left',
        cursor: isActive ? 'pointer' : 'not-allowed',
        opacity: isActive ? 1 : 0.55,
        fontFamily: 'inherit',
        color: 'inherit',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        minHeight: '220px',
        transition: 'transform 0.18s ease, border-color 0.18s ease, background 0.18s ease',
      }}
      onMouseEnter={(e) => {
        if (!isActive) return;
        const el = e.currentTarget as HTMLElement;
        el.style.transform = 'translateY(-3px)';
        el.style.borderColor = 'var(--border-bright)';
        el.style.background = 'var(--card-hover)';
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.transform = 'translateY(0)';
        el.style.borderColor = 'var(--border)';
        el.style.background = 'var(--card)';
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{
          width: '52px',
          height: '52px',
          borderRadius: '12px',
          background: `${sport.accent}1a`,
          border: `1px solid ${sport.accent}55`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <SportIcon sport={sport} size={32} />
        </div>
        {isActive ? (
          nbaStats?.liveCount ? (
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              fontWeight: 700,
              color: 'var(--success)',
              background: 'var(--success-dim)',
              border: '1px solid rgba(16,185,129,0.3)',
              borderRadius: '4px',
              padding: '3px 8px',
              letterSpacing: '0.1em',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
            }}>
              <span style={{
                width: '6px', height: '6px', borderRadius: '50%',
                background: 'var(--success)',
                boxShadow: '0 0 6px var(--success)',
                animation: 'pulse-dot 2.5s ease-in-out infinite',
              }} />
              {nbaStats.liveCount} LIVE
            </span>
          ) : (
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              fontWeight: 600,
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
              borderRadius: '4px',
              padding: '3px 8px',
              letterSpacing: '0.1em',
            }}>
              ACTIVE
            </span>
          )
        ) : (
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            fontWeight: 600,
            color: 'var(--text-muted)',
            border: '1px solid var(--border)',
            borderRadius: '4px',
            padding: '3px 8px',
            letterSpacing: '0.1em',
          }}>
            COMING SOON
          </span>
        )}
      </div>

      {/* Title */}
      <div>
        <div style={{
          fontFamily: 'var(--font-display)',
          fontSize: '32px',
          fontWeight: 800,
          color: 'var(--text-primary)',
          letterSpacing: '0.02em',
          textTransform: 'uppercase',
          lineHeight: 1,
        }}>
          {sport.name}
        </div>
        <div style={{
          marginTop: '6px',
          fontFamily: 'var(--font-body)',
          fontSize: '13px',
          color: 'var(--text-secondary)',
        }}>
          {sport.tagline}
        </div>
      </div>

      {/* Stats footer (NBA only) */}
      {isActive && nbaStats && (
        <div style={{
          marginTop: 'auto',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px',
          paddingTop: '16px',
          borderTop: '1px solid var(--border)',
        }}>
          <Stat
            label="Games today"
            value={nbaStats.gameCount === null ? '–' : String(nbaStats.gameCount)}
          />
          <Stat
            label="Accuracy"
            value={
              nbaStats.accuracyPct === null || nbaStats.totalPredictions === 0
                ? '–'
                : `${Math.round(nbaStats.accuracyPct)}%`
            }
            sub={
              nbaStats.totalPredictions
                ? `${nbaStats.totalPredictions} resolved`
                : 'no resolved games'
            }
          />
        </div>
      )}
    </button>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '9px',
        fontWeight: 600,
        color: 'var(--text-muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.12em',
      }}>
        {label}
      </div>
      <div style={{
        fontFamily: 'var(--font-display)',
        fontSize: '22px',
        fontWeight: 700,
        color: 'var(--text-primary)',
        marginTop: '2px',
      }}>
        {value}
      </div>
      {sub && (
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '9px',
          color: 'var(--text-muted)',
          marginTop: '2px',
        }}>
          {sub}
        </div>
      )}
    </div>
  );
}
