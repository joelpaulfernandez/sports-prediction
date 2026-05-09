import type { F1RacePrediction, F1DriverPrediction } from '../../types';

interface Props {
  prediction: F1RacePrediction;
  index?: number;
}

// ── Team color lookup (constructor → hex) ────────────────────────────────────

// Keyed by the canonical constructor name returned by the backend.
// Partial match fallback handles variants like "BWT Alpine F1 Team".
const TEAM_COLORS: Record<string, string> = {
  'Red Bull':     '#3671C6',
  'Ferrari':      '#E8002D',
  'Mercedes':     '#27F4D2',
  'McLaren':      '#FF8000',
  'Aston Martin': '#229971',
  'Alpine':       '#FF87BC',
  'Williams':     '#64C4FF',
  'RB':           '#6692FF',
  'Haas':         '#B6BABD',
  'Kick Sauber':  '#52E252',
};

const _TEAM_KEYS = Object.keys(TEAM_COLORS);

function teamColor(team: string): string {
  if (TEAM_COLORS[team]) return TEAM_COLORS[team];
  const match = _TEAM_KEYS.find(k => team.includes(k));
  if (match) return TEAM_COLORS[match];
  const hue = team.split('').reduce((a, c) => a + c.charCodeAt(0), 0) % 360;
  return `hsl(${hue}, 60%, 55%)`;
}

// ── Confidence ring ───────────────────────────────────────────────────────────

function ConfidenceRing({ value, delay = 0 }: { value: number; delay?: number }) {
  const r = 36;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - value / 100);
  const color = value >= 70 ? 'var(--primary)' : value >= 55 ? 'var(--accent)' : 'var(--error)';
  const colorHex = value >= 70 ? '#3b82f6' : value >= 55 ? '#f59e0b' : '#ef4444';

  return (
    <div style={{ position: 'relative', width: '84px', height: '84px', flexShrink: 0 }}>
      <svg width="84" height="84" viewBox="0 0 84 84" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="42" cy="42" r={r} fill="none" stroke="var(--border)" strokeWidth="4" />
        <circle
          cx="42" cy="42" r={r}
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeLinecap="round"
          className="conf-ring-arc"
          style={{
            '--ring-offset': offset,
            '--ring-delay': `${delay}ms`,
            filter: `drop-shadow(0 0 6px ${colorHex}66)`,
          } as React.CSSProperties}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        gap: '1px',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '16px',
          fontWeight: 700, color, lineHeight: 1, letterSpacing: '-0.02em',
        }}>
          {value}%
        </span>
      </div>
    </div>
  );
}

// ── Circuit variance badge ────────────────────────────────────────────────────

function VarianceBadge({ variance }: { variance: 'high' | 'normal' }) {
  if (variance !== 'high') return null;
  return (
    <span style={{
      fontFamily: 'var(--font-mono)',
      fontSize: '9px',
      fontWeight: 700,
      color: 'var(--accent)',
      background: 'rgba(245,158,11,0.08)',
      border: '1px solid rgba(245,158,11,0.25)',
      borderRadius: '3px',
      padding: '2px 7px',
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
    }}>
      HIGH VARIANCE
    </span>
  );
}

// ── Model confidence badge ────────────────────────────────────────────────────

function ModelBadge({ version }: { version?: string }) {
  const isML = version === 'xgboost-ranker-v1';
  return (
    <span style={{
      fontFamily: 'var(--font-mono)',
      fontSize: '9px',
      fontWeight: 600,
      color: isML ? 'var(--primary)' : 'var(--text-muted)',
      background: isML ? 'var(--primary-dim)' : 'rgba(255,255,255,0.03)',
      border: `1px solid ${isML ? 'rgba(59,130,246,0.2)' : 'var(--border)'}`,
      borderRadius: '3px',
      padding: '2px 6px',
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
    }}>
      {isML ? 'XGBoost' : 'Rule-based'}
    </span>
  );
}

// ── Driver podium row ─────────────────────────────────────────────────────────

