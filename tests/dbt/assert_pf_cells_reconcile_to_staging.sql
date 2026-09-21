-- The household cells add back to the staged SCR.data totals exactly, month by month, so the
-- product mapping neither loses nor double-counts a balance. Returns the months that don't.

with staged as (
    select
        month,
        sum(carteira_ativa) as carteira_ativa,
        sum(carteira_inadimplencia) as carteira_inadimplencia,
        sum(vencido_de_15_ate_90_dias) as vencido_de_15_ate_90_dias,
        sum(ativo_problematico) as ativo_problematico
    from {{ ref('stg_bcb__scrdata') }}
    where cliente = 'PF'
    group by month
),

cells as (
    select
        month,
        sum(carteira_ativa) as carteira_ativa,
        sum(carteira_inadimplencia) as carteira_inadimplencia,
        sum(vencido_de_15_ate_90_dias) as vencido_de_15_ate_90_dias,
        sum(ativo_problematico) as ativo_problematico
    from {{ ref('int_pf_cells') }}
    group by month
)

select coalesce(staged.month, cells.month) as month
from staged
full outer join cells on staged.month = cells.month
where
    staged.carteira_ativa is distinct from cells.carteira_ativa
    or staged.carteira_inadimplencia is distinct from cells.carteira_inadimplencia
    or staged.vencido_de_15_ate_90_dias is distinct from cells.vencido_de_15_ate_90_dias
    or staged.ativo_problematico is distinct from cells.ativo_problematico
