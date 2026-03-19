begin;

-- Keep the explicit tipo_movimentacao index and drop the duplicate legacy alias.
drop index if exists public.idx_investimentos_tipo;

commit;
