-- Chart 5, mix versus rate: the change in the national household rate between two months, split
-- exactly into three parts (docs/analysis-design.md, section 1.3). With o an occupation, p a
-- product group, W the occupation's share of the household portfolio, v the product's share of
-- the occupation's balance, r a rate, mid() the average of the two months and d() the change:
--     pure rate    = sum_o mid(W_o) * sum_p mid(v_p|o) * d(r_op)
--     product mix  = sum_o mid(W_o) * sum_p mid(r_op) * d(v_p|o)
--     borrower mix = sum_o mid(R_o) * d(W_o)
-- Cells are occupation x product, not income: bands shift every January, so an income "mix"
-- across years would mostly be the minimum wage. Where a cell is empty at one end, its rate is
-- taken from the other end, which keeps the split exact. The "all" variant keeps every
-- occupation and sums to the published total; "excluding_residual" drops "Outros".

with cells as (
    select
        month,
        occupation,
        product_group,
        sum(carteira_ativa) as balance,
        sum(carteira_inadimplencia) as numerator_d90,
        sum(vencido_de_15_ate_90_dias) as numerator_d15
    from {{ ref('mart_pf_cells') }}
    where month >= date '2017-01-01'
    group by all
),

measured as (
    select month, occupation, product_group, balance, 'd90' as measure, numerator_d90 as numerator
    from cells
    union all
    select month, occupation, product_group, balance, 'd15', numerator_d15
    from cells
),

measures as (
    select 'd90' as measure
    union all
    select 'd15'
),

comparisons as (
    -- the fixed episodes, each starting in a January after an occupation reclassification
    select
        windows.window_id as comparison_id,
        'episode' as kind,
        measures.measure,
        windows.start_month as month_0,
        windows.end_month as month_1
    from {{ ref('analysis_windows') }} as windows
    cross join measures
    where windows.kind = 'episode'
    union all
    -- the 15-90-day rate, the one measure that runs through January 2025, to the latest month
    select 'ep_2025_latest', 'episode', 'd15', date '2025-01-01', max(month)
    from cells
    union all
    -- every month against the same month a year earlier, which removes January seasonality
    select
        'yoy_' || strftime(months.month, '%Y-%m'),
        'year_over_year',
        measures.measure,
        cast(months.month - interval 12 month as date),
        months.month
    from (select distinct month from cells) as months
    cross join measures
    where
        months.month >= date '2018-01-01'
        and (
            measures.measure = 'd15'
            or months.month <= cast('{{ var("d90_last_comparable_month") }}' as date)
        )
),

available as (
    -- a comparison needs both of its months in the data; a build on part of the history (as in
    -- CI) would otherwise divide by an empty starting month
    select comparisons.*
    from comparisons
    where
        comparisons.month_0 in (select month from cells)
        and comparisons.month_1 in (select month from cells)
),

variants as (
    select 'all' as variant
    union all
    select 'excluding_residual'
),

ends as (
    select
        comparisons.comparison_id,
        comparisons.measure,
        variants.variant,
        measured.occupation,
        measured.product_group,
        coalesce(sum(measured.balance) filter (where measured.month = comparisons.month_0), 0) as balance_0,
        coalesce(sum(measured.balance) filter (where measured.month = comparisons.month_1), 0) as balance_1,
        coalesce(sum(measured.numerator) filter (where measured.month = comparisons.month_0), 0) as numerator_0,
        coalesce(sum(measured.numerator) filter (where measured.month = comparisons.month_1), 0) as numerator_1
    from available as comparisons
    inner join measured
        on measured.measure = comparisons.measure
        and measured.month in (comparisons.month_0, comparisons.month_1)
    cross join variants
    where
        variants.variant = 'all'
        or measured.occupation not in ({{ "'" ~ var('residual_occupations') | join("', '") ~ "'" }})
    group by all
),

occupations as (
    select
        comparison_id, measure, variant, occupation,
        sum(balance_0) as balance_0,
        sum(balance_1) as balance_1,
        sum(numerator_0) as numerator_0,
        sum(numerator_1) as numerator_1
    from ends
    group by all
),

