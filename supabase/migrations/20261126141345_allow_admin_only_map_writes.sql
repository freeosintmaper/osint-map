-- Remove the legacy permissive policies that allowed any authenticated
-- account to write, then add explicit administrator-only permissive policies.
-- The restrictive policies created by the previous migration remain as defense in depth.

drop policy if exists "Auth delete zones" on public.control_zones;
drop policy if exists "Auth insert zones" on public.control_zones;
drop policy if exists "Auth update zones" on public.control_zones;

drop policy if exists "Authenticated can delete events" on public.events;
drop policy if exists "Authenticated can insert events" on public.events;
drop policy if exists "Authenticated can update events" on public.events;

drop policy if exists "Admin may delete zones" on public.control_zones;
create policy "Admin may delete zones"
  on public.control_zones
  for delete to authenticated
  using ((select private.is_osint_map_admin()));

drop policy if exists "Admin may insert zones" on public.control_zones;
create policy "Admin may insert zones"
  on public.control_zones
  for insert to authenticated
  with check ((select private.is_osint_map_admin()));

drop policy if exists "Admin may update zones" on public.control_zones;
create policy "Admin may update zones"
  on public.control_zones
  for update to authenticated
  using ((select private.is_osint_map_admin()))
  with check ((select private.is_osint_map_admin()));

drop policy if exists "Admin may delete events" on public.events;
create policy "Admin may delete events"
  on public.events
  for delete to authenticated
  using ((select private.is_osint_map_admin()));

drop policy if exists "Admin may insert events" on public.events;
create policy "Admin may insert events"
  on public.events
  for insert to authenticated
  with check ((select private.is_osint_map_admin()));

drop policy if exists "Admin may update events" on public.events;
create policy "Admin may update events"
  on public.events
  for update to authenticated
  using ((select private.is_osint_map_admin()))
  with check ((select private.is_osint_map_admin()));

revoke all on table public.control_zones from public, anon, authenticated;
grant select on table public.control_zones to anon;
grant select, insert, update, delete on table public.control_zones to authenticated;

revoke all on table public.events from public, anon, authenticated;
grant select on table public.events to anon;
grant select, insert, update, delete on table public.events to authenticated;
