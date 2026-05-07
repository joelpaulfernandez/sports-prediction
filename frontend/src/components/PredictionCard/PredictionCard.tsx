import type { GamePrediction, TeamStats } from '../../types';

interface Props {
  prediction: GamePrediction;
  index?: number;
}

// ── Confidence ring ──────────────────────────────────────────────────────────

function ConfidenceRing({ value, delay = 0 }: { value: number; delay?: number }) {
  const r = 44;
  const circumference = 2 * Math.PI * r; // ≈ 276.46
  const offset = circumference * (1 - value);
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? 'var(--primary)' : pct >= 55 ? 'var(--accent)' : 'var(--error)';
  const colorHex = pct >= 70 ? '#3b82f6' : pct >= 55 ? '#f59e0b' : '#ef4444';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
      <div style={{ position: 'relative', width: '104px', height: '104px' }}>
        <svg width="104" height="104" viewBox="0 0 104 104" style={{ transform: 'rotate(-90deg)' }}>
          {/* Track */}
          <circle cx="52" cy="52" r={r} fill="none" stroke="var(--border)" strokeWidth="5" />
          {/* Filled arc */}
          <circle
            cx="52" cy="52" r={r}
            fill="none"
            stroke={color}
            strokeWidth="5"
            strokeLinecap="round"
            className="conf-ring-arc"
            style={{
              '--ring-offset': offset,
              '--ring-delay': `${delay}ms`,
              filter: `drop-shadow(0 0 8px ${colorHex}66)`,
            } as React.CSSProperties}
          />
        </svg>
        {/* Center label */}
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          gap: '1px',
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '20px',
            fontWeight: 700,
            color,
            lineHeight: 1,
            letterSpacing: '-0.02em',
          }}>
            {pct}%
          </span>
        </div>
      </div>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '9px',
        fontWeight: 600,
        color: 'var(--text-muted)',
        letterSpacing: '0.12em',
        textTransform: 'uppercase',
      }}>
        Confidence
      </span>
    </div>
  );
}

// ── Team logo with initials fallback ─────────────────────────────────────────

function TeamLogo({ teamId, name, size = 64 }: { teamId?: number | null; name: string; size?: number }) {
  const initials = name.split(' ').slice(-2).map(w => w[0]).join('').toUpperCase().slice(0, 2);
  const hue = name.split('').reduce((a, c) => a + c.charCodeAt(0), 0) % 360;

  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      {teamId && (
        <img
          src={`https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`}
          alt={name}
          width={size}
          height={size}
          style={{ objectFit: 'contain', display: 'block' }}
          onError={e => {
            (e.currentTarget as HTMLImageElement).style.display = 'none';
            const fb = (e.currentTarget as HTMLImageElement).nextElementSibling as HTMLElement | null;
            if (fb) fb.style.display = 'flex';
          }}
        />
      )}
      <div style={{
        width: size, height: size,
        borderRadius: '50%',
        background: `linear-gradient(135deg, hsl(${hue},40%,20%), hsl(${hue},40%,12%))`,
        border: `2px solid hsl(${hue},35%,28%)`,
        display: teamId ? 'none' : 'flex',
        alignItems: 'center', justifyContent: 'center',
        fontFamily: 'var(--font-display)',
        fontSize: size * 0.28,
        fontWeight: 800,
        color: `hsl(${hue},55%,70%)`,
        letterSpacing: '0.05em',
        position: teamId ? 'absolute' : 'static',
        top: 0, left: 0,
      }}>
        {initials}
      </div>
    </div>
  );
}

// ── Stat comparison table ─────────────────────────────────────────────────────

interface StatRowProps {
  label: string;
  homeVal: string;
  awayVal: string;
  homeWins?: boolean;
}

