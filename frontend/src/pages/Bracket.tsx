import { useEffect, useState } from 'react';
import type { PlayoffBracket, BracketSeries, BracketGame } from '../types/bracket';
import { getBracket } from '../api/predictions';

// ── Tiny team logo ──────────────────────────────────────────────────────────
function TeamLogo({ teamId, size = 28 }: { teamId: number; size?: number }) {
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
    ? { bg: 'rgba(0,232,122,0.18)', border: 'rgba(0,232,122,0.5)', fg: '#00e87a', label: '✓' }
    : game.correct === false
    ? { bg: 'rgba(248,113,113,0.18)', border: 'rgba(248,113,113,0.5)', fg: '#f87171', label: '✗' }
    : { bg: 'rgba(74,96,117,0.15)', border: 'rgba(74,96,117,0.4)', fg: '#4a6075', label: '·' };

  const tooltip = game.predicted_winner_name
    ? `Game ${game.date}: predicted ${game.predicted_winner_name} (${Math.round((game.confidence ?? 0) * 100)}%) — ${game.correct ? 'correct' : 'wrong'}`
    : `Game ${game.date}: no prediction recorded`;

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
        fontSize: '11px',
        fontWeight: 800,
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
      borderRadius: '6px',
      background: won ? 'rgba(0,232,122,0.06)' : 'transparent',
      opacity: dim ? 0.5 : 1,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
        <TeamLogo teamId={team.team_id} size={24} />
        <span style={{
          color: won ? '#f0f6ff' : '#8ca3be',
          fontSize: '12px',
          fontWeight: won ? 700 : 500,
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}>
          {team.team_name.split(' ').slice(-1)[0]}
        </span>
      </div>
      <span style={{
        color: won ? '#00e87a' : '#4a6075',
        fontSize: '14px',
        fontWeight: 800,
        flexShrink: 0,
        marginLeft: '8px',
      }}>
        {team.wins}
      </span>
    </div>
  );

  return (
    <div style={{
      background: 'linear-gradient(160deg, #131f2e 0%, #0f1923 100%)',
      border: '1px solid #1e2d40',
      borderRadius: '10px',
      padding: '10px',
      display: 'flex',
      flexDirection: 'column',
      gap: '4px',
      minWidth: '200px',
    }}>
      {teamRow(higher_seed, higherWon, isComplete && lowerWon)}
      {teamRow(lower_seed, lowerWon, isComplete && higherWon)}

      {/* Game-by-game prediction badges */}
      {games.length > 0 && (
        <div style={{
          marginTop: '6px',
          paddingTop: '8px',
          borderTop: '1px solid #1a2535',
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
        textAlign: 'center',
        color: '#4a6075',
        fontSize: '11px',
        fontWeight: 800,
        textTransform: 'uppercase',
        letterSpacing: '0.12em',
        paddingBottom: '8px',
        borderBottom: '1px solid #1a2535',
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
            color: '#2d4060',
            fontSize: '12px',
            textAlign: 'center',
            padding: '40px 0',
          }}>
            Not started
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

  // Always render all 4 round columns so the bracket structure is clear
  const allRoundNames = ['First Round', 'Conference Semifinals', 'Conference Finals', 'NBA Finals'];
  const roundsByName = new Map(data?.rounds.map((r) => [r.name, r]) ?? []);

  return (
    <main style={{
      maxWidth: '1400px',
      margin: '0 auto',
      padding: '0 24px 80px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Hero */}
      <div style={{ padding: '52px 0 24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{
          alignSelf: 'flex-start',
          background: 'rgba(0,232,122,0.1)',
          border: '1px solid rgba(0,232,122,0.2)',
          borderRadius: '6px',
          padding: '4px 10px',
          fontSize: '11px',
          fontWeight: 700,
          color: '#00e87a',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
        }}>
          {data?.season ?? '2025–26'} Playoffs
        </div>
        <h1 style={{
          margin: 0,
          fontSize: 'clamp(28px, 4vw, 42px)',
          fontWeight: 900,
          color: '#f0f6ff',
          lineHeight: 1.1,
          letterSpacing: '-0.03em',
        }}>
          Playoff Bracket
        </h1>
        <p style={{ margin: 0, color: '#4a6075', fontSize: '15px' }}>
          Each game is annotated with the model's prediction.
          {' '}
          <span style={{ color: '#00e87a' }}>✓</span> = correct,
          {' '}
          <span style={{ color: '#f87171' }}>✗</span> = wrong,
          {' '}
          <span style={{ color: '#4a6075' }}>·</span> = no prediction on file.
        </p>
      </div>

      {/* Accuracy summary */}
      {data?.summary && data.summary.games_with_prediction > 0 && (
        <div style={{
          display: 'flex',
          gap: '24px',
          background: 'linear-gradient(135deg, #131f2e, #0f1923)',
          border: '1px solid #1e2d40',
          borderRadius: '12px',
          padding: '16px 24px',
          marginBottom: '32px',
        }}>
          <div>
            <div style={{ color: '#4a6075', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 }}>
              Prediction Accuracy
            </div>
            <div style={{ color: '#00e87a', fontSize: '24px', fontWeight: 900, marginTop: '4px' }}>
              {data.summary.accuracy_pct}%
            </div>
          </div>
          <div style={{ width: '1px', background: '#1e2d40' }} />
          <div>
            <div style={{ color: '#4a6075', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 }}>
              Games Predicted
            </div>
            <div style={{ color: '#f0f6ff', fontSize: '24px', fontWeight: 900, marginTop: '4px' }}>
              {data.summary.correct_predictions} / {data.summary.games_with_prediction}
            </div>
          </div>
          <div style={{ width: '1px', background: '#1e2d40' }} />
          <div>
            <div style={{ color: '#4a6075', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 }}>
              Total Playoff Games
            </div>
            <div style={{ color: '#f0f6ff', fontSize: '24px', fontWeight: 900, marginTop: '4px' }}>
              {data.summary.total_games}
            </div>
          </div>
        </div>
      )}

      {/* Bracket grid */}
      {loading && (
        <div style={{ padding: '100px 0', textAlign: 'center', color: '#4a6075' }}>
          Loading bracket…
        </div>
      )}
      {error && (
        <div style={{
          background: 'rgba(248,113,113,0.06)',
          border: '1px solid rgba(248,113,113,0.2)',
          borderRadius: '12px',
          padding: '20px 24px',
          color: '#fca5a5',
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
