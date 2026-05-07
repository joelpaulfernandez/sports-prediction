import type { GamePrediction, TeamStats } from '../../types';

interface Props {
  prediction: GamePrediction;
}

const STATUS_CONFIG: Record<string, { color: string; bg: string; dot?: boolean }> = {
  scheduled: { color: '#60a5fa', bg: 'rgba(96,165,250,0.12)' },
  live:       { color: '#00e87a', bg: 'rgba(0,232,122,0.12)', dot: true },
  finished:   { color: '#4a6075', bg: 'rgba(74,96,117,0.12)' },
};

function formatGameTime(game_time_utc: string | null | undefined, status: string): string {
  if (status === 'live') return 'LIVE';
  if (status === 'finished') return 'Final';
  if (!game_time_utc) return 'Today';
  try {
    return new Date(game_time_utc).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  } catch {
    return 'Today';
  }
}

function TeamAvatarWithFallback({ teamId, name }: { teamId?: number | null; name: string }) {
  const initials = name.split(' ').slice(-2).map((w) => w[0]).join('').toUpperCase().slice(0, 2);
  const hue = name.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360;
  return (
    <div style={{ position: 'relative', width: '56px', height: '56px', flexShrink: 0 }}>
      {teamId && (
        <img
          src={`https://cdn.nba.com/logos/nba/${teamId}/global/L/logo.svg`}
          alt={name}
          width={56}
          height={56}
          style={{ objectFit: 'contain', display: 'block' }}
          onError={(e) => {
            const img = e.currentTarget;
            img.style.display = 'none';
            const next = img.nextElementSibling as HTMLElement | null;
            if (next) next.style.display = 'flex';
          }}
        />
      )}
      <div style={{
        width: '56px', height: '56px', borderRadius: '50%',
        background: `linear-gradient(135deg, hsl(${hue},50%,25%), hsl(${hue},50%,15%))`,
        border: `2px solid hsl(${hue},40%,30%)`,
        display: teamId ? 'none' : 'flex',
        alignItems: 'center', justifyContent: 'center',
        fontSize: '15px', fontWeight: 800, color: `hsl(${hue},60%,75%)`,
        position: teamId ? 'absolute' : 'relative', top: 0, left: 0,
      }}>
        {initials}
      </div>
    </div>
  );
}

// ── Compact stat comparison row ──────────────────────────────────────────────

interface StatRowProps {
  label: string;
  homeVal: string;
  awayVal: string;
  homeWins?: boolean;  // true = highlight home, false = highlight away, undefined = neutral
}

function StatRow({ label, homeVal, awayVal, homeWins }: StatRowProps) {
  const homeColor = homeWins === true ? '#00e87a' : homeWins === false ? '#8ca3be' : '#c8d8ea';
  const awayColor = homeWins === false ? '#00e87a' : homeWins === true ? '#8ca3be' : '#c8d8ea';
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr auto 1fr',
      alignItems: 'center',
      gap: '6px',
      padding: '4px 0',
    }}>
      <span style={{ color: homeColor, fontWeight: homeWins === true ? 700 : 500, fontSize: '12px', textAlign: 'right' }}>
        {homeVal}
      </span>
      <span style={{ color: '#2d4060', fontSize: '10px', fontWeight: 600, textAlign: 'center', minWidth: '70px', letterSpacing: '0.04em' }}>
        {label}
      </span>
      <span style={{ color: awayColor, fontWeight: homeWins === false ? 700 : 500, fontSize: '12px', textAlign: 'left' }}>
        {awayVal}
      </span>
    </div>
  );
}

