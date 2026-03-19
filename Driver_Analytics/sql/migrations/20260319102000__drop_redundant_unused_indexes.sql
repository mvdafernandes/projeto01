begin;

-- These indexes are either fully covered by more specific composites used by the
-- current code paths or are legacy single-column date indexes no longer used by
-- the backend query model.
drop index if exists public.idx_receitas_user_id_data;
drop index if exists public.idx_despesas_user_id_data;
drop index if exists public.idx_investimentos_user_id_data;
drop index if exists public.idx_investimentos_user_id_data_fim;
drop index if exists public.idx_work_km_periods_user_id;
drop index if exists public.idx_categorias_despesas_user_id;
drop index if exists public.idx_controle_km_data_inicio;
drop index if exists public.idx_controle_km_data_fim;
drop index if exists public.idx_controle_litros_data;

commit;
