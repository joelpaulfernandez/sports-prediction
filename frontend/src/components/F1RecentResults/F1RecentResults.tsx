import { useState } from 'react';
import type { F1RecentResult, F1ResultDriver } from '../../types';

interface Props {
  results: F1RecentResult[];
}

const TEAM_COLORS: Record<string, string> = {
  'Red Bull': '#3671C6', 'Ferrari': '#E8002D', 'Mercedes': '#27F4D2',
  'McLaren': '#FF8000', 'Aston Martin': '#229971', 'Alpine': '#FF87BC',
  'Williams': '#64C4FF', 'RB': '#6692FF', 'Haas': '#B6BABD', 'Kick Sauber': '#52E252',
};
function teamColor(team: string): string {
  for (const [k, v] of Object.entries(TEAM_COLORS)) {
    if (team.includes(k)) return v;
  }
  const hue = team.split('').reduce((a, c) => a + c.charCodeAt(0), 0) % 360;
  return `hsl(${hue}, 60%, 55%)`;
}

function positionLabel(pos: number) {
  return `P${pos}`;
}

// ── Side-by-side comparison for one race ─────────────────────────────────────

function RaceComparison({ result, expanded, onToggle }: {
  result: F1RecentResult;
  expanded: boolean;
  onToggle: () => void;
}) {
  const { event, circuit_country, race_date, winner_correct, podium_overlap, spearman, predicted, actual } = result;

  const dateLabel = new Date(race_date + 'T12:00:00').toLocaleDateString('en-US', {
    month: 'short', day: 'numeric',
  });

  const overlapColor = podium_overlap >= 2 ? 'var(--success)' : podium_overlap === 1 ? 'var(--accent)' : 'var(--error)';

  return (
    <div style={{
      background: 'var(--card)',
      border: '1px solid var(--border)',
      borderRadius: '10px',
      overflow: 'hidden',
      transition: 'border-color 0.15s',
    }}>
      {/* Top accent */}
      <div style={{
        height: '2px',
        background: winner_correct
          ? 'linear-gradient(90deg, transparent, var(--success), transparent)'
          : 'linear-gradient(90deg, transparent, var(--error), transparent)',
      }} />

      {/* Summary row — always visible */}
      <button
        onClick={onToggle}
        style={{
          width: '100%', background: 'none', border: 'none', cursor: 'pointer',
          padding: '14px 18px',
          display: 'grid',
          gridTemplateColumns: '1fr auto auto auto auto',
          alignItems: 'center',
          gap: '16px',
          textAlign: 'left',
        }}
      >
        {/* Event */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <span style={{
            fontFamily: 'var(--font-display)', fontSize: '13px', fontWeight: 800,
            color: 'var(--text-primary)', letterSpacing: '0.04em', textTransform: 'uppercase',
          }}>
            {event}
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.06em' }}>
            {circuit_country} · {dateLabel}
          </span>
        </div>

        {/* Winner badge */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '5px',
          background: winner_correct ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
          border: `1px solid ${winner_correct ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
          borderRadius: '4px', padding: '3px 8px', flexShrink: 0,
        }}>
          <span style={{ fontSize: '10px' }}>{winner_correct ? '✓' : '✗'}</span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
            color: winner_correct ? 'var(--success)' : 'var(--error)', letterSpacing: '0.08em',
          }}>
            WINNER
          </span>
        </div>

        {/* Podium */}
        <div style={{ textAlign: 'center', flexShrink: 0 }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 700, color: overlapColor }}>
            {podium_overlap}/3
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '8px', color: 'var(--text-muted)', letterSpacing: '0.06em' }}>PODIUM</div>
        </div>

        {/* Spearman */}
        <div style={{ textAlign: 'center', flexShrink: 0 }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 700,
            color: spearman !== null && spearman >= 0.65 ? 'var(--success)' : spearman !== null && spearman >= 0.4 ? 'var(--accent)' : 'var(--text-muted)',
          }}>
            {spearman !== null ? spearman.toFixed(2) : '—'}
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '8px', color: 'var(--text-muted)', letterSpacing: '0.06em' }}>SPEAR</div>
        </div>

        {/* Chevron */}
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)',
          transition: 'transform 0.2s',
          display: 'inline-block',
          transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
          flexShrink: 0,
        }}>▶</span>
      </button>

      {/* Expanded: side-by-side top 10 */}
      {expanded && (
        <div style={{ borderTop: '1px solid var(--border)', padding: '0 18px 16px' }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '12px',
            paddingTop: '14px',
          }}>
            <DriverList label="PREDICTED" drivers={predicted} actual={actual} side="predicted" />
            <DriverList label="ACTUAL" drivers={actual} predicted={predicted} side="actual" />
          </div>
        </div>
      )}
    </div>
  );
}

function DriverList({ label, drivers, actual, predicted, side }: {
  label: string;
  drivers: F1ResultDriver[];
  actual?: F1ResultDriver[];
  predicted?: F1ResultDriver[];
  side: 'predicted' | 'actual';
}) {
  const accentColor = side === 'predicted' ? 'var(--primary)' : 'var(--accent)';
  const compareList = side === 'predicted' ? actual : predicted;

  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
        color: accentColor, letterSpacing: '0.12em',
        paddingBottom: '8px', borderBottom: '1px solid var(--border)', marginBottom: '6px',
      }}>
        {label}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
        {drivers.map(d => {
          const compareDriver = compareList?.find(c => c.driver_id === d.driver_id);
          const samePosition = compareDriver?.position === d.position;
          const isWinner = d.position === 1;
          const isPodium = d.position <= 3;
          const color = teamColor(d.team);
          const podiumColors = ['var(--accent)', '#C0C0C0', '#CD7F32'];
          const posColor = isPodium ? podiumColors[d.position - 1] : 'var(--text-muted)';

          return (
            <div key={d.driver_id} style={{
              display: 'grid',
              gridTemplateColumns: '20px 4px 1fr',
              alignItems: 'center',
              gap: '8px',
              padding: '4px 6px',
              borderRadius: '4px',
              background: isPodium ? 'rgba(255,255,255,0.02)' : 'transparent',
              border: isPodium ? '1px solid var(--border)' : '1px solid transparent',
            }}>
              {/* Position */}
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: isPodium ? '13px' : '11px',
                fontWeight: isPodium ? 700 : 400,
                color: posColor,
                textAlign: 'right',
              }}>
                {positionLabel(d.position)}
              </span>

              {/* Team color */}
              <div style={{
                width: '3px', height: isPodium ? '24px' : '18px',
                borderRadius: '2px', background: color,
                boxShadow: isPodium ? `0 0 5px ${color}88` : 'none',
              }} />

              {/* Name + team */}
              <div style={{ minWidth: 0 }}>
                <div style={{
                  fontFamily: isPodium ? 'var(--font-display)' : 'var(--font-body)',
                  fontSize: isPodium ? '12px' : '11px',
                  fontWeight: isPodium ? 700 : 400,
                  color: samePosition ? 'var(--success)' : isPodium ? 'var(--text-primary)' : 'var(--text-secondary)',
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  letterSpacing: isPodium ? '0.03em' : '0',
                  textTransform: isPodium ? 'uppercase' : 'none',
                }}>
                  {d.driver.split(' ').pop()}
                  {samePosition && (
                    <span style={{ color: 'var(--success)', marginLeft: '4px', fontSize: '9px' }}>✓</span>
                  )}
                </div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: '8px',
                  color: 'var(--text-muted)', letterSpacing: '0.04em',
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                }}>
                  {d.team}
                  {side === 'predicted' && d.win_prob !== undefined && (
                    <span style={{ color: 'var(--primary)', marginLeft: '4px' }}>
                      {Math.round(d.win_prob * 100)}%
                    </span>
                  )}
                  {side === 'actual' && d.status && d.status !== 'Finished' && !d.status.startsWith('+') && (
                    <span style={{ color: 'var(--error)', marginLeft: '4px' }}>DNF</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Summary stats bar ─────────────────────────────────────────────────────────

function SummaryBar({ results }: { results: F1RecentResult[] }) {
  if (results.length === 0) return null;
  const winnerAcc = results.filter(r => r.winner_correct).length / results.length;
  const avgPodium = results.reduce((s, r) => s + r.podium_overlap, 0) / (results.length * 3);
  const spearValues = results.map(r => r.spearman).filter((s): s is number => s !== null);
  const avgSpear = spearValues.length > 0 ? spearValues.reduce((a, b) => a + b, 0) / spearValues.length : null;

  const stat = (label: string, value: string, color: string) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', alignItems: 'center' }}>
      <span style={{ fontFamily: 'var(--font-display)', fontSize: '24px', fontWeight: 900, color, lineHeight: 1 }}>
        {value}
      </span>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.1em' }}>
        {label}
      </span>
    </div>
  );

  return (
    <div style={{
      display: 'flex', justifyContent: 'space-around', alignItems: 'center',
      padding: '16px 24px',
      background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border)',
      borderRadius: '8px', marginBottom: '20px',
    }}>
      {stat('WINNER ACC', `${Math.round(winnerAcc * 100)}%`, winnerAcc >= 0.5 ? 'var(--success)' : 'var(--accent)')}
      <div style={{ width: '1px', height: '32px', background: 'var(--border)' }} />
      {stat('PODIUM ACC', `${Math.round(avgPodium * 100)}%`, avgPodium >= 0.6 ? 'var(--success)' : 'var(--accent)')}
      <div style={{ width: '1px', height: '32px', background: 'var(--border)' }} />
      {stat('AVG SPEARMAN', avgSpear !== null ? avgSpear.toFixed(2) : '—', avgSpear !== null && avgSpear >= 0.65 ? 'var(--success)' : 'var(--accent)')}
      <div style={{ width: '1px', height: '32px', background: 'var(--border)' }} />
      {stat('SAMPLE', `${results.length} RACES`, 'var(--text-muted)')}
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export function F1RecentResults({ results }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(results[0]?.race_id ?? null);

  if (results.length === 0) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '16px',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
          color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase',
        }}>
          Past {results.length} Races — Predicted vs Actual
        </span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '9px',
          color: 'var(--text-muted)', letterSpacing: '0.06em',
        }}>
          {results[0]?.model_version === 'xgboost-ranker-v1' ? 'XGBoost' : 'Rule-based (pre-training)'}
        </span>
      </div>

      <SummaryBar results={results} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {results.map(r => (
          <RaceComparison
            key={r.race_id}
            result={r}
            expanded={expandedId === r.race_id}
            onToggle={() => setExpandedId(expandedId === r.race_id ? null : r.race_id)}
          />
        ))}
      </div>
    </div>
  );
}