function StatsGrid({ home, away }: { home: TeamStats; away: TeamStats }) {
  const fmt = (n: number, decimals = 1) => n.toFixed(decimals);
  const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

  return (
    <div style={{
      background: 'rgba(255,255,255,0.02)',
      border: '1px solid #1a2535',
      borderRadius: '10px',
      padding: '12px 14px',
      display: 'flex',
      flexDirection: 'column',
      gap: '2px',
    }}>
      {/* Column headers */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr auto 1fr',
        gap: '6px',
        marginBottom: '6px',
      }}>
        <span style={{ color: '#00e87a', fontSize: '10px', fontWeight: 700, textAlign: 'right', letterSpacing: '0.06em' }}>HOME</span>
        <span style={{ color: '#2d4060', fontSize: '10px', fontWeight: 700, textAlign: 'center', minWidth: '70px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Key Stats</span>
        <span style={{ color: '#60a5fa', fontSize: '10px', fontWeight: 700, textAlign: 'left', letterSpacing: '0.06em' }}>AWAY</span>
      </div>

      <StatRow
        label="Net Rating"
        homeVal={home.net_rating >= 0 ? `+${fmt(home.net_rating)}` : fmt(home.net_rating)}
        awayVal={away.net_rating >= 0 ? `+${fmt(away.net_rating)}` : fmt(away.net_rating)}
        homeWins={Math.abs(home.net_rating - away.net_rating) > 0.3 ? home.net_rating > away.net_rating : undefined}
      />
      <StatRow
        label="Elo Rating"
        homeVal={home.elo.toFixed(0)}
        awayVal={away.elo.toFixed(0)}
        homeWins={Math.abs(home.elo - away.elo) > 10 ? home.elo > away.elo : undefined}
      />
      <StatRow
        label="Last 10 W%"
        homeVal={pct(home.recent_win_pct)}
        awayVal={pct(away.recent_win_pct)}
        homeWins={Math.abs(home.recent_win_pct - away.recent_win_pct) > 0.05 ? home.recent_win_pct > away.recent_win_pct : undefined}
      />
      <StatRow
        label="eFG%"
        homeVal={pct(home.efg_pct)}
        awayVal={pct(away.efg_pct)}
        homeWins={Math.abs(home.efg_pct - away.efg_pct) > 0.005 ? home.efg_pct > away.efg_pct : undefined}
      />
      <StatRow
        label="TOV%"
        homeVal={`${fmt(home.tov_pct)}%`}
        awayVal={`${fmt(away.tov_pct)}%`}
        homeWins={Math.abs(home.tov_pct - away.tov_pct) > 0.3 ? home.tov_pct < away.tov_pct : undefined}
      />
      <StatRow
        label="Rest Days"
        homeVal={`${home.rest_days}d`}
        awayVal={`${away.rest_days}d`}
        homeWins={home.rest_days !== away.rest_days ? home.rest_days > away.rest_days : undefined}
      />
    </div>
  );
}

// ── Model badge ──────────────────────────────────────────────────────────────

function ModelBadge({ version }: { version?: string }) {
  const isML = version === 'xgboost-v1';
  return (
    <span style={{
      background: isML ? 'rgba(0,232,122,0.08)' : 'rgba(74,96,117,0.15)',
      border: `1px solid ${isML ? 'rgba(0,232,122,0.2)' : '#1e2d40'}`,
      borderRadius: '4px',
      padding: '2px 7px',
      fontSize: '10px',
      fontWeight: 700,
      color: isML ? '#00e87a' : '#4a6075',
      letterSpacing: '0.05em',
    }}>
      {isML ? 'XGBoost' : 'Rule-based'}
    </span>
  );
}

// ── Main card ────────────────────────────────────────────────────────────────

export function PredictionCard({ prediction }: Props) {
  const {
    home_team, away_team, home_team_id, away_team_id, predicted_winner, confidence,
    predicted_home_score, predicted_away_score, reasons,
    game_date, status, home_pts, away_pts, game_time_utc, home_stats, away_stats, model_version,
  } = prediction;

  const hasActualScore = (status === 'live' || status === 'finished') &&
    home_pts != null && away_pts != null;

  const confidencePct = Math.round(confidence * 100);
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.scheduled;
  const timeLabel = formatGameTime(game_time_utc, status);
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
      <div style={{ height: '3px', background: `linear-gradient(90deg, ${barColor}88, ${barColor}, ${barColor}44)` }} />

      <div style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

        {/* Header: date + status + model badge */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: '#4a6075', fontSize: '12px', fontWeight: 500 }}>{formattedDate}</span>
            <ModelBadge version={model_version} />
          </div>
          <span style={{
            background: cfg.bg, color: cfg.color,
            fontSize: '11px', fontWeight: 700, letterSpacing: '0.04em',
            textTransform: status === 'scheduled' ? 'none' : 'uppercase',
            padding: '4px 10px', borderRadius: '20px', border: `1px solid ${cfg.color}33`,
            display: 'flex', alignItems: 'center', gap: '5px',
          }}>
            {cfg.dot && (
              <span style={{
                width: '6px', height: '6px', background: cfg.color, borderRadius: '50%',
                animation: 'pulse-glow 1.5s ease-in-out infinite', display: 'inline-block',
              }} />
            )}
            {timeLabel}
          </span>
        </div>

        {/* Teams matchup */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center', gap: '8px' }}>
          {/* Home */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
            <TeamAvatarWithFallback teamId={home_team_id} name={home_team} />
            <span style={{ color: homeWins ? '#f0f6ff' : '#8ca3be', fontWeight: homeWins ? 700 : 500, fontSize: '13px', textAlign: 'center', lineHeight: 1.3 }}>
              {home_team}
            </span>
            {hasActualScore ? (
              <>
                <span style={{ fontSize: '34px', fontWeight: 900, color: home_pts! > away_pts! ? '#00e87a' : '#4a6075', letterSpacing: '-0.02em', lineHeight: 1 }}>
                  {home_pts}
                </span>
                <span style={{ fontSize: '10px', color: '#2d4060', fontWeight: 600 }}>
                  pred. {predicted_home_score}
                </span>
              </>
            ) : (
              <span style={{ fontSize: '34px', fontWeight: 900, color: homeWins ? '#00e87a' : '#4a6075', letterSpacing: '-0.02em', lineHeight: 1 }}>
                {predicted_home_score}
              </span>
            )}
            <span style={{ fontSize: '10px', color: '#2d4060', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Home</span>
          </div>

          {/* VS / Score divider */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
            <div style={{ width: '1px', height: '20px', background: 'linear-gradient(to bottom, transparent, #2d4060, transparent)' }} />
            <span style={{ color: '#2d4060', fontWeight: 800, fontSize: '11px', letterSpacing: '0.1em' }}>
              {hasActualScore ? (status === 'live' ? 'LIVE' : 'FINAL') : 'VS'}
            </span>
            <div style={{ width: '1px', height: '20px', background: 'linear-gradient(to bottom, transparent, #2d4060, transparent)' }} />
          </div>

          {/* Away */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
            <TeamAvatarWithFallback teamId={away_team_id} name={away_team} />
            <span style={{ color: awayWins ? '#f0f6ff' : '#8ca3be', fontWeight: awayWins ? 700 : 500, fontSize: '13px', textAlign: 'center', lineHeight: 1.3 }}>
              {away_team}
            </span>
            {hasActualScore ? (
              <>
                <span style={{ fontSize: '34px', fontWeight: 900, color: away_pts! > home_pts! ? '#00e87a' : '#4a6075', letterSpacing: '-0.02em', lineHeight: 1 }}>
                  {away_pts}
                </span>
                <span style={{ fontSize: '10px', color: '#2d4060', fontWeight: 600 }}>
                  pred. {predicted_away_score}
                </span>
              </>
            ) : (
              <span style={{ fontSize: '34px', fontWeight: 900, color: awayWins ? '#00e87a' : '#4a6075', letterSpacing: '-0.02em', lineHeight: 1 }}>
                {predicted_away_score}
              </span>
            )}
            <span style={{ fontSize: '10px', color: '#2d4060', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Away</span>
          </div>
        </div>

        {/* Winner pill */}
        <div style={{
          background: 'rgba(0,232,122,0.07)', border: '1px solid rgba(0,232,122,0.18)',
          borderRadius: '10px', padding: '10px 16px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <span style={{ color: '#4a6075', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Predicted Winner</span>
            <span style={{ color: '#00e87a', fontWeight: 800, fontSize: '15px' }}>{predicted_winner}</span>
          </div>
          <span style={{ fontSize: '20px' }}>🏆</span>
        </div>

        {/* Confidence bar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#4a6075', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Model Confidence
            </span>
            <span style={{ color: barColor, fontWeight: 800, fontSize: '14px' }}>{confidencePct}%</span>
          </div>
          <div style={{ height: '5px', background: '#0f1923', borderRadius: '3px', overflow: 'hidden', border: '1px solid #1e2d40' }}>
            <div style={{
              height: '100%', width: `${confidencePct}%`,
              background: `linear-gradient(90deg, ${barColor}88, ${barColor})`,
              borderRadius: '3px', transition: 'width 0.7s cubic-bezier(0.4,0,0.2,1)',
              boxShadow: `0 0 8px ${barColor}66`,
            }} />
          </div>
        </div>

        {/* Stats comparison grid (only when advanced stats are available) */}
        {home_stats && away_stats && (
          <StatsGrid home={home_stats} away={away_stats} />
        )}

        {/* Divider */}
        <div style={{ height: '1px', background: '#1a2535' }} />

        {/* AI Reasons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <span style={{ color: '#2d4060', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 700 }}>
            Why we picked this
          </span>
          <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {reasons.map((r, i) => (
              <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', color: '#8ca3be', fontSize: '12.5px', lineHeight: 1.55 }}>
                <span style={{
                  flexShrink: 0, width: '20px', height: '20px',
                  background: 'rgba(0,232,122,0.08)', border: '1px solid rgba(0,232,122,0.18)',
                  borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#00e87a', fontSize: '10px', fontWeight: 800, marginTop: '1px',
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