function StatRow({ label, homeVal, awayVal, homeWins }: StatRowProps) {
  const homeColor = homeWins === true ? 'var(--primary)' : homeWins === false ? 'var(--text-muted)' : 'var(--text-secondary)';
  const awayColor = homeWins === false ? 'var(--primary)' : homeWins === true ? 'var(--text-muted)' : 'var(--text-secondary)';

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 80px 1fr',
      alignItems: 'center',
      padding: '4px 0',
      borderBottom: '1px solid var(--border)',
    }}>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        fontWeight: homeWins === true ? 700 : 400,
        color: homeColor,
        textAlign: 'right',
        letterSpacing: '-0.01em',
      }}>
        {homeVal}
      </span>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '9px',
        fontWeight: 600,
        color: 'var(--text-muted)',
        textAlign: 'center',
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
      }}>
        {label}
      </span>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        fontWeight: homeWins === false ? 700 : 400,
        color: awayColor,
        letterSpacing: '-0.01em',
      }}>
        {awayVal}
      </span>
    </div>
  );
}

function StatsGrid({ home, away }: { home: TeamStats; away: TeamStats }) {
  const fmt = (n: number, d = 1) => n.toFixed(d);
  const pct = (n: number) => `${(n * 100).toFixed(1)}%`;
  const diff = (a: number, b: number, threshold = 0) => Math.abs(a - b) > threshold ? a > b : undefined;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.25)',
      border: '1px solid var(--border)',
      borderRadius: '6px',
      overflow: 'hidden',
      marginTop: '2px',
    }}>
      {/* Header */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 80px 1fr',
        padding: '7px 12px',
        background: 'rgba(255,255,255,0.02)',
        borderBottom: '1px solid var(--border)',
      }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700, color: 'var(--primary)', textAlign: 'right', letterSpacing: '0.1em' }}>HOME</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700, color: 'var(--text-muted)', textAlign: 'center', letterSpacing: '0.1em' }}>STATS</span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700, color: 'var(--accent)', letterSpacing: '0.1em' }}>AWAY</span>
      </div>
      <div style={{ padding: '6px 12px', display: 'flex', flexDirection: 'column', gap: '0' }}>
        <StatRow label="NET RTG" homeVal={home.net_rating >= 0 ? `+${fmt(home.net_rating)}` : fmt(home.net_rating)} awayVal={away.net_rating >= 0 ? `+${fmt(away.net_rating)}` : fmt(away.net_rating)} homeWins={diff(home.net_rating, away.net_rating, 0.3)} />
        <StatRow label="ELO" homeVal={home.elo.toFixed(0)} awayVal={away.elo.toFixed(0)} homeWins={diff(home.elo, away.elo, 10)} />
        <StatRow label="L10 W%" homeVal={pct(home.recent_win_pct)} awayVal={pct(away.recent_win_pct)} homeWins={diff(home.recent_win_pct, away.recent_win_pct, 0.05)} />
        <StatRow label="eFG%" homeVal={pct(home.efg_pct)} awayVal={pct(away.efg_pct)} homeWins={diff(home.efg_pct, away.efg_pct, 0.005)} />
        <StatRow label="TOV%" homeVal={`${fmt(home.tov_pct)}%`} awayVal={`${fmt(away.tov_pct)}%`} homeWins={diff(away.tov_pct, home.tov_pct, 0.3)} />
        <StatRow label="REST" homeVal={`${home.rest_days}d`} awayVal={`${away.rest_days}d`} homeWins={home.rest_days !== away.rest_days ? home.rest_days > away.rest_days : undefined} />
      </div>
    </div>
  );
}

// ── Model badge ───────────────────────────────────────────────────────────────

function ModelBadge({ version }: { version?: string }) {
  const isML = version === 'xgboost-v1';
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

// ── Status badge ──────────────────────────────────────────────────────────────

const STATUS_CFG = {
  live:      { color: 'var(--success)',   bg: 'var(--success-dim)',   dot: true,  label: 'LIVE' },
  finished:  { color: 'var(--text-muted)', bg: 'rgba(255,255,255,0.04)', dot: false, label: 'FINAL' },
  scheduled: { color: 'var(--primary)',   bg: 'var(--primary-dim)',   dot: false, label: null },
};

function formatTime(utc: string | null | undefined, status: string) {
  if (status === 'live') return 'LIVE';
  if (status === 'finished') return 'Final';
  if (!utc) return 'Today';
  try { return new Date(utc).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }); }
  catch { return 'Today'; }
}

