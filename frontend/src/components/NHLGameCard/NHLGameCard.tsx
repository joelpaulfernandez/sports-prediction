import type { NHLGamePrediction } from '../../types';

interface Props {
  game: NHLGamePrediction;
  index?: number;
}

// ── Predicted goals from team stats ──────────────────────────────────────────

function predictedGoals(
  homeStats: { goals_for_per_game: number; goals_against_per_game: number } | null | undefined,
  awayStats: { goals_for_per_game: number; goals_against_per_game: number } | null | undefined,
  homeWins: boolean,
): [number, number] {
  if (!homeStats || !awayStats) return [3, 2];
  const rawHome = (homeStats.goals_for_per_game + awayStats.goals_against_per_game) / 2;
  const rawAway = (awayStats.goals_for_per_game + homeStats.goals_against_per_game) / 2;
  let h = Math.max(1, Math.round(rawHome));
  let a = Math.max(1, Math.round(rawAway));
  // ensure winner has strictly more goals
  if (homeWins && h <= a) h = a + 1;
  if (!homeWins && a <= h) a = h + 1;
  return [h, a];
}

// ── Confidence ring ───────────────────────────────────────────────────────────

function ConfidenceRing({ value, delay = 0 }: { value: number; delay?: number }) {
  const r = 44;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - value);
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? 'var(--primary)' : pct >= 55 ? 'var(--accent)' : 'var(--error)';
  const colorHex = pct >= 70 ? '#3b82f6' : pct >= 55 ? '#f59e0b' : '#ef4444';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
      <div style={{ position: 'relative', width: '104px', height: '104px' }}>
        <svg width="104" height="104" viewBox="0 0 104 104" style={{ transform: 'rotate(-90deg)' }}>
          <circle cx="52" cy="52" r={r} fill="none" stroke="var(--border)" strokeWidth="5" />
          <circle
            cx="52" cy="52" r={r}
            fill="none" stroke={color} strokeWidth="5" strokeLinecap="round"
            className="conf-ring-arc"
            style={{
              '--ring-offset': offset,
              '--ring-delay': `${delay}ms`,
              filter: `drop-shadow(0 0 8px ${colorHex}66)`,
            } as React.CSSProperties}
          />
        </svg>
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: '1px',
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '20px',
            fontWeight: 700, color, lineHeight: 1, letterSpacing: '-0.02em',
          }}>
            {pct}%
          </span>
        </div>
      </div>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
        color: 'var(--text-muted)', letterSpacing: '0.12em',
        textTransform: 'uppercase', textAlign: 'center',
      }}>
        Confidence
      </span>
    </div>
  );
}

// ── Team logo ─────────────────────────────────────────────────────────────────

function TeamLogo({ abbrev, name, size = 56 }: { abbrev: string; name: string; size?: number }) {
  const initials = abbrev.slice(0, 3).toUpperCase();
  const hue = abbrev.split('').reduce((a, c) => a + c.charCodeAt(0), 0) % 360;

  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <img
        src={`https://assets.nhle.com/logos/nhl/svg/${abbrev}_light.svg`}
        alt={name}
        width={size} height={size}
        style={{ objectFit: 'contain', display: 'block' }}
        onError={e => {
          (e.currentTarget as HTMLImageElement).style.display = 'none';
          const fb = (e.currentTarget as HTMLImageElement).nextElementSibling as HTMLElement | null;
          if (fb) fb.style.display = 'flex';
        }}
      />
      <div style={{
        width: size, height: size, borderRadius: '50%',
        background: `linear-gradient(135deg, hsl(${hue},40%,20%), hsl(${hue},40%,12%))`,
        border: `2px solid hsl(${hue},35%,28%)`,
        display: 'none', alignItems: 'center', justifyContent: 'center',
        fontFamily: 'var(--font-display)', fontSize: size * 0.28, fontWeight: 800,
        color: `hsl(${hue},55%,70%)`, letterSpacing: '0.05em',
        position: 'absolute', top: 0, left: 0,
      }}>
        {initials}
      </div>
    </div>
  );
}

