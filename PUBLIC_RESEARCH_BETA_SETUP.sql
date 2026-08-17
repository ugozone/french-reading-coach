-- French Reading Coach — Public Research Beta v1.0
-- Run ONCE in Supabase SQL Editor before enabling RESEARCH_MODE.
--
-- Design principles:
--   * Public users receive NO direct read/write policy on research tables.
--   * The Streamlit server writes research records with the service-role key kept in secrets.
--   * Research enrollment stores no name, email, IP address, or raw audio.
--   * Admin export also uses the service-role key stored only in Streamlit secrets.
--   * Beta feedback is operational feedback and is stored separately from research events.

create extension if not exists pgcrypto;

create table if not exists public.research_participants (
    id uuid primary key,
    participant_code text unique not null,
    consent_version text not null,
    consent_given boolean not null default false,
    age_18_or_older boolean not null default false,
    french_level text,
    language_background text,
    enrolled_at timestamptz not null default now()
);

create table if not exists public.research_sessions (
    id uuid primary key,
    participant_id uuid not null references public.research_participants(id) on delete cascade,
    participant_code text not null,
    consent_version text not null,
    app_version text,
    started_at timestamptz not null default now()
);

create table if not exists public.research_events (
    id uuid primary key,
    session_id uuid not null references public.research_sessions(id) on delete cascade,
    participant_id uuid not null references public.research_participants(id) on delete cascade,
    participant_code text not null,
    event_type text not null,
    activity_type text not null,
    metrics jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.beta_feedback (
    id uuid primary key,
    rating integer not null check (rating between 1 and 5),
    category text,
    message text not null,
    research_participant_code text,
    created_at timestamptz not null default now()
);

alter table public.research_participants enable row level security;
alter table public.research_sessions enable row level security;
alter table public.research_events enable row level security;
alter table public.beta_feedback enable row level security;

-- Remove any older public research policies if upgrading from a prior draft.
drop policy if exists "public can insert consented research participants" on public.research_participants;
drop policy if exists "public can insert research sessions" on public.research_sessions;
drop policy if exists "public can insert research events" on public.research_events;
drop policy if exists "public can insert beta feedback" on public.beta_feedback;

-- No public policies are created for research_participants, research_sessions,
-- or research_events. The Streamlit server uses the service-role key for these
-- writes after consent. This reduces direct tampering through the public anon key.

-- Operational beta feedback can be submitted without an account. It is kept in
-- a separate table and public users still cannot SELECT, UPDATE, or DELETE it.
create policy "public can insert beta feedback"
on public.beta_feedback
for insert
to anon, authenticated
with check (rating between 1 and 5 and length(message) > 0);

-- The service-role key bypasses RLS for authorized server-side writes and exports.
