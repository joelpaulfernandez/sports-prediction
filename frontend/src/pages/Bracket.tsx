import { useEffect, useState } from 'react';
import type { PlayoffBracket, BracketSeries, BracketGame } from '../types/bracket';
import { getBracket } from '../api/predictions';

// ── Tiny team logo ──────────────────────────────────────────────────────────
function TeamLogo({ teamId, size = 24 }: { teamId: number; size?: number }) {
  return (
    <img
      src={`https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`}
      alt=""
      width={size}
      height={size}
      style={{ objectFit: 'contain', flexShrink: 0 }}
    />
  );
}

// ── Game badge — small ✓/✗ marker per game in a series ──────────────────────
function GameBadge({ game }: { game: BracketGame }) {
  const colors = game.correct === true
    ? { bg: 'var(--success-dim)', border: 'rgba(16,185,129,0.5)', fg: 'var(--success)', label: '✓' }
    : game.correct === false
    ? { bg: 'var(--error-dim)', border: 'rgba(239,68,68,0.5)', fg: 'var(--error)', label: '✗' }
    : { bg: 'rgba(100,116,139,0.10)', border: 'var(--border)', fg: 'var(--text-muted)', label: '·' };

  const tooltip = game.predicted_winner_name
    ? `${game.date}: predicted ${game.predicted_winner_name} (${Math.round((game.confidence ?? 0) * 100)}%) — ${game.correct ? 'correct' : 'wrong'}`
    : `${game.date}: no prediction recorded`;

  return (
    <span
      title={tooltip}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '20px',
        height: '20px',
        background: colors.bg,
        border: `1px solid ${colors.border}`,
        color: colors.fg,
        borderRadius: '4px',
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        fontWeight: 700,
        lineHeight: 1,
      }}
    >
      {colors.label}
    </span>
  );
}

// ── Series card ─────────────────────────────────────────────────────────────
function SeriesCard({ series }: { series: BracketSeries }) {
  const { higher_seed, lower_seed, winner_team_id, games } = series;
  const higherWon = winner_team_id === higher_seed.team_id;
  const lowerWon = winner_team_id === lower_seed.team_id;
  const isComplete = winner_team_id !== null;

  const teamRow = (team: typeof higher_seed, won: boolean, dim: boolean) => (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '6px 10px',
      borderRadius: '4px',
      background: won ? 'var(--primary-dim)' : 'transparent',
      opacity: dim ? 0.45 : 1,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
        <TeamLogo teamId={team.team_id} size={22} />
        <span style={{
          fontFamily: 'var(--font-body)',
          color: won ? 'var(--text-primary)' : 'var(--text-secondary)',
          fontSize: '12px',
          fontWeight: won ? 600 : 500,
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}>
          {team.team_name.split(' ').slice(-1)[0]}
        </span>
      </div>
      <span style={{
        fontFamily: 'var(--font-mono)',
        color: won ? 'var(--primary)' : 'var(--text-muted)',
        fontSize: '14px',
        fontWeight: 700,
        flexShrink: 0,
        marginLeft: '8px',
      }}>
        {team.wins}
      </span>
    </div>
  );

  return (
    <div style={{
      background: 'var(--card)',
      border: '1px solid var(--border)',
      borderRadius: '8px',
      padding: '8px',
      display: 'flex',
      flexDirection: 'column',
      gap: '2px',
      minWidth: '200px',
    }}>
      {teamRow(higher_seed, higherWon, isComplete && lowerWon)}
      {teamRow(lower_seed, lowerWon, isComplete && higherWon)}

      {games.length > 0 && (
        <div style={{
          marginTop: '6px',
          paddingTop: '8px',
          borderTop: '1px solid var(--border)',
          display: 'flex',
          gap: '4px',
          alignItems: 'center',
          justifyContent: 'center',
          flexWrap: 'wrap',
        }}>
          {games.map((g) => <GameBadge key={g.game_id} game={g} />)}
        </div>
      )}
    </div>
  );
}

// ── Round column ────────────────────────────────────────────────────────────
function RoundColumn({ name, seriesList }: { name: string; seriesList: BracketSeries[] }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '14px',
      flex: '1 1 0',
      minWidth: '210px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        textAlign: 'center',
        color: 'var(--text-muted)',
        fontSize: '10px',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.14em',
        paddingBottom: '8px',
        borderBottom: '1px solid var(--border)',
      }}>
        {name}
      </div>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '14px',
        justifyContent: 'space-around',
        flex: 1,
      }}>
        {seriesList.length === 0 ? (
          <div style={{
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)',
            fontSize: '11px',
            textAlign: 'center',
            padding: '40px 0',
            letterSpacing: '0.08em',
          }}>
            NOT STARTED
          </div>
        ) : (
          seriesList.map((s, i) => (
            <SeriesCard key={`${s.higher_seed.team_id}-${s.lower_seed.team_id}-${i}`} series={s} />
          ))
        )}
      </div>
    </div>
  );
}

