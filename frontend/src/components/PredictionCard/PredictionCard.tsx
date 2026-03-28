import type { GamePrediction } from '../../types';

interface Props {
  prediction: GamePrediction;
}

const STATUS_CONFIG: Record<string, { color: string; bg: string; label: string; dot?: boolean }> = {
  scheduled: { color: '#60a5fa', bg: 'rgba(96,165,250,0.12)', label: 'Today' },
  live:       { color: '#00e87a', bg: 'rgba(0,232,122,0.12)',  label: 'LIVE', dot: true },
  finished:   { color: '#4a6075', bg: 'rgba(74,96,117,0.12)',  label: 'Final' },
};

function TeamAvatar({ name }: { name: string }) {
  const initials = name
    .split(' ')
    .slice(-2)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const hue = name.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360;

  return (
    <div style={{
      width: '48px',
      height: '48px',
      borderRadius: '50%',
      background: `linear-gradient(135deg, hsl(${hue},50%,25%), hsl(${hue},50%,15%))`,
      border: `2px solid hsl(${hue},40%,30%)`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '14px',
      fontWeight: 800,
      color: `hsl(${hue},60%,75%)`,
      flexShrink: 0,
    }}>
      {initials}
    </div>
  );
}

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
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.scheduled;
  const homeWins = predicted_winner === home_team;
  const awayWins = predicted_winner === away_team;

  const formattedDate = new Date(game_date + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
  });

  const barColor = confidencePct >= 70 ? '#00e87a' : confidencePct >= 55 ? '#fbbf24' : '#f87171';

  return (
    <div
      style={{
        background: 'linear-gradient(160deg, #131f2e 0%, #0f1923 100%)',
        border: '1px solid #1e2d40',
        borderRadius: '16px',
        padding: '0',
        overflow: 'hidden',
        boxShadow: '0 4px 32px rgba(0,0,0,0.4)',
        transition: 'transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease',
        animation: 'fadeUp 0.4s ease both',
      }}
      onMouseEnter={(e) => {
        const el = e.currentTarget as HTMLDivElement;
        el.style.transform = 'translateY(-4px)';
        el.style.boxShadow = '0 12px 48px rgba(0,0,0,0.55)';
        el.style.borderColor = '#2d4060';
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLDivElement;
        el.style.transform = 'translateY(0)';
        el.style.boxShadow = '0 4px 32px rgba(0,0,0,0.4)';
        el.style.borderColor = '#1e2d40';
      }}
    >
      {/* Top accent bar */}
      <div style={{
        height: '3px',
        background: `linear-gradient(90deg, ${barColor}88, ${barColor}, ${barColor}44)`,
      }} />

      <div style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: '18px' }}>

        {/* Header: date + status */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ color: '#4a6075', fontSize: '12px', fontWeight: 500 }}>{formattedDate}</span>
          <span style={{
            background: cfg.bg,
            color: cfg.color,
            fontSize: '11px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            padding: '4px 10px',
            borderRadius: '20px',
            border: `1px solid ${cfg.color}33`,
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
          }}>
            {cfg.dot && (
              <span style={{
                width: '6px', height: '6px',
                background: cfg.color,
                borderRadius: '50%',
                animation: 'pulse-glow 1.5s ease-in-out infinite',
                display: 'inline-block',
              }} />
            )}
            {cfg.label}
          </span>
        </div>

        {/* Teams matchup */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto 1fr',
          alignItems: 'center',
          gap: '8px',
        }}>
          {/* Home team */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
            <TeamAvatar name={home_team} />
            <span style={{
              color: homeWins ? '#f0f6ff' : '#8ca3be',
              fontWeight: homeWins ? 700 : 500,
              fontSize: '13px',
              textAlign: 'center',
              lineHeight: 1.3,
            }}>
              {home_team}
            </span>
            <span style={{
              fontSize: '36px',
              fontWeight: 900,
              color: homeWins ? '#00e87a' : '#4a6075',
              letterSpacing: '-0.02em',
              lineHeight: 1,
            }}>
              {predicted_home_score}
            </span>
            <span style={{
              fontSize: '10px',
              color: '#2d4060',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              fontWeight: 600,
            }}>
              Home
            </span>
          </div>

          {/* VS divider */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
            <div style={{
              width: '1px',
              height: '20px',
              background: 'linear-gradient(to bottom, transparent, #2d4060, transparent)',
            }} />
            <span style={{
              color: '#2d4060',
              fontWeight: 800,
              fontSize: '11px',
              letterSpacing: '0.1em',
            }}>
              VS
            </span>
            <div style={{
              width: '1px',
              height: '20px',
              background: 'linear-gradient(to bottom, transparent, #2d4060, transparent)',
            }} />
          </div>

          {/* Away team */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
            <TeamAvatar name={away_team} />
            <span style={{
              color: awayWins ? '#f0f6ff' : '#8ca3be',
              fontWeight: awayWins ? 700 : 500,
              fontSize: '13px',
              textAlign: 'center',
              lineHeight: 1.3,
            }}>
              {away_team}
            </span>
            <span style={{
              fontSize: '36px',
              fontWeight: 900,
              color: awayWins ? '#00e87a' : '#4a6075',
              letterSpacing: '-0.02em',
              lineHeight: 1,
            }}>
              {predicted_away_score}
            </span>
            <span style={{
              fontSize: '10px',
              color: '#2d4060',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              fontWeight: 600,
            }}>
              Away
            </span>
          </div>
        </div>

        {/* Winner pill */}
        <div style={{
          background: 'rgba(0,232,122,0.07)',
          border: '1px solid rgba(0,232,122,0.18)',
          borderRadius: '10px',
          padding: '10px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <span style={{ color: '#4a6075', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>
              Predicted Winner
            </span>
            <span style={{ color: '#00e87a', fontWeight: 800, fontSize: '15px' }}>
              {predicted_winner}
            </span>
          </div>
          <span style={{ fontSize: '20px' }}>🏆</span>
        </div>

        {/* Confidence */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#4a6075', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Confidence
            </span>
            <span style={{
              color: barColor,
              fontWeight: 800,
              fontSize: '14px',
            }}>
              {confidencePct}%
            </span>
          </div>
          <div style={{
            height: '5px',
            background: '#0f1923',
            borderRadius: '3px',
            overflow: 'hidden',
            border: '1px solid #1e2d40',
          }}>
            <div style={{
              height: '100%',
              width: `${confidencePct}%`,
              background: `linear-gradient(90deg, ${barColor}88, ${barColor})`,
              borderRadius: '3px',
              transition: 'width 0.7s cubic-bezier(0.4,0,0.2,1)',
              boxShadow: `0 0 8px ${barColor}66`,
            }} />
          </div>
        </div>

        {/* Divider */}
        <div style={{ height: '1px', background: '#1a2535' }} />

        {/* Reasons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <span style={{
            color: '#2d4060',
            fontSize: '10px',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            fontWeight: 700,
          }}>
            Why we picked this
          </span>
          <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {reasons.map((r, i) => (
              <li key={i} style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
                color: '#8ca3be',
                fontSize: '12.5px',
                lineHeight: 1.55,
              }}>
                <span style={{
                  flexShrink: 0,
                  width: '20px',
                  height: '20px',
                  background: 'rgba(0,232,122,0.08)',
                  border: '1px solid rgba(0,232,122,0.18)',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#00e87a',
                  fontSize: '10px',
                  fontWeight: 800,
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
