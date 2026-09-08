-- 보드게임 아지트 예약. Supabase SQL Editor에서 별도로 한 번 실행합니다.

create table if not exists public.space_admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);

alter table public.space_admins enable row level security;
revoke all on table public.space_admins from public, anon, authenticated;
grant all on table public.space_admins to service_role;

create table if not exists public.space_bookings (
  id uuid primary key default gen_random_uuid(),
  start_at timestamptz not null,
  end_at timestamptz not null,
  status text not null default 'pending'
    check (status in ('pending', 'approved', 'declined', 'done')),
  name text not null check (char_length(name) between 1 and 100),
  contact text not null check (char_length(contact) between 1 and 200),
  party_size integer not null check (party_size between 1 and 50),
  monthly_pass_count integer not null
    check (monthly_pass_count between 1 and party_size),
  monthly_member_name text not null
    check (char_length(monthly_member_name) between 1 and 100),
  parking integer not null default 0 check (parking between 0 and 2),
  games text not null default '' check (char_length(games) <= 500),
  note text not null default '' check (char_length(note) <= 1000),
  needs_night_notice boolean not null default false,
  needs_host boolean not null default false,
  member_verified boolean not null default false,
  host_confirmed boolean not null default false,
  parking_confirmed boolean not null default false,
  created_at timestamptz not null default now(),
  check (start_at < end_at),
  check (end_at <= start_at + interval '24 hours')
);

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'space_bookings_no_active_overlap'
      and conrelid = 'public.space_bookings'::regclass
  ) then
    alter table public.space_bookings
      add constraint space_bookings_no_active_overlap
      exclude using gist (
        tstzrange(start_at, end_at, '[)') with &&
      ) where (status in ('pending', 'approved'));
  end if;
end
$$;

create index if not exists space_bookings_start_at_idx
  on public.space_bookings (start_at);
create index if not exists space_bookings_created_at_idx
  on public.space_bookings (created_at desc);

alter table public.space_bookings enable row level security;
revoke all on table public.space_bookings from anon, authenticated;
grant all on table public.space_bookings to service_role;

create or replace function public.broadcast_azit_availability()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  begin
    perform realtime.send(
      '{"changed":true}'::jsonb,
      'booking_changed',
      'azit-availability',
      false
    );
  exception when others then
    raise warning 'azit realtime broadcast failed: %', sqlerrm;
  end;
  if tg_op = 'DELETE' then
    return old;
  end if;
  return new;
end;
$$;

revoke all on function public.broadcast_azit_availability() from public, anon, authenticated;
grant execute on function public.broadcast_azit_availability() to service_role;

drop trigger if exists broadcast_azit_availability on public.space_bookings;
create trigger broadcast_azit_availability
  after insert or update or delete on public.space_bookings
  for each row execute function public.broadcast_azit_availability();
