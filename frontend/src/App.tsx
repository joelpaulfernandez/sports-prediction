import { Home } from './pages/Home';
import './App.css';

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

function Header() {
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
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <HexLogo />
          <span style={{
            fontFamily: 'var(--font-display)',
            fontSize: '22px',
            fontWeight: 800,
            letterSpacing: '0.06em',
            color: 'var(--text-primary)',
            textTransform: 'uppercase',
          }}>
            Stat<span style={{ color: 'var(--primary)' }}>Cast</span>
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '9px',
            fontWeight: 600,
            color: 'var(--primary)',
            background: 'var(--primary-dim)',
            border: '1px solid rgba(59,130,246,0.22)',
            borderRadius: '3px',
            padding: '2px 6px',
            letterSpacing: '0.12em',
          }}>
            BETA
          </span>
        </div>

        {/* Center nav */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
          {([
            { label: 'Predictions', href: '/' },
            { label: 'Accuracy', href: '#accuracy' },
          ] as const).map(({ label, href }) => (
            <a
              key={label}
              href={href}
              style={{
                fontFamily: 'var(--font-body)',
                fontSize: '13px',
                fontWeight: 500,
                color: 'var(--text-secondary)',
                padding: '6px 14px',
                borderRadius: '6px',
                transition: 'color 0.15s, background 0.15s',
                letterSpacing: '0.01em',
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.color = 'var(--text-primary)';
                (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.05)';
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)';
                (e.currentTarget as HTMLElement).style.background = 'transparent';
              }}
            >
              {label}
            </a>
          ))}
        </nav>

        {/* Right: live indicator */}
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <span style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: 'var(--text-muted)',
            letterSpacing: '0.08em',
          }}>
            <span style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: 'var(--success)',
              boxShadow: '0 0 8px var(--success)',
              animation: 'pulse-dot 2.5s ease-in-out infinite',
              display: 'inline-block',
              flexShrink: 0,
            }} />
            NBA · LIVE DATA
          </span>
        </div>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
      <Header />
      <Home />
    </div>
  );
}