function DriverRow({ driver, rank }: { driver: F1DriverPrediction; rank: number }) {
  const color = teamColor(driver.team);
  const podiumColors = ['var(--accent)', '#C0C0C0', '#CD7F32'];
  const posColor = rank <= 3 ? podiumColors[rank - 1] : 'var(--text-muted)';
  const winPct = Math.round(driver.win_prob * 100);
  const podPct = Math.round(driver.podium_prob * 100);

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '28px 8px 1fr auto auto',
      alignItems: 'center',
      gap: '10px',
      padding: '7px 0',
      borderBottom: rank < 10 ? '1px solid var(--border)' : 'none',
    }}>
      {/* Position */}
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: rank === 1 ? '18px' : '13px',
        fontWeight: rank <= 3 ? 800 : 500,
        color: posColor,
        textAlign: 'right',
        lineHeight: 1,
      }}>
        P{driver.position}
      </span>

      {/* Team color strip */}
      <div style={{
        width: '3px', height: rank === 1 ? '32px' : '24px',
        borderRadius: '2px',
        background: color,
        boxShadow: `0 0 6px ${color}66`,
        flexShrink: 0,
      }} />

      {/* Driver info */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1px', minWidth: 0 }}>
        <span style={{
          fontFamily: rank === 1 ? 'var(--font-display)' : 'var(--font-body)',
          fontSize: rank === 1 ? '15px' : '12px',
          fontWeight: rank === 1 ? 800 : rank <= 3 ? 600 : 400,
          color: rank === 1 ? 'var(--text-primary)' : rank <= 3 ? 'var(--text-secondary)' : 'var(--text-muted)',
          letterSpacing: rank === 1 ? '0.04em' : '0',
          textTransform: rank === 1 ? 'uppercase' : 'none',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}>
          {driver.driver}
        </span>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '9px',
          color: 'var(--text-muted)',
          letterSpacing: '0.04em',
        }}>
          {driver.team}
        </span>
      </div>

      {/* Win prob */}
      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: rank === 1 ? '14px' : '11px',
          fontWeight: rank === 1 ? 700 : 400,
          color: rank === 1 ? 'var(--primary)' : 'var(--text-muted)',
        }}>
          {winPct}%
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '8px',
          color: 'var(--text-muted)',
          letterSpacing: '0.06em',
        }}>
          WIN
        </div>
      </div>

      {/* Podium prob */}
      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: rank === 1 ? '14px' : '11px',
          fontWeight: rank === 1 ? 700 : 400,
          color: rank <= 3 ? 'var(--accent)' : 'var(--text-muted)',
        }}>
          {podPct}%
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '8px',
          color: 'var(--text-muted)',
          letterSpacing: '0.06em',
        }}>
          POD
        </div>
      </div>
    </div>
  );
}

// ── Analysis reasons ──────────────────────────────────────────────────────────

