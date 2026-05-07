import type { AccuracyStats } from '../../types';

interface Props {
  stats: AccuracyStats;
}

export function AccuracyBanner({ stats }: Props) {
  const { total_predictions, correct_predictions, accuracy_percentage, last_updated, model_cv_accuracy, model_version } = stats;

  const pct = total_predictions > 0 ? accuracy_percentage : null;
  const displayPct = pct !== null ? `${pct.toFixed(1)}%` : '—';
  const barColor = pct === null ? '#4a6075' : pct >= 65 ? '#00e87a' : pct >= 50 ? '#fbbf24' : '#f87171';
  const wrong = total_predictions - correct_predictions;
  const isML = model_version === 'xgboost-v1';

  const formattedDate = new Date(last_updated).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });

  return (
    <div
      id="accuracy"
      style={{
        background: 'linear-gradient(135deg, #0c1a2a 0%, #111f30 50%, #0c1a2a 100%)',
        border: '1px solid #1e2d40',
        borderRadius: '16px',
        padding: '28px 32px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Background glow */}
      <div style={{
        position: 'absolute',
        top: '-60px',
        right: '-40px',
        width: '220px',
        height: '220px',
        background: `radial-gradient(circle, ${barColor}18 0%, transparent 70%)`,
        pointerEvents: 'none',
      }} />

      {/* Header row */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        gap: '20px',
        position: 'relative',
      }}>
        {/* Left */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '6px', height: '6px',
              background: barColor,
              borderRadius: '50%',
              boxShadow: `0 0 8px ${barColor}`,
            }} />
            <span style={{
              color: '#4a6075',
              fontSize: '11px',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              fontWeight: 700,
            }}>
              Model Accuracy · {formattedDate}
            </span>
          </div>
          <h2 style={{
            margin: 0,
            fontSize: '22px',
            fontWeight: 900,
            color: '#f0f6ff',
            lineHeight: 1.2,
          }}>
            Our NBA predictions are{' '}
            <span style={{
              color: barColor,
              fontSize: '30px',
              letterSpacing: '-0.02em',
            }}>
              {displayPct}
            </span>{' '}
            accurate this season
          </h2>
        </div>

        {/* Right: stat pills */}
        <div style={{ display: 'flex', gap: '10px', flexShrink: 0 }}>
          <div style={{
            background: 'rgba(0,232,122,0.07)',
            border: '1px solid rgba(0,232,122,0.18)',
            borderRadius: '10px',
            padding: '12px 18px',
            textAlign: 'center',
            minWidth: '72px',
          }}>
            <div style={{ color: '#00e87a', fontSize: '24px', fontWeight: 900, lineHeight: 1 }}>
              {correct_predictions}
            </div>
            <div style={{ color: '#4a6075', fontSize: '11px', marginTop: '4px', fontWeight: 600 }}>Correct</div>
          </div>
          <div style={{
            background: 'rgba(248,113,113,0.07)',
            border: '1px solid rgba(248,113,113,0.15)',
            borderRadius: '10px',
            padding: '12px 18px',
            textAlign: 'center',
            minWidth: '72px',
          }}>
            <div style={{ color: '#f87171', fontSize: '24px', fontWeight: 900, lineHeight: 1 }}>
              {wrong}
            </div>
            <div style={{ color: '#4a6075', fontSize: '11px', marginTop: '4px', fontWeight: 600 }}>Wrong</div>
          </div>
          <div style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid #1e2d40',
            borderRadius: '10px',
            padding: '12px 18px',
            textAlign: 'center',
            minWidth: '72px',
          }}>
            <div style={{ color: '#f0f6ff', fontSize: '24px', fontWeight: 900, lineHeight: 1 }}>
              {total_predictions}
            </div>
            <div style={{ color: '#4a6075', fontSize: '11px', marginTop: '4px', fontWeight: 600 }}>Total</div>
          </div>
        </div>
      </div>

      {/* Accuracy bar */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', position: 'relative' }}>
        <div style={{
          height: '8px',
          background: '#0c1520',
          borderRadius: '4px',
          overflow: 'hidden',
          border: '1px solid #1e2d40',
        }}>
          <div style={{
            height: '100%',
            width: total_predictions > 0 ? `${Math.min(100, accuracy_percentage)}%` : '0%',
            background: `linear-gradient(90deg, ${barColor}77, ${barColor})`,
            borderRadius: '4px',
            transition: 'width 1s cubic-bezier(0.4,0,0.2,1)',
            boxShadow: `0 0 12px ${barColor}55`,
          }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: '#2d4060', fontSize: '11px' }}>0%</span>
          <span style={{ color: '#2d4060', fontSize: '11px' }}>100%</span>
        </div>
      </div>

      {/* Model info row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap', position: 'relative' }}>
        <span style={{
          background: isML ? 'rgba(0,232,122,0.08)' : 'rgba(74,96,117,0.15)',
          border: `1px solid ${isML ? 'rgba(0,232,122,0.2)' : '#1e2d40'}`,
          borderRadius: '6px', padding: '4px 10px',
          fontSize: '11px', fontWeight: 700,
          color: isML ? '#00e87a' : '#4a6075',
          letterSpacing: '0.05em',
        }}>
          {isML ? 'XGBoost v1' : 'Rule-based fallback'}
        </span>
        {model_cv_accuracy != null && (
          <span style={{ color: '#4a6075', fontSize: '12px' }}>
            Cross-validated training accuracy:{' '}
            <span style={{ color: '#8ca3be', fontWeight: 700 }}>
              {(model_cv_accuracy * 100).toFixed(1)}%
            </span>
            {' '}(3 seasons, ~3 700 games)
          </span>
        )}
        {!isML && (
          <span style={{ color: '#2d4060', fontSize: '12px', fontStyle: 'italic' }}>
            Model training in progress — predictions use heuristic until ready.
          </span>
        )}
      </div>

      {total_predictions === 0 && (
        <p style={{
          margin: 0,
          color: '#2d4060',
          fontSize: '13px',
          fontStyle: 'italic',
          position: 'relative',
        }}>
          No predictions tracked yet. Accuracy updates automatically as games finish.
        </p>
      )}
    </div>
  );
}
