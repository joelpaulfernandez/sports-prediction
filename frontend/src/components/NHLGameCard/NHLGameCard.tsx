import type { NHLGamePrediction } from '../../types';

interface Props {
  game: NHLGamePrediction;
  index?: number;
}

// ── Team logo ────────────────────────────────────────────────────────────────

function TeamLogo({ abbrev, size = 56 }: { abbrev: string; name?: string; size?: number }) {
  const initials = abbrev.slice(0, 3).toUpperCase();
  const hue = abbrev.split('').reduce((a, c) => a + c.charCodeAt(0), 0) % 360;
  return (
    <div style={{
      width: size, height: size, borderRadius: '10px', flexShrink: 0,
      background: `hsl(${hue}, 55%, 18%)`,
      border: `1px solid hsl(${hue}, 55%, 30%)`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <span style={{
        fontFamily: 'var(--font-display)', fontSize: size * 0.32,
        fontWeight: 800, color: `hsl(${hue}, 70%, 72%)`,
        letterSpacing: '-0.01em',
      }}>
        {initials}
      </span>
    </div>
  );
}

// ── Win probability bar ──────────────────────────────────────────────────────

function ProbBar({ homeProb, homeAbbrev, awayAbbrev }: {
  homeProb: number; homeAbbrev: string; awayAbbrev: string;
}) {
  const awayProb = 1 - homeProb;
  const homeWins = homeProb >= 0.5;
  const homeColor = homeWins ? 'var(--primary)' : 'var(--text-muted)';
  const awayColor = !homeWins ? 'var(--success)' : 'var(--text-muted)';

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: homeColor, fontWeight: 600 }}>
          {homeAbbrev} {Math.round(homeProb * 100)}%
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: awayColor, fontWeight: 600 }}>
          {Math.round(awayProb * 100)}% {awayAbbrev}
        </span>
      </div>
      <div style={{
        height: '6px', borderRadius: '3px', overflow: 'hidden',
        background: 'var(--border)', display: 'flex',
      }}>
        <div style={{
          width: `${homeProb * 100}%`,
          background: homeWins ? 'var(--primary)' : 'var(--border-bright)',
          borderRadius: '3px 0 0 3px',
          transition: 'width 0.6s ease',
        }} />
        <div style={{
          flex: 1,
          background: !homeWins ? 'var(--success)' : 'var(--border-bright)',
          borderRadius: '0 3px 3px 0',
        }} />
      </div>
    </div>
  );
}

// ── Stat row ─────────────────────────────────────────────────────────────────

function StatRow({ label, home, away, higherBetter = true }: {
  label: string; home: number; away: number; higherBetter?: boolean;
}) {
  const homeWins = higherBetter ? home > away : home < away;
  const awayWins = higherBetter ? away > home : away < home;
  const fmt = (v: number) => v < 1 ? v.toFixed(3) : v.toFixed(2);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '8px', alignItems: 'center' }}>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '12px',
        color: homeWins ? 'var(--text-primary)' : 'var(--text-muted)',
        fontWeight: homeWins ? 600 : 400, textAlign: 'right',
      }}>
        {fmt(home)}
      </span>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)',
        textTransform: 'uppercase', letterSpacing: '0.08em', whiteSpace: 'nowrap',
      }}>
        {label}
      </span>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '12px',
        color: awayWins ? 'var(--text-primary)' : 'var(--text-muted)',
        fontWeight: awayWins ? 600 : 400, textAlign: 'left',
      }}>
        {fmt(away)}
      </span>
    </div>
  );
}

// ── Status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: NHLGamePrediction['status'] }) {
  if (status === 'live') {
    return (
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: '5px',
        fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 700,
        color: 'var(--success)', background: 'var(--success-dim)',
        border: '1px solid rgba(16,185,129,0.3)', borderRadius: '4px', padding: '3px 8px',
        letterSpacing: '0.1em',
      }}>
        <span style={{
          width: '6px', height: '6px', borderRadius: '50%',
          background: 'var(--success)', boxShadow: '0 0 6px var(--success)',
          animation: 'pulse-dot 2.5s ease-in-out infinite',
        }} />
        LIVE
      </span>
    );
  }
  if (status === 'finished') {
    return (
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
        color: 'var(--text-muted)', border: '1px solid var(--border)',
        borderRadius: '4px', padding: '3px 8px', letterSpacing: '0.1em',
      }}>
        FINAL
      </span>
    );
  }
  return (
    <span style={{
      fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
      color: 'var(--text-secondary)', border: '1px solid var(--border)',
      borderRadius: '4px', padding: '3px 8px', letterSpacing: '0.1em',
    }}>
      SCHEDULED
    </span>
  );
}

// ── Game time ─────────────────────────────────────────────────────────────────

function GameTime({ utc }: { utc?: string | null }) {
  if (!utc) return null;
  try {
    const d = new Date(utc);
    return (
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.05em',
      }}>
        {d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZoneName: 'short' })}
      </span>
    );
  } catch {
    return null;
  }
}

// ── Main card ────────────────────────────────────────────────────────────────

