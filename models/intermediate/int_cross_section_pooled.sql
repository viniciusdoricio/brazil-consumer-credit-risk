-- Household balances pooled over each cross-section window, by income band, occupation and
-- product group, in two product scopes: all products, and all but rural credit (rural is over
-- half of the top income band and 42% of the self-employed, so every comparison is also run
-- without it). Pooling sums numerators and denominators over the window's months. No window
-- contains a January, so income-band membership is fixed within each.

with windows as (
    select
        window_id,
        start_month,
        end_month,
        datediff('month', start_month, end_month) + 1 as months
    from {{ ref('analysis_windows') }}
    where kind = 'cross_section'
),

scopes as (
    select 'all_products' as product_scope
    union all
    select 'excluding_rural'
)

select
    windows.window_id,
    windows.months,
    scopes.product_scope,
    cells.income_band,
    cells.occupation,
    cells.product_group,
    sum(cells.carteira_ativa) as carteira_ativa,
    sum(cells.carteira_inadimplencia) as carteira_inadimplencia,
    sum(cells.vencido_de_15_ate_90_dias) as vencido_de_15_ate_90_dias,
    sum(cells.carteira_ativa_3_months_before) as carteira_ativa_3_months_before,
    sum(cells.carteira_ativa_12_months_before) as carteira_ativa_12_months_before
from {{ ref('int_pf_cells_lagged') }} as cells
inner join windows
    on cells.month between windows.start_month and windows.end_month
cross join scopes
where scopes.product_scope = 'all_products' or cells.product_group <> 'Rural'
group by all
