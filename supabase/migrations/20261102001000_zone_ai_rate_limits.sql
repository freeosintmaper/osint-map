-- Server-side per-admin rate limiting for the zone AI Edge Function.
-- This table is not exposed to anon/authenticated clients. Only the SECURITY DEFINER
-- RPC can update it, and only the service_role may execute that RPC.

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

create table if not exists private.zone_ai_rate_limits (
  key_hash text primary key check (key_hash ~ '^[a-f0-9]{64}$'),
  window_started_at timestamptz not null,
  request_count integer not null check (request_count >= 1)
);

alter table private.zone_ai_rate_limits enable row level security;
revoke all on table private.zone_ai_rate_limits from public, anon, authenticated;

create or replace function public.consume_zone_ai_rate_limit(
  p_key_hash text,
  p_limit integer,
  p_window_seconds integer
)
returns table (
  allowed boolean,
  retry_after_seconds integer,
  remaining integer
)
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_now timestamptz := pg_catalog.clock_timestamp();
  v_window_started_at timestamptz;
  v_request_count integer;
begin
  if p_key_hash is null
     or p_key_hash !~ '^[a-f0-9]{64}$'
     or p_limit is null
     or p_limit < 1
     or p_limit > 100
     or p_window_seconds is null
     or p_window_seconds < 1
     or p_window_seconds > 3600 then
    raise exception 'Invalid zone AI rate-limit parameters'
      using errcode = '22023';
  end if;

  insert into private.zone_ai_rate_limits as stored (
    key_hash,
    window_started_at,
    request_count
  )
  values (
    p_key_hash,
    v_now,
    1
  )
  on conflict (key_hash) do update
    set window_started_at = case
          when stored.window_started_at + pg_catalog.make_interval(secs => p_window_seconds) <= excluded.window_started_at
          then excluded.window_started_at
          else stored.window_started_at
        end,
        request_count = case
          when stored.window_started_at + pg_catalog.make_interval(secs => p_window_seconds) <= excluded.window_started_at
          then 1
          else least(stored.request_count + 1, p_limit + 1)
        end
  returning stored.window_started_at, stored.request_count
    into v_window_started_at, v_request_count;

  return query
  select
    v_request_count <= p_limit,
    case
      when v_request_count <= p_limit then 0
      else greatest(
        1,
        ceil(extract(epoch from (
          v_window_started_at + pg_catalog.make_interval(secs => p_window_seconds) - v_now
        )))::integer
      )
    end,
    greatest(0, p_limit - v_request_count);
end;
$function$;

revoke all on function public.consume_zone_ai_rate_limit(text, integer, integer)
  from public, anon, authenticated;
grant execute on function public.consume_zone_ai_rate_limit(text, integer, integer)
  to service_role;
