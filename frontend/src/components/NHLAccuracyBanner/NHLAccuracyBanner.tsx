import type { NHLAccuracyStats } from '../../types';

interface Props {
  stats: NHLAccuracyStats;
}

function StatCell({ value, label, color }: { value: string | number; label: string; color?: string }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: '6px',
      padding: '20px 24px', borderRight: '1px solid var(--border)', flex: 1,
    }}>
      <span style={{
        fontFamily: 'var(--font-display)', fontSize: '48px', fontWeight: 900,
        letterSpacing: '-0.02em', lineHeight: 1,
        color: color ?? 'var(--text-primary)',
        textShadow: color ? `0 0 32px ${color}44` : undefined,
      }}>
        {value}
      </span>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
        color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase',
      }}>
        {label}
      </span>
    </div>
  );
}

export function NHLAccuracyBanner({ stats }: Props) {
  const { total_predictions, correct_predictions, accuracy_percentage, last_updated, backtest_accuracy, backtest_games } = stats;

  const hasLive = total_predictions > 0;
  const pct = hasLive ? accuracy_percentage : backtest_accuracy * 100;
  const displayPct = `${pct.toFixed(1)}%`;
  const wrong = total_predictions - correct_predictions;

  const pctColor = pct >= 65 ? 'var(--success)' : pct >= 50 ? 'var(--accent)' : 'var(--error)';
  const barWidth = Math.min(100, pct);

  const formattedDate = new Date(last_updated).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });

  return (
    <div style={{
      background: 'var(--card)', border: '1px solid var(--border)',
      borderRadius: '10px', overflow: 'hidden',
      animation: 'fadeUp 0.5s ease both', animationDelay: '0.15s',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 24px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: 'rgba(0,0,0,0.2)',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600,
          color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase',
        }}>
          Model Accuracy · 2025–26 Season
        </span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '10px',
          color: 'var(--text-muted)', letterSpacing: '0.06em',
        }}>
          Updated {formattedDate}
        </span>
      </div>

      {/* Stats row */}
      <div style={{ display: 'flex', flexWrap: 'wrap' }}>
        <StatCell value={displayPct} label={hasLive ? 'Accuracy' : 'Backtested Accuracy'} color={pctColor} />
        {hasLive ? (
          <>
            <StatCell value={correct_predictions} label="Correct" color="var(--success)" />
            <StatCell value={wrong} label="Incorrect" color={wrong > 0 ? 'var(--error)' : 'var(--text-muted)'} />
            <StatCell value={total_predictions} label="Total" />
          </>
        ) : (
          <>
            <StatCell value={backtest_games.toLocaleString()} label="Games Backtested" />
            <StatCell value="58.6%" label="High Conf. Accuracy" color="var(--success)" />
            <StatCell value="NHL Stats" label="Model" />
          </>
        )}
      </div>

      {/* Progress bar */}
      <div style={{ padding: '0 24px' }}>
        <div style={{
          height: '3px', background: 'var(--border)', borderRadius: '2px',
          overflow: 'hidden', marginBottom: '16px',
        }}>
          <div style={{
            height: '100%', width: `${barWidth}%`,
            background: `linear-gradient(90deg, ${pctColor}88, ${pctColor})`,
            borderRadius: '2px',
            transition: 'width 1.2s cubic-bezier(0.4,0,0.2,1)',
            boxShadow: `0 0 8px ${pctColor}55`,
          }} />
        </div>
      </div>

      {/* Footer */}
      <div style={{
        padding: '12px 24px 16px', borderTop: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap',
        background: 'rgba(0,0,0,0.15)',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 700,
          color: 'var(--text-muted)', background: 'rgba(255,255,255,0.03)',
          border: '1px solid var(--border)', borderRadius: '3px',
          padding: '3px 7px', letterSpacing: '0.1em', textTransform: 'uppercase',
        }}>
          NHL Stats v1
        </span>
        {!hasLive ? (
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px',
            color: 'var(--text-muted)', fontStyle: 'italic',
          }}>
            Backtested on {backtest_games.toLocaleString()} regular season games · live accuracy updates as games finish.
          </span>
        ) : (
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)',
          }}>
            Backtested accuracy:{' '}
            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
              {(backtest_accuracy * 100).toFixed(1)}%
            </span>
            {' '}across {backtest_games.toLocaleString()} games
          </span>
        )}
      </div>
    </div>
  );
}
