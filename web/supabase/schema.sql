-- 보드게임 컬렉션 — 스키마
--
-- Supabase SQL Editor에 그대로 붙여넣고 실행하세요. 여러 번 실행해도 안전합니다.

-- ============================================================
-- 1. 대여 예약 / 모임 요청
-- ============================================================

create table if not exists public.requests (
  id          uuid primary key default gen_random_uuid(),
  type        text not null check (type in ('rental', 'meetup')),
  name        text not null,
  contact     text not null,
  payload     jsonb not null default '{}'::jsonb,
  status      text not null default 'pending'
              check (status in ('pending', 'approved', 'declined', 'done')),
  created_at  timestamptz not null default now()
);

create index if not exists requests_created_at_idx
  on public.requests (created_at desc);

-- RLS를 켜두고 정책을 만들지 않으면 anon 키로는 아무것도 못 읽습니다.
-- 서버(service role 키)만 접근하므로 이게 의도된 상태입니다.
-- 연락처가 공개로 새어나가지 않게 하는 안전장치이기도 합니다.
alter table public.requests enable row level security;


-- ============================================================
-- 2. 프로필 — 구글 로그인한 사용자
-- ============================================================

create table if not exists public.profiles (
  id          uuid primary key references auth.users on delete cascade,
  email       text,
  name        text,
  avatar_url  text,
  is_admin    boolean not null default false,
  created_at  timestamptz not null default now()
);

alter table public.profiles enable row level security;

-- 로그인한 사람은 서로의 이름/아바타를 볼 수 있어야 랭킹보드가 성립합니다.
drop policy if exists "profiles are visible to signed-in users" on public.profiles;
create policy "profiles are visible to signed-in users"
  on public.profiles for select
  to authenticated
  using (true);

drop policy if exists "users can update their own profile" on public.profiles;
create policy "users can update their own profile"
  on public.profiles for update
  to authenticated
  using (auth.uid() = id);

-- 구글로 처음 로그인하면 프로필이 자동으로 생깁니다.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, name, avatar_url)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', new.email),
    new.raw_user_meta_data->>'avatar_url'
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();


-- ============================================================
-- 3. 플레이 기록 + 결과 (랭킹보드의 원천)
-- ============================================================

create table if not exists public.plays (
  id          uuid primary key default gen_random_uuid(),
  -- 기록을 올린 사람. 삭제해도 기록은 남깁니다.
  user_id     uuid references auth.users on delete set null,
  -- games.json의 보드라이프 id. 게임 목록은 앱이 들고 있으므로 FK는 없습니다.
  game_id     text not null,
  game_name   text not null,
  played_on   date not null,
  duration    integer,
  note        text not null default '',
  created_at  timestamptz not null default now()
);

create index if not exists plays_game_idx on public.plays (game_id);
create index if not exists plays_played_on_idx on public.plays (played_on desc);

create table if not exists public.play_results (
  id           uuid primary key default gen_random_uuid(),
  play_id      uuid not null references public.plays on delete cascade,
  -- 계정이 없는 사람도 기록되므로 이름은 자유 텍스트입니다.
  player_name  text not null,
  -- 계정이 있는 참가자는 연결해 두면 랭킹에 본인으로 잡힙니다.
  player_id    uuid references auth.users on delete set null,
  score        integer,
  -- 1등이 1. 동점이면 같은 값을 넣어도 됩니다.
  rank         integer not null,
  created_at   timestamptz not null default now()
);

create index if not exists play_results_play_idx on public.play_results (play_id);
create index if not exists play_results_name_idx on public.play_results (player_name);

alter table public.plays enable row level security;
alter table public.play_results enable row level security;

-- 랭킹보드는 로그인한 사람만 봅니다.
drop policy if exists "plays are visible to signed-in users" on public.plays;
create policy "plays are visible to signed-in users"
  on public.plays for select to authenticated using (true);

drop policy if exists "signed-in users can log plays" on public.plays;
create policy "signed-in users can log plays"
  on public.plays for insert to authenticated with check (auth.uid() = user_id);

drop policy if exists "users can edit their own plays" on public.plays;
create policy "users can edit their own plays"
  on public.plays for update to authenticated using (auth.uid() = user_id);

drop policy if exists "users can delete their own plays" on public.plays;
create policy "users can delete their own plays"
  on public.plays for delete to authenticated using (auth.uid() = user_id);

drop policy if exists "results are visible to signed-in users" on public.play_results;
create policy "results are visible to signed-in users"
  on public.play_results for select to authenticated using (true);

-- 결과 행은 그 판을 올린 사람만 건드릴 수 있습니다.
drop policy if exists "play owner can write results" on public.play_results;
create policy "play owner can write results"
  on public.play_results for all to authenticated
  using (exists (select 1 from public.plays p where p.id = play_id and p.user_id = auth.uid()))
  with check (exists (select 1 from public.plays p where p.id = play_id and p.user_id = auth.uid()));


-- ============================================================
-- 4. 랭킹 뷰 — 사람별 전적
-- ============================================================

create or replace view public.player_standings as
select
  r.player_name,
  count(*)                                              as games_played,
  count(*) filter (where r.rank = 1)                    as wins,
  round(100.0 * count(*) filter (where r.rank = 1) / nullif(count(*), 0), 1) as win_rate,
  round(avg(r.rank)::numeric, 2)                        as avg_rank,
  max(p.played_on)                                      as last_played
from public.play_results r
join public.plays p on p.id = r.play_id
group by r.player_name;

-- 뷰는 기반 테이블의 RLS를 따르므로 별도 정책이 필요 없습니다.
