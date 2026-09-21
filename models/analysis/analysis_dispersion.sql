-- Chart 3, which matters more: for each period, how far apart occupations' rates sit within an
-- income band, against how far apart income bands' rates sit within an occupation. The periods are
-- the calendar years 2017-2024, one point each on the chart, and the three cross-section windows,
-- on which the falsification test is defined (docs/v1-decision.md, section 6). Each spread is a
-- balance-weighted standard deviation of cell rates around the band's (or the occupation's) own
-- rate, averaged over bands (or occupations) by their balance. No period crosses a January, when
-- bands shift with the minimum wage; any other reclassification inside a period is flagged. Cells
-- below the minimum size are left out. The "primary" variant uses the named occupations and bands
-- only; "all" adds the residual categories. Unemployment is the period's average of SGS 24369.

with periods as (
    select
        cast(year as varchar) as period_id,
        'calendar_year' as period_kind,
        make_date(year, 1, 1) as start_month,
        make_date(year, 12, 1) as end_month
    from (
        select unnest(generate_series(
            year(cast('{{ var("first_comparable_month") }}' as date)),
            year(cast('{{ var("d90_last_comparable_month") }}' as date))
        )) as year
    )
    union all
    select window_id, 'window', start_month, end_month
    from {{ ref('analysis_windows') }}
    where kind = 'cross_section'
),

cells as (
    select
        periods.period_id,
        cells.occupation,
        cells.income_band,
        sum(cells.carteira_ativa) as carteira_ativa,
        sum(cells.carteira_inadimplencia) as numerator_d90,
        sum(cells.vencido_de_15_ate_90_dias) as numerator_d15
    from {{ ref('mart_pf_cells') }} as cells
    inner join periods
        on cells.month between periods.start_month and periods.end_month
    group by periods.period_id, periods.start_month, periods.end_month, cells.occupation, cells.income_band
    having sum(cells.carteira_ativa)
        / (datediff('month', periods.start_month, periods.end_month) + 1)
        / 1e9 >= {{ var('min_cell_balance_bn') }}
),

measured as (
    select period_id, occupation, income_band, carteira_ativa, 'd90' as measure, numerator_d90 as numerator,
        {{ is_primary_cell('occupation', 'income_band') }} as primary_cell
    from cells
    union all
    select period_id, occupation, income_band, carteira_ativa, 'd15', numerator_d15,
        {{ is_primary_cell('occupation', 'income_band') }}
    from cells
),

variants as (
    select *, 'primary' as variant from measured where primary_cell
    union all
    select *, 'all' from measured
),

rated as (
    select *, numerator / carteira_ativa as rate from variants
),

occupation_spread_by_band as (
    select
        period_id, measure, variant, income_band,
        sum(carteira_ativa) as band_balance,
        sqrt(
            sum(carteira_ativa * power(rate - band_rate, 2)) / sum(carteira_ativa)
        ) as spread
    from (
        select *, sum(numerator) over w / sum(carteira_ativa) over w as band_rate
        from rated
        window w as (partition by period_id, measure, variant, income_band)
    )
    group by all
),

band_spread_by_occupation as (
    select
        period_id, measure, variant, occupation,
        sum(carteira_ativa) as occupation_balance,
        sqrt(
            sum(carteira_ativa * power(rate - occupation_rate, 2)) / sum(carteira_ativa)
        ) as spread
    from (
        select *, sum(numerator) over w / sum(carteira_ativa) over w as occupation_rate
        from rated
        window w as (partition by period_id, measure, variant, occupation)
    )
    group by all
),

unemployment as (
    select periods.period_id, avg(sgs.value) / 100 as unemployment_rate
    from periods
    inner join {{ ref('stg_bcb__sgs') }} as sgs
        on sgs.sgs_code = 24369
        and sgs.month between periods.start_month and periods.end_month
    group by 1
),

-- Occupation and income events after a period's first month and up to its last, so a January
-- reset that opens a calendar year, or the March 2019 recoding that opens cs_2019, doesn't count.
reclassifications_inside as (
    select periods.period_id, count(*) as events
    from periods
    inner join {{ ref('classification_events') }} as events
        on events.dimension in ('occupation', 'income')
        and events.month > periods.start_month
        and events.month <= periods.end_month
    group by 1
)

select
    periods.period_id,
    periods.period_kind,
    periods.start_month,
    periods.end_month,
    occupations.measure,
    occupations.variant,
    occupations.spread_across_occupations_within_bands,
    bands.spread_across_bands_within_occupations,
    occupations.spread_across_occupations_within_bands
    / bands.spread_across_bands_within_occupations as occupation_to_income_ratio,
    unemployment.unemployment_rate,
    coalesce(reclassifications_inside.events, 0) as reclassifications_inside
from (
    select period_id, measure, variant,
        sum(band_balance * spread) / sum(band_balance) as spread_across_occupations_within_bands
    from occupation_spread_by_band
    group by all
) as occupations
inner join (
    select period_id, measure, variant,
        sum(occupation_balance * spread) / sum(occupation_balance) as spread_across_bands_within_occupations
    from band_spread_by_occupation
    group by all
) as bands
    on occupations.period_id = bands.period_id
    and occupations.measure = bands.measure
    and occupations.variant = bands.variant
inner join periods on occupations.period_id = periods.period_id
left join unemployment on occupations.period_id = unemployment.period_id
left join reclassifications_inside on occupations.period_id = reclassifications_inside.period_id
