import { Home } from './pages/Home';

function Header() {
  return (
    <header style={{
      background: 'rgba(8, 15, 26, 0.85)',
      backdropFilter: 'blur(16px)',
      borderBottom: '1px solid #1e2d40',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      <div style={{
        maxWidth: '1180px',
        margin: '0 auto',
        padding: '0 24px',
        height: '64px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '34px',
            height: '34px',
            background: 'linear-gradient(135deg, #00e87a, #00a854)',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '18px',
            boxShadow: '0 0 16px rgba(0,232,122,0.35)',
          }}>
            🏀
          </div>
          <span style={{ fontSize: '20px', fontWeight: 900, color: '#f0f6ff', letterSpacing: '-0.03em' }}>
            Stat<span style={{ color: '#00e87a' }}>Cast</span>
          </span>
          <span style={{
            fontSize: '10px',
            fontWeight: 700,
            color: '#00e87a',
            background: 'rgba(0,232,122,0.12)',
            border: '1px solid rgba(0,232,122,0.25)',
            borderRadius: '4px',
            padding: '2px 7px',
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            marginLeft: '4px',
          }}>
            BETA
          </span>
        </div>

        {/* Nav */}
        <nav style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          <a href="/" style={{
            color: '#8ca3be',
            fontSize: '14px',
            fontWeight: 500,
            padding: '7px 14px',
            borderRadius: '8px',
            transition: 'color 0.15s',
          }}>
            Predictions
          </a>
          <a href="#accuracy" style={{
            color: '#8ca3be',
            fontSize: '14px',
            fontWeight: 500,
            padding: '7px 14px',
            borderRadius: '8px',
          }}>
            Accuracy
          </a>
          <div style={{
            width: '1px',
            height: '20px',
            background: '#1e2d40',
            margin: '0 8px',
          }} />
          <a
            href="https://api-sports.io"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              color: '#f0f6ff',
              fontSize: '13px',
              fontWeight: 600,
              padding: '7px 16px',
              background: 'linear-gradient(135deg, #00e87a18, #00e87a0a)',
              border: '1px solid rgba(0,232,122,0.35)',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span style={{ color: '#00e87a' }}>●</span> Live Data
          </a>
        </nav>
      </div>
    </header>
  );
}

function App() {
  return (
    <div style={{ minHeight: '100vh', background: '#080f1a' }}>
      <Header />
      <Home />
    </div>
  );
}

export default App;