function StatBlock({ label, value, color = 'var(--text-primary)' }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        color: 'var(--text-muted)',
        fontSize: '10px',
        textTransform: 'uppercase',
        letterSpacing: '0.12em',
        fontWeight: 600,
      }}>
        {label}
      </div>
      <div style={{
        fontFamily: 'var(--font-display)',
        color,
        fontSize: '26px',
        fontWeight: 800,
        marginTop: '4px',
        letterSpacing: '-0.01em',
      }}>
        {value}
      </div>
    </div>
  );
}

// ── Main page ───────────────────────────────────────────────────────────────
export function Bracket() {
  const [data, setData] = useState<PlayoffBracket | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getBracket()
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load bracket'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const allRoundNames = ['First Round', 'Conference Semifinals', 'Conference Finals', 'NBA Finals'];
  const roundsByName = new Map(data?.rounds.map((r) => [r.name, r]) ?? []);

  return (
    <main style={{
      maxWidth: '1400px',
      margin: '0 auto',
      padding: '0 24px 80px',
      width: '100%',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{ padding: '52px 0 24px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <div style={{
          alignSelf: 'flex-start',
          fontFamily: 'var(--font-mono)',
          background: 'var(--primary-dim)',
          border: '1px solid rgba(59,130,246,0.22)',
          borderRadius: '4px',
          padding: '4px 10px',
          fontSize: '10px',
          fontWeight: 600,
          color: 'var(--primary)',
          textTransform: 'uppercase',
          letterSpacing: '0.12em',
        }}>
          {data?.season ?? '2025–26'} Playoffs
        </div>
        <h1 style={{
          margin: 0,
          fontFamily: 'var(--font-display)',
          fontSize: 'clamp(32px, 4vw, 48px)',
          fontWeight: 800,
          color: 'var(--text-primary)',
          lineHeight: 1.05,
          letterSpacing: '-0.02em',
          textTransform: 'uppercase',
        }}>
          Playoff Bracket
        </h1>
        <p style={{
          margin: 0,
          fontFamily: 'var(--font-body)',
          color: 'var(--text-secondary)',
          fontSize: '14px',
        }}>
          Each game is annotated with the model's prediction.
          {' '}
          <span style={{ color: 'var(--success)', fontWeight: 600 }}>✓</span> correct,
          {' '}
          <span style={{ color: 'var(--error)', fontWeight: 600 }}>✗</span> wrong,
          {' '}
          <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>·</span> no prediction on file.
        </p>
      </div>

      {data?.summary && data.summary.games_with_prediction > 0 && (
        <div style={{
          display: 'flex',
          gap: '32px',
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: '8px',
          padding: '20px 24px',
          marginBottom: '32px',
        }}>
          <StatBlock label="Prediction Accuracy" value={`${data.summary.accuracy_pct}%`} color="var(--primary)" />
          <div style={{ width: '1px', background: 'var(--border)' }} />
          <StatBlock label="Games Predicted" value={`${data.summary.correct_predictions} / ${data.summary.games_with_prediction}`} />
          <div style={{ width: '1px', background: 'var(--border)' }} />
          <StatBlock label="Total Playoff Games" value={String(data.summary.total_games)} />
        </div>
      )}

      {loading && (
        <div style={{
          padding: '100px 0',
          textAlign: 'center',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-muted)',
          fontSize: '12px',
          letterSpacing: '0.08em',
        }}>
          LOADING BRACKET…
        </div>
      )}
      {error && (
        <div style={{
          background: 'var(--error-dim)',
          border: '1px solid rgba(239,68,68,0.3)',
          borderRadius: '8px',
          padding: '20px 24px',
          color: 'var(--error)',
          fontFamily: 'var(--font-body)',
          fontSize: '14px',
        }}>
          {error}
        </div>
      )}
      {!loading && !error && (
        <div style={{
          display: 'flex',
          gap: '24px',
          alignItems: 'stretch',
          overflowX: 'auto',
          paddingBottom: '8px',
        }}>
          {allRoundNames.map((name) => (
            <RoundColumn
              key={name}
              name={name}
              seriesList={roundsByName.get(name)?.series ?? []}
            />
          ))}
        </div>
      )}
    </main>
  );
}
