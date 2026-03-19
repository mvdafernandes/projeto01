begin;

-- These tables are backend-only. Keep RLS enabled and add explicit deny-all
-- policies so the intent is visible and lint tools no longer flag "RLS enabled
-- with no policy". service_role still operates as backend and bypasses RLS.
drop policy if exists work_days_backend_only on public.work_days;
create policy work_days_backend_only
  on public.work_days
  as restrictive
  for all
  to public
  using (false)
  with check (false);

drop policy if exists work_day_events_backend_only on public.work_day_events;
create policy work_day_events_backend_only
  on public.work_day_events
  as restrictive
  for all
  to public
  using (false)
  with check (false);

drop policy if exists work_km_periods_backend_only on public.work_km_periods;
create policy work_km_periods_backend_only
  on public.work_km_periods
  as restrictive
  for all
  to public
  using (false)
  with check (false);

commit;
