-- Keep the map administrator allow-list outside the public API schema.
-- Bootstrap the trusted owner explicitly after creating the Auth user; see SECURITY.md.

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
grant usage on schema private to authenticated;

create table if not exists private.osint_map_admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);

alter table private.osint_map_admins enable row level security;
revoke all on table private.osint_map_admins from public, anon, authenticated;

create or replace function private.is_osint_map_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $function$
  select exists (
    select 1
    from private.osint_map_admins as admins
    join auth.sessions as sessions
      on sessions.user_id = admins.user_id
    where admins.user_id = (select auth.uid())
      and sessions.id = nullif((select auth.jwt() ->> 'session_id'), '')::uuid
      and (sessions.not_after is null or sessions.not_after > statement_timestamp())
  );
$function$;

revoke all on function private.is_osint_map_admin() from public, anon;
grant execute on function private.is_osint_map_admin() to authenticated;

create or replace function public.is_osint_map_admin()
returns boolean
language sql
stable
set search_path = ''
as $function$
  select private.is_osint_map_admin();
$function$;

revoke all on function public.is_osint_map_admin() from public, anon;
grant execute on function public.is_osint_map_admin() to authenticated;

alter table public.control_zones enable row level security;
alter table public.events enable row level security;

revoke all on table public.control_zones from public, anon, authenticated;
grant select on table public.control_zones to anon;
grant select, insert, update, delete on table public.control_zones to authenticated;

revoke all on table public.events from public, anon, authenticated;
grant select on table public.events to anon;
grant select, insert, update, delete on table public.events to authenticated;

drop policy if exists "Admin only insert zones" on public.control_zones;
create policy "Admin only insert zones"
  on public.control_zones as restrictive
  for insert to authenticated
  with check ((select private.is_osint_map_admin()));

drop policy if exists "Admin only update zones" on public.control_zones;
create policy "Admin only update zones"
  on public.control_zones as restrictive
  for update to authenticated
  using ((select private.is_osint_map_admin()))
  with check ((select private.is_osint_map_admin()));

drop policy if exists "Admin only delete zones" on public.control_zones;
create policy "Admin only delete zones"
  on public.control_zones as restrictive
  for delete to authenticated
  using ((select private.is_osint_map_admin()));

drop policy if exists "Admin only insert events" on public.events;
create policy "Admin only insert events"
  on public.events as restrictive
  for insert to authenticated
  with check ((select private.is_osint_map_admin()));

drop policy if exists "Admin only update events" on public.events;
create policy "Admin only update events"
  on public.events as restrictive
  for update to authenticated
  using ((select private.is_osint_map_admin()))
  with check ((select private.is_osint_map_admin()));

drop policy if exists "Admin only delete events" on public.events;
create policy "Admin only delete events"
  on public.events as restrictive
  for delete to authenticated
  using ((select private.is_osint_map_admin()));
