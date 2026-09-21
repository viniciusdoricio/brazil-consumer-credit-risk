-- Chart 3, which matters more: for each calendar year 2017-2024, how far apart occupations' rates
-- sit within an income band, against how far apart income bands' rates sit within an occupation.
-- Each spread is a balance-weighted standard deviation of cell rates around the band's (or the
-- occupation's) own rate, averaged over bands (or occupations) by their balance. Calendar years
-- contain no January, so band membership is fixed within each. Cells below the minimum size are
-- left out. The "primary" variant uses the named occupations and bands only; "all" adds the
-- residual categories. Unemployment is the year's average of SGS 24369.

with cells as (
    select
        year(month) as year,
        occupation,
        income_band,
        sum(carteira_ativa) as carteira_ativa,
        sum(carteira_inadimplencia) as numerator_d90,
        sum(vencido_de_15_ate_90_dias) as numerator_d15
    from {{ ref('mart_pf_cells') }}
    where month between date '2017-01-01' and cast('{{ var("d90_last_comparable_month") }}' as date)
    group by all
    having sum(carteira_ativa) / 12 / 1e9 >= {{ var('min_cell_balance_bn') }}
),

measured as (
    select year, occupation, income_band, carteira_ativa, 'd90' as measure, numerator_d90 as numerator,
        {{ is_primary_cell('occupation', 'income_band') }} as primary_cell
    from cells
    union all
    select year, occupation, income_band, carteira_ativa, 'd15', numerator_d15,
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
        year, measure, variant, income_band,
        sum(carteira_ativa) as band_balance,
        sqrt(
            sum(carteira_ativa * power(rate - band_rate, 2)) / sum(carteira_ativa)
        ) as spread
    from (
        select *, sum(numerator) over w / sum(carteira_ativa) over w as band_rate
        from rated
        window w as (partition by year, measure, variant, income_band)
    )
    group by all
),

band_spread_by_occupation as (
    select
        year, measure, variant, occupation,
        sum(carteira_ativa) as occupation_balance,
        sqrt(
            sum(carteira_ativa * power(rate - occupation_rate, 2)) / sum(carteira_ativa)
        ) as spread
    from (
        select *, sum(numerator) over w / sum(carteira_ativa) over w as occupation_rate
        from rated
        window w as (partition by year, measure, variant, occupation)
    )
    group by all
),

unemployment as (
    select year(month) as year, avg(value) / 100 as unemployment_rate
    from {{ ref('stg_bcb__sgs') }}
    where sgs_code = 24369
    group by 1
),

mid_year_income_events as (
    select distinct year(month) as year
    from {{ ref('classification_events') }}
    where dimension = 'income' and month(month) <> 1
)

select
    occupations.year,
    occupations.measure,
    occupations.variant,
    occupations.spread_across_occupations_within_bands,
    bands.spread_across_bands_within_occupations,
    occupations.spread_across_occupations_within_bands
    / bands.spread_across_bands_within_occupations as occupation_to_income_ratio,
    unemployment.unemployment_rate,
    mid_year_income_events.year is not null as year_has_mid_year_income_event
from (
    select year, measure, variant,
        sum(band_balance * spread) / sum(band_balance) as spread_across_occupations_within_bands
    from occupation_spread_by_band
    group by all
) as occupations
inner join (
    select year, measure, variant,
        sum(occupation_balance * spread) / sum(occupation_balance) as spread_across_bands_within_occupations
    from band_spread_by_occupation
    group by all
) as bands
    on occupations.year = bands.year
    and occupations.measure = bands.measure
    and occupations.variant = bands.variant
left join unemployment on occupations.year = unemployment.year
left join mid_year_income_events on occupations.year = mid_year_income_events.year