// ── Main card ─────────────────────────────────────────────────────────────────

export function PredictionCard({ prediction, index = 0 }: Props) {
  const {
    home_team, away_team, home_team_id, away_team_id,
    predicted_winner, confidence,
    predicted_home_score, predicted_away_score,
    reasons, game_date, status,
    home_pts, away_pts, game_time_utc,
    home_stats, away_stats, model_version,
  } = prediction;

  const cfg = STATUS_CFG[status as keyof typeof STATUS_CFG] ?? STATUS_CFG.scheduled;
  const hasScore = (status === 'live' || status === 'finished') && home_pts != null && away_pts != null;
  const homeWinsPredicted = predicted_winner === home_team;
  const awayWinsPredicted = predicted_winner === away_team;

  const dateLabel = (() => {
    const src = game_time_utc ? new Date(game_time_utc) : new Date(game_date + 'T12:00:00');
    return src.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  })();

  const timeLabel = formatTime(game_time_utc, status);

  const confidencePct = Math.round(confidence * 100);
  const confColor = confidencePct >= 70 ? 'var(--primary)' : confidencePct >= 55 ? 'var(--accent)' : 'var(--error)';

  // Glow border for winning side
  const winnerGlow = homeWinsPredicted
    ? 'inset 3px 0 0 0 var(--primary)'
    : 'inset -3px 0 0 0 var(--primary)';

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
      {/* Top accent line */}
      <div style={{ height: '2px', background: `linear-gradient(90deg, transparent, ${confColor}, transparent)` }} />

      <div style={{ padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

        {/* ── Header row ── */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: 'var(--text-muted)',
            letterSpacing: '0.06em',
          }}>
            {dateLabel.toUpperCase()}
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ModelBadge version={model_version} />
            <span style={{
              display: 'flex', alignItems: 'center', gap: '5px',
              background: cfg.bg,
              color: cfg.color,
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              padding: '3px 9px',
              borderRadius: '3px',
            }}>
              {cfg.dot && (
                <span style={{
                  width: '5px', height: '5px', borderRadius: '50%',
                  background: cfg.color, animation: 'pulse-dot 1.5s ease-in-out infinite',
                  display: 'inline-block', flexShrink: 0,
                }} />
              )}
              {cfg.label ?? timeLabel}
              {status === 'scheduled' && timeLabel !== 'Today' && ` · ${timeLabel}`}
            </span>
          </div>
        </div>

        {/* ── Teams scoreboard ── */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto 1fr',
          gap: '8px',
          alignItems: 'center',
          boxShadow: winnerGlow,
          borderRadius: '8px',
          background: 'rgba(0,0,0,0.2)',
          padding: '16px 12px',
          border: '1px solid var(--border)',
        }}>
          {/* Away */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
            <TeamLogo teamId={away_team_id} name={away_team} size={56} />
            <span style={{
              fontFamily: 'var(--font-body)',
              fontSize: '11px',
              fontWeight: awayWinsPredicted ? 700 : 400,
              color: awayWinsPredicted ? 'var(--text-primary)' : 'var(--text-secondary)',
              textAlign: 'center',
              lineHeight: 1.3,
            }}>
              {away_team}
            </span>
            {hasScore ? (
              <>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '32px',
                  fontWeight: 700,
                  color: away_pts! > home_pts! ? 'var(--success)' : 'var(--text-muted)',
                  letterSpacing: '-0.03em',
                  lineHeight: 1,
                }}>
                  {away_pts}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.04em' }}>
                  pred. {predicted_away_score}
                </span>
              </>
            ) : (
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '32px',
                fontWeight: 700,
                color: awayWinsPredicted ? confColor : 'var(--text-muted)',
                letterSpacing: '-0.03em',
                lineHeight: 1,
              }}>
                {predicted_away_score}
              </span>
            )}
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '8px', color: 'var(--text-muted)', letterSpacing: '0.12em', fontWeight: 600 }}>AWAY</span>
          </div>

          {/* Center divider */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', padding: '0 4px' }}>
            <div style={{ width: '1px', height: '16px', background: 'var(--border)' }} />
            <span style={{
              fontFamily: 'var(--font-display)',
              fontSize: '13px',
              fontWeight: 700,
              color: 'var(--border-bright)',
              letterSpacing: '0.06em',
            }}>
              {hasScore ? (status === 'live' ? 'LIVE' : 'FIN') : 'VS'}
            </span>
            <div style={{ width: '1px', height: '16px', background: 'var(--border)' }} />
          </div>

          {/* Home */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
            <TeamLogo teamId={home_team_id} name={home_team} size={56} />
            <span style={{
              fontFamily: 'var(--font-body)',
              fontSize: '11px',
              fontWeight: homeWinsPredicted ? 700 : 400,
              color: homeWinsPredicted ? 'var(--text-primary)' : 'var(--text-secondary)',
              textAlign: 'center',
              lineHeight: 1.3,
            }}>
              {home_team}
            </span>
            {hasScore ? (
              <>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '32px',
                  fontWeight: 700,
                  color: home_pts! > away_pts! ? 'var(--success)' : 'var(--text-muted)',
                  letterSpacing: '-0.03em',
                  lineHeight: 1,
                }}>
                  {home_pts}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.04em' }}>
                  pred. {predicted_home_score}
                </span>
              </>
            ) : (
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '32px',
                fontWeight: 700,
                color: homeWinsPredicted ? confColor : 'var(--text-muted)',
                letterSpacing: '-0.03em',
                lineHeight: 1,
              }}>
                {predicted_home_score}
              </span>
            )}
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '8px', color: 'var(--text-muted)', letterSpacing: '0.12em', fontWeight: 600 }}>HOME</span>
          </div>
        </div>

        {/* ── Confidence ring + Winner ── */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'auto 1fr',
          gap: '20px',
          alignItems: 'center',
          padding: '12px 16px',
          background: 'rgba(0,0,0,0.2)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
        }}>
          <ConfidenceRing value={confidence} delay={index * 80 + 300} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '9px',
              fontWeight: 600,
              color: 'var(--text-muted)',
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
            }}>
              Predicted Winner
            </span>
            <span style={{
              fontFamily: 'var(--font-display)',
              fontSize: '22px',
              fontWeight: 800,
              color: 'var(--text-primary)',
              letterSpacing: '0.04em',
              lineHeight: 1.1,
              textTransform: 'uppercase',
            }}>
              {predicted_winner}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
              <div style={{
                height: '3px',
                flex: 1,
                background: 'var(--border)',
                borderRadius: '2px',
                overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%',
                  width: `${confidencePct}%`,
                  background: confColor,
                  borderRadius: '2px',
                  transition: 'width 1s cubic-bezier(0.4,0,0.2,1)',
                }} />
              </div>
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '10px',
                color: confColor,
                fontWeight: 700,
                flexShrink: 0,
              }}>
                {confidencePct}%
              </span>
            </div>
          </div>
        </div>

        {/* ── Stats grid ── */}
        {home_stats && away_stats && (
          <StatsGrid home={home_stats} away={away_stats} />
        )}

        {/* ── Divider ── */}
        <div style={{ height: '1px', background: 'var(--border)' }} />

        {/* ── Reasons ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '9px',
            fontWeight: 600,
            color: 'var(--text-muted)',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
          }}>
            Analysis
          </span>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '7px' }}>
            {reasons.map((r, i) => (
              <li key={i} style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
                fontFamily: 'var(--font-body)',
                fontSize: '12px',
                color: 'var(--text-secondary)',
                lineHeight: 1.55,
              }}>
                <span style={{
                  flexShrink: 0,
                  fontFamily: 'var(--font-mono)',
                  fontSize: '9px',
                  fontWeight: 700,
                  color: 'var(--primary)',
                  background: 'var(--primary-dim)',
                  width: '18px',
                  height: '18px',
                  borderRadius: '3px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginTop: '1px',
                }}>
                  {i + 1}
                </span>
                {r.text}
              </li>
            ))}
          </ul>
        </div>

      </div>
    </div>
  );
}
