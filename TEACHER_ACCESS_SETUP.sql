-- JamiSpeak French: secure teacher-access workflow
-- Run this once in Supabase SQL Editor.
--
-- Public visitors may submit a REQUEST only.
-- They cannot activate themselves as teachers.

create table if not exists public.teacher_access_requests (
    id uuid primary key default gen_random_uuid(),
    full_name text not null,
    email text not null unique,
    institution text,
    message text,
    status text not null default 'pending' check (status in ('pending', 'approved', 'declined')),
    created_at timestamptz not null default now(),
    reviewed_at timestamptz,
    reviewed_by text
);

alter table public.teacher_access_requests enable row level security;

-- Allow a visitor to create a pending request only.
drop policy if exists "public can submit pending teacher requests" on public.teacher_access_requests;
create policy "public can submit pending teacher requests"
on public.teacher_access_requests
for insert
to anon, authenticated
with check (status = 'pending');

-- No public SELECT/UPDATE/DELETE policy is intentionally created.
-- Review requests in the Supabase dashboard with an administrator/service role.

-- Make sure the approved-teacher table has the fields used by the app.
create table if not exists public.teacher_access (
    id uuid primary key default gen_random_uuid(),
    teacher_name text,
    full_name text,
    email text unique not null,
    role text not null default 'teacher',
    is_active boolean not null default false,
    invite_status text not null default 'pending',
    invited_by text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.teacher_access add column if not exists teacher_name text;
alter table public.teacher_access add column if not exists full_name text;
alter table public.teacher_access add column if not exists email text;
alter table public.teacher_access add column if not exists role text default 'teacher';
alter table public.teacher_access add column if not exists is_active boolean default false;
alter table public.teacher_access add column if not exists invite_status text default 'pending';
alter table public.teacher_access add column if not exists invited_by text;
alter table public.teacher_access add column if not exists created_at timestamptz default now();
alter table public.teacher_access add column if not exists updated_at timestamptz default now();

-- Required for one approved row per teacher email.
create unique index if not exists teacher_access_email_unique_idx
on public.teacher_access(email);

alter table public.teacher_access enable row level security;

-- Approved authenticated teachers may read only their own access record.
drop policy if exists "teachers can read own access record" on public.teacher_access;
create policy "teachers can read own access record"
on public.teacher_access
for select
to authenticated
using (lower(email) = lower(coalesce(auth.jwt() ->> 'email', '')));

-- IMPORTANT: no anon/authenticated INSERT or UPDATE policy is created for teacher_access.
-- Add/approve teachers only from the Supabase dashboard or a trusted server-side admin process.