// ── Stat row ──────────────────────────────────────────────────────────────────

function StatRow({ label, homeVal, awayVal, homeWins }: {
  label: string; homeVal: string; awayVal: string; homeWins?: boolean;
}) {
  const homeColor = homeWins === true ? 'var(--primary)' : homeWins === false ? 'var(--text-muted)' : 'var(--text-secondary)';
  const awayColor = homeWins === false ? 'var(--primary)' : homeWins === true ? 'var(--text-muted)' : 'var(--text-secondary)';

  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '1fr 80px 1fr',
      alignItems: 'center', padding: '4px 0', borderBottom: '1px solid var(--border)',
    }}>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '11px',
        fontWeight: homeWins === true ? 700 : 400, color: homeColor,
        textAlign: 'right', letterSpacing: '-0.01em',
      }}>{homeVal}</span>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
        color: 'var(--text-muted)', textAlign: 'center',
        letterSpacing: '0.06em', textTransform: 'uppercase',
      }}>{label}</span>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '11px',
        fontWeight: homeWins === false ? 700 : 400, color: awayColor,
        letterSpacing: '-0.01em',
      }}>{awayVal}</span>
    </div>
  );
}

// ── Model badge ───────────────────────────────────────────────────────────────

function ModelBadge() {
  return (
    <span style={{
      fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
      color: 'var(--text-muted)', background: 'rgba(255,255,255,0.03)',
      border: '1px solid var(--border)', borderRadius: '3px',
      padding: '2px 6px', letterSpacing: '0.08em', textTransform: 'uppercase',
    }}>
      NHL Stats
    </span>
  );
}

// ── Status badge ──────────────────────────────────────────────────────────────

const STATUS_CFG = {
  live:      { color: 'var(--success)',    bg: 'var(--success-dim)',      dot: true,  label: 'LIVE' },
  finished:  { color: 'var(--text-muted)', bg: 'rgba(255,255,255,0.04)', dot: false, label: 'FINAL' },
  scheduled: { color: 'var(--primary)',    bg: 'var(--primary-dim)',      dot: false, label: null },
};

function formatTime(utc: string | null | undefined, status: string) {
  if (status === 'live') return 'LIVE';
  if (status === 'finished') return 'Final';
  if (!utc) return 'Today';
  try { return new Date(utc).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }); }
  catch { return 'Today'; }
}

// ── Main card ─────────────────────────────────────────────────────────────────

