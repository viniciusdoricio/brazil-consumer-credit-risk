-- Each household cell with its own balance 3 and 12 months earlier, for the lagged-denominator
-- rates the design requires as a sensitivity: a fast-growing portfolio looks healthier than a
-- mature one simply because its new loans haven't had time to go bad (docs/analysis-design.md,
-- section 2.2). For income bands the lag crosses a January, when band membership shifts with the
-- minimum wage, so these rates are a crude seasoning check, not a measure in their own right.

select
    cells.month,
    cells.occupation,
    cells.income_band,
    cells.product_group,
    cells.carteira_ativa,
    cells.carteira_inadimplencia,
    cells.vencido_de_15_ate_90_dias,
    three_months_before.carteira_ativa as carteira_ativa_3_months_before,
    twelve_months_before.carteira_ativa as carteira_ativa_12_months_before
from {{ ref('int_pf_cells') }} as cells
left join {{ ref('int_pf_cells') }} as three_months_before
    on three_months_before.month = cast(cells.month - interval 3 month as date)
    and three_months_before.occupation = cells.occupation
    and three_months_before.income_band = cells.income_band
    and three_months_before.product_group = cells.product_group
left join {{ ref('int_pf_cells') }} as twelve_months_before
    on twelve_months_before.month = cast(cells.month - interval 12 month as date)
    and twelve_months_before.occupation = cells.occupation
    and twelve_months_before.income_band = cells.income_band
    and twelve_months_before.product_group = cells.product_group
