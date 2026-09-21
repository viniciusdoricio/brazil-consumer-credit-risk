-- Chart 2, the grid: household 90-day and 15-90-day rates by occupation and income band, pooled
-- over each cross-section window, with the lagged-denominator rates beside them (90-day on the
-- balance 12 months earlier, 15-90-day on 3 months earlier) and the cell's real growth, so a
-- fast-growing cell can't look safe just by being new (docs/analysis-design.md, section 2.2).
-- Growth runs from the window's first month to its last, never across a January, when band
-- membership shifts. Cells below the minimum size keep their balances but are flagged, and their
-- rates are not shown.

with cells as (
    select
        window_id,
        months,
        occupation,
        income_band,
        sum(carteira_ativa) as carteira_ativa,
        sum(carteira_inadimplencia) as carteira_inadimplencia,
        sum(vencido_de_15_ate_90_dias) as vencido_de_15_ate_90_dias,
        sum(carteira_ativa_3_months_before) as carteira_ativa_3_months_before,
        sum(carteira_ativa_12_months_before) as carteira_ativa_12_months_before
    from {{ ref('int_cross_section_pooled') }}
    where product_scope = 'all_products'
    group by all
),

real_balances as (
    select
        windows.window_id,
        cells.occupation,
        cells.income_band,
        sum(cells.carteira_ativa / prices.price_index)
            filter (where cells.month = windows.start_month) as real_balance_first_month,
        sum(cells.carteira_ativa / prices.price_index)
            filter (where cells.month = windows.end_month) as real_balance_last_month
    from {{ ref('int_pf_cells') }} as cells
    inner join {{ ref('analysis_windows') }} as windows
        on windows.kind = 'cross_section'
        and cells.month in (windows.start_month, windows.end_month)
    inner join {{ ref('int_price_index') }} as prices on cells.month = prices.month
    group by all
)

select
    cells.window_id,
    cells.occupation,
    cells.income_band,
    cells.carteira_ativa / cells.months / 1e9 as average_balance_bn,
    cells.carteira_inadimplencia / cells.carteira_ativa as d90_rate,
    cells.vencido_de_15_ate_90_dias / cells.carteira_ativa as d15_rate,
    cells.carteira_inadimplencia / nullif(cells.carteira_ativa_12_months_before, 0) as d90_rate_lagged,
    cells.vencido_de_15_ate_90_dias / nullif(cells.carteira_ativa_3_months_before, 0) as d15_rate_lagged,
    real_balances.real_balance_last_month / nullif(real_balances.real_balance_first_month, 0) - 1
        as real_growth_within_window,
    {{ is_primary_cell('cells.occupation', 'cells.income_band') }} as in_primary_grid,
    cells.carteira_ativa / cells.months / 1e9 < {{ var('min_cell_balance_bn') }} as below_minimum_size
from cells
left join real_balances
    on cells.window_id = real_balances.window_id
    and cells.occupation = real_balances.occupation
    and cells.income_band = real_balances.income_band