export function NHLGameCard({ game, index = 0 }: Props) {
  const homeWins = game.home_win_prob >= 0.5;
  const isFinished = game.status === 'finished';
  const actualWinnerAbbrev = isFinished
    ? (game.home_score != null && game.away_score != null
        ? (game.home_score > game.away_score ? game.home_team_abbrev : game.away_team_abbrev)
        : null)
    : null;
  const predictionCorrect = isFinished && actualWinnerAbbrev
    ? actualWinnerAbbrev === game.predicted_winner_abbrev
    : null;

  const confColor =
    game.model_confidence === 'high' ? 'var(--primary)' :
    game.model_confidence === 'medium' ? 'var(--accent)' : 'var(--error)';

  return (
    <div
      style={{
        background: 'var(--card)',
        border: '1px solid var(--border)',
        borderRadius: '12px',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        animation: 'fadeUp 0.4s ease both',
        animationDelay: `${index * 60}ms`,
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <StatusBadge status={game.status} />
          <GameTime utc={game.game_time_utc} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '9px', color: confColor,
            background: `${confColor}18`, border: `1px solid ${confColor}44`,
            borderRadius: '3px', padding: '2px 7px', letterSpacing: '0.1em',
            fontWeight: 600, textTransform: 'uppercase',
          }}>
            {game.model_confidence}
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)',
            letterSpacing: '0.06em',
          }}>
            {game.confidence}% conf
          </span>
        </div>
      </div>

      {/* Teams */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '16px', alignItems: 'center' }}>
        {/* Home */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '8px' }}>
          <TeamLogo abbrev={game.home_team_abbrev} name={game.home_team} />
          <div>
            <div style={{
              fontFamily: 'var(--font-display)', fontSize: '15px', fontWeight: 800,
              color: homeWins ? 'var(--text-primary)' : 'var(--text-secondary)',
              textTransform: 'uppercase', letterSpacing: '0.03em',
            }}>
              {game.home_team}
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
              HOME
            </div>
            {game.home_stats && (
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                {game.home_stats.wins}-{game.home_stats.losses}-{game.home_stats.ot_losses}
              </div>
            )}
          </div>
        </div>

        {/* Score / VS */}
        <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {isFinished && game.home_score != null && game.away_score != null ? (
            <>
              <div style={{
                fontFamily: 'var(--font-display)', fontSize: '28px', fontWeight: 900,
                color: 'var(--text-primary)', letterSpacing: '0.04em',
              }}>
                {game.home_score} – {game.away_score}
              </div>
              {predictionCorrect !== null && (
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
                  color: predictionCorrect ? 'var(--success)' : 'var(--error)',
                  letterSpacing: '0.1em',
                }}>
                  {predictionCorrect ? '✓ CORRECT' : '✗ WRONG'}
                </span>
              )}
            </>
          ) : (
            <div style={{
              fontFamily: 'var(--font-display)', fontSize: '18px', fontWeight: 700,
              color: 'var(--text-muted)', letterSpacing: '0.1em',
            }}>
              VS
            </div>
          )}
        </div>

        {/* Away */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
          <TeamLogo abbrev={game.away_team_abbrev} name={game.away_team} />
          <div style={{ textAlign: 'right' }}>
            <div style={{
              fontFamily: 'var(--font-display)', fontSize: '15px', fontWeight: 800,
              color: !homeWins ? 'var(--text-primary)' : 'var(--text-secondary)',
              textTransform: 'uppercase', letterSpacing: '0.03em',
            }}>
              {game.away_team}
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
              AWAY
            </div>
            {game.away_stats && (
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                {game.away_stats.wins}-{game.away_stats.losses}-{game.away_stats.ot_losses}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Probability bar */}
      <ProbBar
        homeProb={game.home_win_prob}
        homeAbbrev={game.home_team_abbrev}
        awayAbbrev={game.away_team_abbrev}
      />

      {/* Predicted winner label */}
      <div style={{
        padding: '10px 14px',
        background: 'rgba(59,130,246,0.06)',
        border: '1px solid rgba(59,130,246,0.15)',
        borderRadius: '8px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>
          PREDICTED WINNER
        </span>
        <span style={{
          fontFamily: 'var(--font-display)', fontSize: '14px', fontWeight: 800,
          color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em',
        }}>
          {game.predicted_winner}
        </span>
      </div>

      {/* Stats comparison */}
      {game.home_stats && game.away_stats && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', marginBottom: '10px', paddingBottom: '8px', borderBottom: '1px solid var(--border)' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', textAlign: 'right', letterSpacing: '0.08em' }}>
              {game.home_team_abbrev}
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', textAlign: 'center', letterSpacing: '0.08em', paddingInline: '8px' }}>
              STATS
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', textAlign: 'left', letterSpacing: '0.08em' }}>
              {game.away_team_abbrev}
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <StatRow label="Pts%" home={game.home_stats.points_pct} away={game.away_stats.points_pct} />
            <StatRow label="GF/G" home={game.home_stats.goals_for_per_game} away={game.away_stats.goals_for_per_game} />
            <StatRow label="GA/G" home={game.home_stats.goals_against_per_game} away={game.away_stats.goals_against_per_game} higherBetter={false} />
            {(game.home_stats.save_pct > 0 || game.away_stats.save_pct > 0) && (
              <StatRow label="SV%" home={game.home_stats.save_pct} away={game.away_stats.save_pct} />
            )}
            {(game.home_stats.pp_pct > 0 || game.away_stats.pp_pct > 0) && (
              <StatRow label="PP%" home={game.home_stats.pp_pct} away={game.away_stats.pp_pct} />
            )}
          </div>
        </div>
      )}

      {/* Reasons */}
      {game.reasons.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {game.reasons.slice(0, 3).map((r, i) => (
            <div key={i} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: '10px',
                color: 'var(--primary)', flexShrink: 0, marginTop: '1px',
              }}>
                ›
              </span>
              <span style={{
                fontFamily: 'var(--font-body)', fontSize: '12px',
                color: 'var(--text-secondary)', lineHeight: 1.5,
              }}>
                {r.text}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
