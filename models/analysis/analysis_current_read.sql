-- Chart 6, the current read: each occupation's 15-90-day rate over the last 12 published months
-- against calendar 2024, next to the change in its real portfolio. The 15-90-day rate is the one
-- delinquency measure that runs through the January 2025 accounting change, with one caveat:
-- since 2025, overdue amounts carry accrued interest until an asset becomes a problem asset
-- (docs/data-landscape.md, section A.3). Income bands are left out: they were reclassified in
-- July 2025 and May 2026. Balances are in reais of the latest month (int_price_index). A rate that
-- fell while the real portfolio shrank is flagged as possible tightening, not borrowers improving
-- (docs/analysis-design.md, section 2.2).

with latest as (
    select max(month) as latest_month from {{ ref('mart_pf_cells') }}
),

windows as (
    select 'calendar_2024' as window_id, date '2024-01-01' as start_month, date '2024-12-01' as end_month
    union all
    select 'last_12_months', cast(latest_month - interval 11 month as date), latest_month
    from latest
),

monthly as (
    select
        month,
        occupation,
        sum(carteira_ativa) as balance,
        sum(vencido_de_15_ate_90_dias) as numerator,
        sum(carteira_ativa_3_months_before) as balance_3_months_before
    from {{ ref('int_pf_cells_lagged') }}
    group by all
),

pooled as (
    select
        windows.window_id,
        monthly.occupation,
        count(*) as months,
        sum(monthly.numerator) / sum(monthly.balance) as d15_rate,
        sum(monthly.numerator) / nullif(sum(monthly.balance_3_months_before), 0) as d15_rate_lagged,
        avg(monthly.balance / prices.price_index) / 1e9 as average_real_balance_bn
    from monthly
    inner join windows on monthly.month between windows.start_month and windows.end_month
    inner join {{ ref('int_price_index') }} as prices on monthly.month = prices.month
    group by all
)

select
    base.occupation,
    (select latest_month from latest) as latest_month,
    base.months as months_2024,
    recent.months as months_last_12,
    base.d15_rate as d15_rate_2024,
    recent.d15_rate as d15_rate_last_12_months,
    recent.d15_rate - base.d15_rate as d15_change,
    base.d15_rate_lagged as d15_rate_lagged_2024,
    recent.d15_rate_lagged as d15_rate_lagged_last_12_months,
    recent.d15_rate_lagged - base.d15_rate_lagged as d15_change_lagged,
    base.average_real_balance_bn as average_real_balance_2024_bn,
    recent.average_real_balance_bn as average_real_balance_last_12_months_bn,
    recent.average_real_balance_bn / base.average_real_balance_bn - 1 as real_balance_growth,
    recent.d15_rate < base.d15_rate
    and recent.average_real_balance_bn < base.average_real_balance_bn as possible_tightening,
    base.occupation not in ({{ "'" ~ var('residual_occupations') | join("', '") ~ "'" }}) as named_occupation
from pooled as base
inner join pooled as recent on base.occupation = recent.occupation
where base.window_id = 'calendar_2024' and recent.window_id = 'last_12_months'
