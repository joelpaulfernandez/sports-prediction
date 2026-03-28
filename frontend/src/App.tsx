import { Home } from './pages/Home';

function Header() {
  return (
    <header
      style={{
        background: '#0a1628',
        borderBottom: '1px solid #1e2d40',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}
    >
      <div
        style={{
          maxWidth: '1100px',
          margin: '0 auto',
          padding: '0 20px',
          height: '60px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '30px',
              height: '30px',
              background: 'linear-gradient(135deg, #4ade80, #16a34a)',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '16px',
              fontWeight: 800,
              color: '#0a1628',
            }}
          >
            S
          </div>
          <span
            style={{
              fontSize: '20px',
              fontWeight: 800,
              color: '#f1f5f9',
              letterSpacing: '-0.02em',
            }}
          >
            Stat<span style={{ color: '#4ade80' }}>Cast</span>
          </span>
        </div>

        {/* Nav */}
        <nav style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <a
            href="/"
            style={{
              color: '#94a3b8',
              textDecoration: 'none',
              fontSize: '14px',
              fontWeight: 500,
              padding: '6px 12px',
              borderRadius: '6px',
            }}
          >
            Predictions
          </a>
          <a
            href="#accuracy"
            style={{
              color: '#94a3b8',
              textDecoration: 'none',
              fontSize: '14px',
              fontWeight: 500,
              padding: '6px 12px',
              borderRadius: '6px',
            }}
          >
            Accuracy
          </a>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              color: '#4ade80',
              textDecoration: 'none',
              fontSize: '13px',
              fontWeight: 600,
              padding: '6px 14px',
              border: '1px solid rgba(74,222,128,0.4)',
              borderRadius: '6px',
            }}
          >
            GitHub
          </a>
        </nav>
      </div>
    </header>
  );
}

function App() {
  return (
    <div style={{ minHeight: '100vh', background: '#0d1b2a' }}>
      <Header />
      <Home />
    </div>
  );
}

export default App;