export function NHLGameCard({ game, index = 0 }: Props) {
  const {
    home_team, away_team, home_team_abbrev, away_team_abbrev,
    predicted_winner, home_win_prob,
    model_confidence, reasons, game_time_utc, game_date, status,
    home_score, away_score, home_stats, away_stats,
  } = game;

  const cfg = STATUS_CFG[status] ?? STATUS_CFG.scheduled;
  const hasScore = (status === 'live' || status === 'finished') && home_score != null && away_score != null;
  const homeWinsPredicted = predicted_winner === home_team;
  const awayWinsPredicted = !homeWinsPredicted;

  // Winner's win probability — single source of truth for ring + bar
  const winnerProb = homeWinsPredicted ? home_win_prob : (1 - home_win_prob);
  const winnerPct = Math.round(winnerProb * 100);

  const [predHomeGoals, predAwayGoals] = predictedGoals(home_stats, away_stats, homeWinsPredicted);

  const dateLabel = (() => {
    const src = game_time_utc ? new Date(game_time_utc) : new Date(game_date + 'T12:00:00');
    return src.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  })();

  const timeLabel = formatTime(game_time_utc, status);
  const confColor = model_confidence === 'high' ? 'var(--primary)' : model_confidence === 'medium' ? 'var(--accent)' : 'var(--error)';

  const winnerGlow = homeWinsPredicted
    ? 'inset 3px 0 0 0 var(--primary)'
    : 'inset -3px 0 0 0 var(--primary)';

  const predictionCorrect = hasScore
    ? (home_score! > away_score! ? homeWinsPredicted : awayWinsPredicted)
    : null;

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

        {/* Header row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.06em' }}>
            {dateLabel.toUpperCase()}
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ModelBadge />
            <span style={{
              display: 'flex', alignItems: 'center', gap: '5px',
              background: cfg.bg, color: cfg.color,
              fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
              letterSpacing: '0.08em', padding: '3px 9px', borderRadius: '3px',
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

        {/* Teams scoreboard */}
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr auto 1fr',
          gap: '8px', alignItems: 'center',
          boxShadow: winnerGlow, borderRadius: '8px',
          background: 'rgba(0,0,0,0.2)', padding: '16px 12px',
          border: '1px solid var(--border)',
        }}>
          {/* Away */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
            <TeamLogo abbrev={away_team_abbrev} name={away_team} size={56} />
            <span style={{
              fontFamily: 'var(--font-body)', fontSize: '11px',
              fontWeight: awayWinsPredicted ? 700 : 400,
              color: awayWinsPredicted ? 'var(--text-primary)' : 'var(--text-secondary)',
              textAlign: 'center', lineHeight: 1.3,
            }}>{away_team}</span>
            {hasScore ? (
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '32px', fontWeight: 700,
                color: away_score! > home_score! ? 'var(--success)' : 'var(--text-muted)',
                letterSpacing: '-0.03em', lineHeight: 1,
              }}>{away_score}</span>
            ) : (
              <>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '32px', fontWeight: 700,
                  color: awayWinsPredicted ? confColor : 'var(--text-muted)',
                  letterSpacing: '-0.03em', lineHeight: 1,
                }}>{predAwayGoals}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>
                  PREDICTED
                </span>
              </>
            )}
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '8px', color: 'var(--text-muted)', letterSpacing: '0.12em', fontWeight: 600 }}>AWAY</span>
          </div>

          {/* Center */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', padding: '0 4px' }}>
            <div style={{ width: '1px', height: '16px', background: 'var(--border)' }} />
            <span style={{
              fontFamily: 'var(--font-display)', fontSize: '13px', fontWeight: 700,
              color: 'var(--border-bright)', letterSpacing: '0.06em',
            }}>
              {hasScore ? (status === 'live' ? 'LIVE' : 'FIN') : 'VS'}
            </span>
            <div style={{ width: '1px', height: '16px', background: 'var(--border)' }} />
          </div>

          {/* Home */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
            <TeamLogo abbrev={home_team_abbrev} name={home_team} size={56} />
            <span style={{
              fontFamily: 'var(--font-body)', fontSize: '11px',
              fontWeight: homeWinsPredicted ? 700 : 400,
              color: homeWinsPredicted ? 'var(--text-primary)' : 'var(--text-secondary)',
              textAlign: 'center', lineHeight: 1.3,
            }}>{home_team}</span>
            {hasScore ? (
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '32px', fontWeight: 700,
                color: home_score! > away_score! ? 'var(--success)' : 'var(--text-muted)',
                letterSpacing: '-0.03em', lineHeight: 1,
              }}>{home_score}</span>
            ) : (
              <>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '32px', fontWeight: 700,
                  color: homeWinsPredicted ? confColor : 'var(--text-muted)',
                  letterSpacing: '-0.03em', lineHeight: 1,
                }}>{predHomeGoals}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>
                  PREDICTED
                </span>
              </>
            )}
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '8px', color: 'var(--text-muted)', letterSpacing: '0.12em', fontWeight: 600 }}>HOME</span>
          </div>
        </div>

        {/* Confidence ring + predicted winner */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'auto 1fr',
          gap: '20px', alignItems: 'center',
          padding: '12px 16px', background: 'rgba(0,0,0,0.2)',
          border: '1px solid var(--border)', borderRadius: '8px',
        }}>
          <ConfidenceRing value={winnerProb} delay={index * 80 + 300} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
              color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase',
            }}>
              Predicted Winner
            </span>
            <span style={{
              fontFamily: 'var(--font-display)', fontSize: '22px', fontWeight: 800,
              color: 'var(--text-primary)', letterSpacing: '0.04em',
              lineHeight: 1.1, textTransform: 'uppercase',
            }}>
              {predicted_winner}
            </span>
            {predictionCorrect !== null && (
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
                color: predictionCorrect ? 'var(--success)' : 'var(--error)',
                letterSpacing: '0.1em',
              }}>
                {predictionCorrect ? '✓ CORRECT' : '✗ INCORRECT'}
              </span>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
              <div style={{ height: '3px', flex: 1, background: 'var(--border)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{
                  height: '100%', width: `${winnerPct}%`,
                  background: confColor, borderRadius: '2px',
                  transition: 'width 1s cubic-bezier(0.4,0,0.2,1)',
                }} />
              </div>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: confColor, fontWeight: 700, flexShrink: 0 }}>
                {winnerPct}%
              </span>
            </div>
          </div>
        </div>

        {/* Stats grid */}
        {home_stats && away_stats && (() => {
          const fmt = (n: number) => n.toFixed(2);
          const pct = (n: number) => `${(n * 100).toFixed(1)}%`;
          const diff = (a: number, b: number, t = 0) => Math.abs(a - b) > t ? a > b : undefined;

          return (
            <div style={{
              background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border)',
              borderRadius: '6px', overflow: 'hidden', marginTop: '2px',
            }}>
              <div style={{
                display: 'grid', gridTemplateColumns: '1fr 80px 1fr',
                padding: '7px 12px', background: 'rgba(255,255,255,0.02)',
                borderBottom: '1px solid var(--border)',
              }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700, color: 'var(--primary)', textAlign: 'right', letterSpacing: '0.1em' }}>HOME</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700, color: 'var(--text-muted)', textAlign: 'center', letterSpacing: '0.1em' }}>STATS</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700, color: 'var(--accent)', letterSpacing: '0.1em' }}>AWAY</span>
              </div>
              <div style={{ padding: '6px 12px', display: 'flex', flexDirection: 'column' }}>
                <StatRow label="PTS%" homeVal={home_stats.points_pct.toFixed(3)} awayVal={away_stats.points_pct.toFixed(3)} homeWins={diff(home_stats.points_pct, away_stats.points_pct, 0.01)} />
                <StatRow label="GF/G" homeVal={fmt(home_stats.goals_for_per_game)} awayVal={fmt(away_stats.goals_for_per_game)} homeWins={diff(home_stats.goals_for_per_game, away_stats.goals_for_per_game, 0.1)} />
                <StatRow label="GA/G" homeVal={fmt(home_stats.goals_against_per_game)} awayVal={fmt(away_stats.goals_against_per_game)} homeWins={diff(away_stats.goals_against_per_game, home_stats.goals_against_per_game, 0.1)} />
                {(home_stats.save_pct > 0 || away_stats.save_pct > 0) && (
                  <StatRow label="SV%" homeVal={pct(home_stats.save_pct)} awayVal={pct(away_stats.save_pct)} homeWins={diff(home_stats.save_pct, away_stats.save_pct, 0.002)} />
                )}
                {(home_stats.pp_pct > 0 || away_stats.pp_pct > 0) && (
                  <StatRow label="PP%" homeVal={pct(home_stats.pp_pct)} awayVal={pct(away_stats.pp_pct)} homeWins={diff(home_stats.pp_pct, away_stats.pp_pct, 0.005)} />
                )}
                <StatRow
                  label="W-L-OT"
                  homeVal={`${home_stats.wins}-${home_stats.losses}-${home_stats.ot_losses}`}
                  awayVal={`${away_stats.wins}-${away_stats.losses}-${away_stats.ot_losses}`}
                  homeWins={diff(home_stats.points_pct, away_stats.points_pct, 0.01)}
                />
              </div>
            </div>
          );
        })()}

        {/* Divider */}
        <div style={{ height: '1px', background: 'var(--border)' }} />

        {/* Reasons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
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

      </div>
    </div>
  );
}
