import { GamePrediction } from '../../types';

interface Props {
  prediction: GamePrediction;
}

const STATUS_COLORS: Record<string, string> = {
  scheduled: '#3b82f6',
  live: '#22c55e',
  finished: '#6b7280',
};

const STATUS_LABELS: Record<string, string> = {
  scheduled: 'Scheduled',
  live: 'LIVE',
  finished: 'Final',
};

export function PredictionCard({ prediction }: Props) {
  const {
    home_team,
    away_team,
    predicted_winner,
    confidence,
    predicted_home_score,
    predicted_away_score,
    reasons,
    game_date,
    status,
  } = prediction;

  const confidencePct = Math.round(confidence * 100);
  const statusColor = STATUS_COLORS[status] ?? '#6b7280';
  const statusLabel = STATUS_LABELS[status] ?? status;

  const formattedDate = new Date(game_date + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });

  return (
    <div
      style={{
        background: 'linear-gradient(135deg, #1e2a3a 0%, #16202e 100%)',
        border: '1px solid #2d3f55',
        borderRadius: '12px',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '18px',
        boxShadow: '0 4px 24px rgba(0,0,0,0.35)',
        transition: 'transform 0.15s ease, box-shadow 0.15s ease',
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-3px)';
        (e.currentTarget as HTMLDivElement).style.boxShadow = '0 8px 32px rgba(0,0,0,0.45)';
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
        (e.currentTarget as HTMLDivElement).style.boxShadow = '0 4px 24px rgba(0,0,0,0.35)';
      }}
    >
      {/* Header row: date + status badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ color: '#94a3b8', fontSize: '13px' }}>{formattedDate}</span>
        <span
          style={{
            background: statusColor,
            color: '#fff',
            fontSize: '11px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            padding: '3px 10px',
            borderRadius: '20px',
          }}
        >
          {statusLabel}
        </span>
      </div>

      {/* Teams & predicted scores */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto 1fr',
          alignItems: 'center',
          gap: '12px',
          textAlign: 'center',
        }}
      >
        {/* Home team */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <span
            style={{
              color: predicted_winner === home_team ? '#4ade80' : '#cbd5e1',
              fontWeight: predicted_winner === home_team ? 700 : 500,
              fontSize: '15px',
              lineHeight: 1.3,
            }}
          >
            {home_team}
          </span>
          <span
            style={{
              fontSize: '28px',
              fontWeight: 800,
              color: predicted_winner === home_team ? '#4ade80' : '#94a3b8',
            }}
          >
            {predicted_home_score}
          </span>
          <span style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Home
          </span>
        </div>

        {/* VS divider */}
        <span style={{ color: '#475569', fontWeight: 700, fontSize: '14px' }}>VS</span>

        {/* Away team */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <span
            style={{
              color: predicted_winner === away_team ? '#4ade80' : '#cbd5e1',
              fontWeight: predicted_winner === away_team ? 700 : 500,
              fontSize: '15px',
              lineHeight: 1.3,
            }}
          >
            {away_team}
          </span>
          <span
            style={{
              fontSize: '28px',
              fontWeight: 800,
              color: predicted_winner === away_team ? '#4ade80' : '#94a3b8',
            }}
          >
            {predicted_away_score}
          </span>
          <span style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Away
          </span>
        </div>
      </div>

      {/* Predicted winner */}
      <div
        style={{
          background: 'rgba(74, 222, 128, 0.08)',
          border: '1px solid rgba(74, 222, 128, 0.2)',
          borderRadius: '8px',
          padding: '10px 14px',
          textAlign: 'center',
        }}
      >
        <span style={{ color: '#94a3b8', fontSize: '12px' }}>Predicted Winner · </span>
        <span style={{ color: '#4ade80', fontWeight: 700, fontSize: '14px' }}>{predicted_winner}</span>
      </div>

      {/* Confidence bar */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ color: '#94a3b8', fontSize: '12px' }}>Confidence</span>
          <span style={{ color: '#e2e8f0', fontWeight: 700, fontSize: '13px' }}>{confidencePct}%</span>
        </div>
        <div
          style={{
            height: '6px',
            background: '#1e3a2f',
            borderRadius: '3px',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${confidencePct}%`,
              background: confidencePct >= 70 ? '#4ade80' : confidencePct >= 55 ? '#facc15' : '#f87171',
              borderRadius: '3px',
              transition: 'width 0.6s ease',
            }}
          />
        </div>
      </div>

      {/* Reasons */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <span
          style={{
            color: '#64748b',
            fontSize: '11px',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            fontWeight: 600,
          }}
        >
          Why we picked this
        </span>
        <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {reasons.map((r, i) => (
            <li
              key={i}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '8px',
                color: '#94a3b8',
                fontSize: '13px',
                lineHeight: 1.5,
              }}
            >
              <span
                style={{
                  flexShrink: 0,
                  width: '18px',
                  height: '18px',
                  background: 'rgba(74, 222, 128, 0.12)',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#4ade80',
                  fontSize: '10px',
                  fontWeight: 700,
                  marginTop: '1px',
                }}
              >
                {i + 1}
              </span>
              {r.text}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
