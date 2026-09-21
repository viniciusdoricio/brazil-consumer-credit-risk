-- Chart 2, the grid: household 90-day and 15-90-day rates by occupation and income band, pooled
-- over each cross-section window, with the lagged-denominator 90-day rate beside them. Cells
-- below the minimum size keep their balances but are flagged, and their rates are not shown.

with cells as (
    select
        window_id,
        months,
        occupation,
        income_band,
        sum(carteira_ativa) as carteira_ativa,
        sum(carteira_inadimplencia) as carteira_inadimplencia,
        sum(vencido_de_15_ate_90_dias) as vencido_de_15_ate_90_dias,
        sum(carteira_ativa_12_months_before) as carteira_ativa_12_months_before
    from {{ ref('int_cross_section_pooled') }}
    where product_scope = 'all_products'
    group by all
)

select
    window_id,
    occupation,
    income_band,
    carteira_ativa / months / 1e9 as average_balance_bn,
    carteira_inadimplencia / carteira_ativa as d90_rate,
    vencido_de_15_ate_90_dias / carteira_ativa as d15_rate,
    carteira_inadimplencia / nullif(carteira_ativa_12_months_before, 0) as d90_rate_lagged,
    {{ is_primary_cell('occupation', 'income_band') }} as in_primary_grid,
    carteira_ativa / months / 1e9 < {{ var('min_cell_balance_bn') }} as below_minimum_size
from cells
