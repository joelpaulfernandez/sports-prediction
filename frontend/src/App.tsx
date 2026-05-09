import { useState } from 'react';
import { Home } from './pages/Home';
import { Bracket } from './pages/Bracket';
import { Landing } from './pages/Landing';
import { F1Page } from './pages/F1Page';
import './App.css';

type View = 'landing' | 'nba-predictions' | 'nba-bracket' | 'f1';

function HexLogo() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <polygon
        points="14,2 24,7.5 24,20.5 14,26 4,20.5 4,7.5"
        stroke="#3b82f6"
        strokeWidth="1.5"
        fill="rgba(59,130,246,0.1)"
      />
      <polygon points="14,8 19,11 19,17 14,20 9,17 9,11" fill="#3b82f6" fillOpacity="0.55" />
    </svg>
  );
}

type NavTarget = 'nba-predictions' | 'nba-bracket';

function NavButton({ label, target, view, onChange }: {
  label: string;
  target: NavTarget;
  view: View;
  onChange: (v: View) => void;
}) {
  const active = view === target;
  return (
    <button
      onClick={() => onChange(target)}
      style={{
        fontFamily: 'var(--font-body)',
        fontSize: '13px',
        fontWeight: active ? 600 : 500,
        color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
        padding: '6px 14px',
        borderRadius: '6px',
        background: active ? 'var(--primary-dim)' : 'transparent',
        border: active ? '1px solid rgba(59,130,246,0.22)' : '1px solid transparent',
        cursor: 'pointer',
        transition: 'color 0.15s, background 0.15s, border-color 0.15s',
        letterSpacing: '0.01em',
      }}
      onMouseEnter={(e) => {
        if (!active) {
          (e.currentTarget as HTMLElement).style.color = 'var(--text-primary)';
          (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.05)';
        }
      }}
      onMouseLeave={(e) => {
        if (!active) {
          (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)';
          (e.currentTarget as HTMLElement).style.background = 'transparent';
        }
      }}
    >
      {label}
    </button>
  );
}

function Header({ view, onChange }: { view: View; onChange: (v: View) => void }) {
  const isNba = view === 'nba-predictions' || view === 'nba-bracket';
  const isF1 = view === 'f1';

  const liveColor = isF1 ? 'var(--error)' : 'var(--success)';
  const liveLabel = isF1 ? 'F1 · LIVE DATA' : 'NBA · LIVE DATA';

  return (
    <header style={{
      position: 'sticky',
      top: 0,
      zIndex: 100,
      background: 'rgba(10, 10, 15, 0.90)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      boxShadow: '0 1px 0 rgba(59,130,246,0.10), 0 4px 24px rgba(0,0,0,0.5)',
    }}>
      <div style={{
        maxWidth: '1200px',
        margin: '0 auto',
        padding: '0 24px',
        height: '60px',
        display: 'grid',
        gridTemplateColumns: '1fr auto 1fr',
        alignItems: 'center',
        gap: '24px',
      }}>
        {/* Left: logo + breadcrumb */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <button
            onClick={() => onChange('landing')}
            style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              background: 'transparent', border: 'none', cursor: 'pointer',
              padding: 0, fontFamily: 'inherit', color: 'inherit',
            }}
          >
            <HexLogo />
            <span style={{
              fontFamily: 'var(--font-display)', fontSize: '22px', fontWeight: 800,
              letterSpacing: '0.06em', color: 'var(--text-primary)', textTransform: 'uppercase',
            }}>
              Stat<span style={{ color: 'var(--primary)' }}>Cast</span>
            </span>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
              color: 'var(--primary)', background: 'var(--primary-dim)',
              border: '1px solid rgba(59,130,246,0.22)', borderRadius: '3px',
              padding: '2px 6px', letterSpacing: '0.12em',
            }}>
              BETA
            </span>
          </button>
          {(isNba || isF1) && (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
              <span style={{ color: 'var(--text-secondary)' }}>/</span>
              {' '}
              <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
                {isF1 ? 'F1' : 'NBA'}
              </span>
            </span>
          )}
        </div>

        {/* Center: NBA nav only */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
          {isNba && (
            <>
              <NavButton label="Predictions" target="nba-predictions" view={view} onChange={onChange} />
              <NavButton label="Bracket" target="nba-bracket" view={view} onChange={onChange} />
            </>
          )}
        </nav>

        {/* Right: live indicator */}
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          {view === 'landing' ? (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
              AI · LIVE DATA
            </span>
          ) : (
            <span style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              fontFamily: 'var(--font-mono)', fontSize: '10px',
              color: 'var(--text-muted)', letterSpacing: '0.08em',
            }}>
              <span style={{
                width: '6px', height: '6px', borderRadius: '50%',
                background: liveColor, boxShadow: `0 0 8px ${liveColor}`,
                animation: 'pulse-dot 2.5s ease-in-out infinite',
                display: 'inline-block', flexShrink: 0,
              }} />
              {liveLabel}
            </span>
          )}
        </div>
      </div>
    </header>
  );
}

export default function App() {
  const [view, setView] = useState<View>('landing');

  const handleSportSelect = (sportKey: string) => {
    if (sportKey === 'nba') setView('nba-predictions');
    else if (sportKey === 'f1') setView('f1');
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Header view={view} onChange={setView} />
      {view === 'landing' && <Landing onSelectSport={handleSportSelect} />}
      {view === 'nba-predictions' && <Home />}
      {view === 'nba-bracket' && <Bracket />}
      {view === 'f1' && <F1Page />}
    </div>
  );
}
