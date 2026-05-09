-- F1 prediction tables
-- Run once against your Supabase project before deploying the F1 backend.

-- Stores the predicted winner for each race at prediction time.
-- Populated automatically when GET /f1/races/{id}/predictions is called.
create table if not exists f1_predictions (
    race_id             text primary key,
    event               text not null,
    season              integer not null,
    round               integer not null,
    circuit_key         text not null default '',
    circuit_variance    text not null default 'normal',
    predicted_winner    text not null,
    predicted_winner_id text not null,
    win_prob            real not null,
    confidence_score    real not null,
    model_version       text not null default '',
    timestamp           timestamptz not null default now()
);

-- Stores post-race accuracy results after each race is resolved.
-- Populated by resolve_f1_accuracy() which runs at startup and nightly.
create table if not exists f1_accuracy_log (
    race_id             text primary key,
    event               text not null default '',
    season              integer,
    circuit_key         text not null default '',
    circuit_variance    text not null default 'normal',
    race_date           date,
    winner_correct      boolean not null default false,
    podium_correct      integer not null default 0,  -- 0–3 podium positions correct
    confidence_score    real not null default 0,
    model_version       text not null default '',
    rank_correlation    real,                         -- Spearman rho, null if unavailable
    resolved_at         timestamptz not null default now()
);

-- Indexes for common query patterns
create index if not exists f1_predictions_season_idx on f1_predictions (season);
create index if not exists f1_accuracy_log_season_idx on f1_accuracy_log (season);
create index if not exists f1_accuracy_log_date_idx on f1_accuracy_log (race_date desc);