portfolio as (
    select
        comparison_id, measure, variant,
        sum(balance_0) as balance_0,
        sum(balance_1) as balance_1,
        sum(numerator_0) as numerator_0,
        sum(numerator_1) as numerator_1
    from ends
    group by all
),

products as (
    select
        ends.comparison_id,
        ends.measure,
        ends.variant,
        ends.occupation,
        coalesce(ends.balance_0 / nullif(occupations.balance_0, 0), 0) as share_0,
        coalesce(ends.balance_1 / nullif(occupations.balance_1, 0), 0) as share_1,
        coalesce(ends.numerator_0 / nullif(ends.balance_0, 0), ends.numerator_1 / nullif(ends.balance_1, 0)) as rate_0,
        coalesce(ends.numerator_1 / nullif(ends.balance_1, 0), ends.numerator_0 / nullif(ends.balance_0, 0)) as rate_1
    from ends
    inner join occupations
        on ends.comparison_id = occupations.comparison_id
        and ends.measure = occupations.measure
        and ends.variant = occupations.variant
        and ends.occupation = occupations.occupation
),

within_occupations as (
    select
        comparison_id, measure, variant, occupation,
        sum((share_0 + share_1) / 2 * (rate_1 - rate_0)) as pure_rate,
        sum((rate_0 + rate_1) / 2 * (share_1 - share_0)) as product_mix
    from products
    group by all
),

occupation_weights as (
    select
        occupations.comparison_id,
        occupations.measure,
        occupations.variant,
        occupations.occupation,
        occupations.balance_0 / portfolio.balance_0 as weight_0,
        occupations.balance_1 / portfolio.balance_1 as weight_1,
        coalesce(
            occupations.numerator_0 / nullif(occupations.balance_0, 0),
            occupations.numerator_1 / nullif(occupations.balance_1, 0)
        ) as rate_0,
        coalesce(
            occupations.numerator_1 / nullif(occupations.balance_1, 0),
            occupations.numerator_0 / nullif(occupations.balance_0, 0)
        ) as rate_1
    from occupations
    inner join portfolio
        on occupations.comparison_id = portfolio.comparison_id
        and occupations.measure = portfolio.measure
        and occupations.variant = portfolio.variant
),

decomposed as (
    select
        weights.comparison_id,
        weights.measure,
        weights.variant,
        sum((weights.weight_0 + weights.weight_1) / 2 * within.pure_rate) as pure_rate,
        sum((weights.weight_0 + weights.weight_1) / 2 * within.product_mix) as product_mix,
        sum((weights.rate_0 + weights.rate_1) / 2 * (weights.weight_1 - weights.weight_0)) as borrower_mix
    from occupation_weights as weights
    inner join within_occupations as within
        on weights.comparison_id = within.comparison_id
        and weights.measure = within.measure
        and weights.variant = within.variant
        and weights.occupation = within.occupation
    group by all
)

select
    comparisons.comparison_id,
    comparisons.kind,
    comparisons.measure,
    decomposed.variant,
    comparisons.month_0,
    comparisons.month_1,
    portfolio.numerator_0 / portfolio.balance_0 as rate_0,
    portfolio.numerator_1 / portfolio.balance_1 as rate_1,
    portfolio.numerator_1 / portfolio.balance_1 - portfolio.numerator_0 / portfolio.balance_0 as change,
    decomposed.pure_rate,
    decomposed.product_mix,
    decomposed.borrower_mix,
    exists (
        select 1
        from {{ ref('classification_events') }} as events
        where
            events.dimension = 'occupation'
            and events.month > comparisons.month_0
            and events.month <= comparisons.month_1
    ) as spans_occupation_reclassification
from available as comparisons
inner join decomposed
    on comparisons.comparison_id = decomposed.comparison_id
    and comparisons.measure = decomposed.measure
inner join portfolio
    on decomposed.comparison_id = portfolio.comparison_id
    and decomposed.measure = portfolio.measure
    and decomposed.variant = portfolio.variant
