import { AccuracyStats } from '../../types';

interface Props {
  stats: AccuracyStats;
}

export function AccuracyBanner({ stats }: Props) {
  const { total_predictions, correct_predictions, accuracy_percentage, last_updated } = stats;

  const formattedDate = new Date(last_updated).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  const pct = total_predictions > 0 ? accuracy_percentage : null;
  const displayPct = pct !== null ? `${pct.toFixed(1)}%` : '—';

  const barColor =
    pct === null ? '#475569' : pct >= 65 ? '#4ade80' : pct >= 50 ? '#facc15' : '#f87171';

  return (
    <div
      style={{
        background: 'linear-gradient(135deg, #0f2027 0%, #1a2f42 50%, #0f2027 100%)',
        border: '1px solid #2d3f55',
        borderRadius: '14px',
        padding: '28px 32px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px',
        boxShadow: '0 2px 16px rgba(0,0,0,0.4)',
      }}
    >
      {/* Top row */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'space-between',
          alignItems: 'flex-end',
          gap: '16px',
        }}
      >
        {/* Left: headline */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <span
            style={{
              color: '#64748b',
              fontSize: '12px',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              fontWeight: 600,
            }}
          >
            Season Record
          </span>
          <h2 style={{ margin: 0, fontSize: '22px', fontWeight: 800, color: '#f1f5f9', lineHeight: 1.2 }}>
            Our NBA Predictions are{' '}
            <span
              style={{
                color: barColor,
                fontSize: '28px',
              }}
            >
              {displayPct}
            </span>{' '}
            accurate this season
          </h2>
        </div>

        {/* Right: stats pills */}
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <div
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid #2d3f55',
              borderRadius: '8px',
              padding: '10px 16px',
              textAlign: 'center',
              minWidth: '80px',
            }}
          >
            <div style={{ color: '#4ade80', fontSize: '22px', fontWeight: 800 }}>{correct_predictions}</div>
            <div style={{ color: '#64748b', fontSize: '11px', marginTop: '2px' }}>Correct</div>
          </div>
          <div
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid #2d3f55',
              borderRadius: '8px',
              padding: '10px 16px',
              textAlign: 'center',
              minWidth: '80px',
            }}
          >
            <div style={{ color: '#e2e8f0', fontSize: '22px', fontWeight: 800 }}>{total_predictions}</div>
            <div style={{ color: '#64748b', fontSize: '11px', marginTop: '2px' }}>Total</div>
          </div>
        </div>
      </div>

      {/* Accuracy bar */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div
          style={{
            height: '10px',
            background: '#1e293b',
            borderRadius: '5px',
            overflow: 'hidden',
            border: '1px solid #2d3f55',
          }}
        >
          <div
            style={{
              height: '100%',
              width: total_predictions > 0 ? `${Math.min(100, accuracy_percentage)}%` : '0%',
              background: `linear-gradient(90deg, ${barColor}aa, ${barColor})`,
              borderRadius: '5px',
              transition: 'width 0.8s ease',
            }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: '#475569', fontSize: '11px' }}>0%</span>
          <span style={{ color: '#475569', fontSize: '11px' }}>Last updated: {formattedDate}</span>
          <span style={{ color: '#475569', fontSize: '11px' }}>100%</span>
        </div>
      </div>

      {/* Empty state notice */}
      {total_predictions === 0 && (
        <p style={{ margin: 0, color: '#475569', fontSize: '13px', fontStyle: 'italic' }}>
          No predictions have been tracked yet. Accuracy will appear here as games complete.
        </p>
      )}
    </div>
  );
}
