-- Run after supabase/azit.sql in a non-production database. Always rolls back.
begin;

insert into public.space_bookings
  (id, start_at, end_at, name, contact, party_size, monthly_pass_count, monthly_member_name)
values
  ('00000000-0000-4000-8000-000000000001', '2099-01-01 10:00+09', '2099-01-01 11:00+09', '테스트', 'test', 1, 1, '테스트'),
  ('00000000-0000-4000-8000-000000000002', '2099-01-01 11:00+09', '2099-01-01 12:00+09', '테스트', 'test', 1, 1, '테스트');

do $$
begin
  begin
    insert into public.space_bookings
      (start_at, end_at, name, contact, party_size, monthly_pass_count, monthly_member_name)
    values
      ('2099-01-01 10:30+09', '2099-01-01 11:30+09', '충돌', 'test', 1, 1, '충돌');
    raise exception 'overlapping active booking was accepted';
  exception
    when exclusion_violation then null;
  end;
end
$$;

rollback;