function ReasonsList({ reasons }: { reasons: { text: string }[] }) {
  if (!reasons || reasons.length === 0) return null;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '9px', fontWeight: 600,
        color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase',
      }}>
        Analysis
      </span>
      <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '7px' }}>
        {reasons.map((r, i) => (
          <li key={i} style={{
            display: 'flex', alignItems: 'flex-start', gap: '10px',
            fontFamily: 'var(--font-body)', fontSize: '12px',
            color: 'var(--text-secondary)', lineHeight: 1.55,
          }}>
            <span style={{
              flexShrink: 0, fontFamily: 'var(--font-mono)', fontSize: '9px',
              fontWeight: 700, color: 'var(--primary)', background: 'var(--primary-dim)',
              width: '18px', height: '18px', borderRadius: '3px',
              display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: '1px',
            }}>
              {i + 1}
            </span>
            {r.text}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── Main card ─────────────────────────────────────────────────────────────────

export function F1RaceCard({ prediction, index = 0 }: Props) {
  const {
    event, circuit, circuit_country, race_date, race_time_utc,
    predictions, circuit_variance, model_version,
  } = prediction;

  const top = predictions[0];
  const top10 = predictions.slice(0, 10);
  const confColor = top.confidence_score >= 70 ? 'var(--primary)'
    : top.confidence_score >= 55 ? 'var(--accent)' : 'var(--error)';

  const dateLabel = (() => {
    const d = race_time_utc ? new Date(race_time_utc) : new Date(race_date + 'T12:00:00');
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  })();

  const timeLabel = (() => {
    if (!race_time_utc) return 'Race Day';
    try { return new Date(race_time_utc).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }); }
    catch { return 'Race Day'; }
  })();

  return (
    <div
      className="card-animate"
      style={{
        '--card-delay': `${index * 80}ms`,
        background: 'var(--card)',
        border: '1px solid var(--border)',
        borderRadius: '10px',
        overflow: 'hidden',
        boxShadow: '0 2px 16px rgba(0,0,0,0.4)',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease',
      } as React.CSSProperties}
      onMouseEnter={e => {
        const el = e.currentTarget as HTMLDivElement;
        el.style.transform = 'translateY(-3px)';
        el.style.boxShadow = '0 8px 32px rgba(0,0,0,0.6), 0 0 0 1px var(--border-bright)';
        el.style.borderColor = 'var(--border-bright)';
      }}
      onMouseLeave={e => {
        const el = e.currentTarget as HTMLDivElement;
        el.style.transform = 'translateY(0)';
        el.style.boxShadow = '0 2px 16px rgba(0,0,0,0.4)';
        el.style.borderColor = 'var(--border)';
      }}
    >
      {/* Top accent */}
      <div style={{ height: '2px', background: `linear-gradient(90deg, transparent, ${confColor}, transparent)` }} />

      <div style={{ padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

        {/* ── Header ── */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
                color: 'var(--error)', letterSpacing: '0.1em',
              }}>
                F1
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.06em' }}>
                {dateLabel.toUpperCase()} · {timeLabel}
              </span>
            </div>
            <span style={{
              fontFamily: 'var(--font-body)', fontSize: '13px',
              fontWeight: 600, color: 'var(--text-secondary)',
            }}>
              {circuit_country}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <ModelBadge version={model_version} />
            <VarianceBadge variance={circuit_variance} />
          </div>
        </div>

        {/* ── Event title ── */}
        <div style={{
          padding: '12px 14px',
          background: 'rgba(0,0,0,0.2)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
        }}>
          <span style={{
            fontFamily: 'var(--font-display)', fontSize: 'clamp(18px, 2.5vw, 22px)',
            fontWeight: 900, color: 'var(--text-primary)',
            letterSpacing: '0.04em', textTransform: 'uppercase', lineHeight: 1.1,
          }}>
            {event}
          </span>
          <div style={{ marginTop: '4px' }}>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px',
              color: 'var(--text-muted)', letterSpacing: '0.06em',
            }}>
              {circuit}
            </span>
          </div>
        </div>

        {/* ── Predicted winner ── */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'auto 1fr',
          gap: '16px', alignItems: 'center',
          padding: '12px 14px',
          background: 'rgba(0,0,0,0.2)',
          border: '1px solid var(--border)', borderRadius: '8px',
        }}>
          <ConfidenceRing value={top.confidence_score} delay={index * 80 + 300} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
              color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase',
            }}>
              Predicted Winner
            </span>
            <span style={{
              fontFamily: 'var(--font-display)', fontSize: '20px', fontWeight: 900,
              color: 'var(--text-primary)', letterSpacing: '0.04em', textTransform: 'uppercase', lineHeight: 1.1,
            }}>
              {top.driver}
            </span>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '10px',
              color: teamColor(top.team), letterSpacing: '0.04em',
            }}>
              {top.team}
            </span>
            {/* Win prob bar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
              <div style={{ height: '3px', flex: 1, background: 'var(--border)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{
                  height: '100%', width: `${Math.round(top.win_prob * 100)}%`,
                  background: confColor, borderRadius: '2px',
                  transition: 'width 1s cubic-bezier(0.4,0,0.2,1)',
                }} />
              </div>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px',
                color: confColor, fontWeight: 700, flexShrink: 0,
              }}>
                {Math.round(top.win_prob * 100)}% WIN
              </span>
            </div>
          </div>
        </div>

        {/* ── Top 10 grid ── */}
        <div style={{
          background: 'rgba(0,0,0,0.25)',
          border: '1px solid var(--border)', borderRadius: '6px', overflow: 'hidden',
        }}>
          {/* Header */}
          <div style={{
            display: 'grid', gridTemplateColumns: '28px 8px 1fr auto auto',
            gap: '10px', padding: '6px 12px',
            background: 'rgba(255,255,255,0.02)',
            borderBottom: '1px solid var(--border)',
          }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '8px', fontWeight: 700, color: 'var(--text-muted)', textAlign: 'right', letterSpacing: '0.08em' }}>POS</span>
            <span />
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '8px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>DRIVER</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '8px', fontWeight: 700, color: 'var(--text-muted)', textAlign: 'right', letterSpacing: '0.08em' }}>WIN</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '8px', fontWeight: 700, color: 'var(--text-muted)', textAlign: 'right', letterSpacing: '0.08em' }}>POD</span>
          </div>
          <div style={{ padding: '4px 12px 8px' }}>
            {top10.map(d => (
              <DriverRow key={d.driver_id} driver={d} rank={d.position} />
            ))}
          </div>
        </div>

        {/* ── Divider ── */}
        <div style={{ height: '1px', background: 'var(--border)' }} />

        {/* ── Winner analysis ── */}
        {top.reasons && top.reasons.length > 0 && (
          <ReasonsList reasons={top.reasons} />
        )}

      </div>
    </div>
  );
}
