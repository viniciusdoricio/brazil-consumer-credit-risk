-- One row for every headline pair, cross-section window with data, product scope and named income
-- band, so no comparison is silently dropped by a join. Windows are counted from the pooled data,
-- not the seed: a build on part of the history (as in CI) has no rows for the earlier windows.
-- Returns a row if the count is off.

with expected as (
    select
        (select count(*) from {{ ref('occupation_pairs') }})
        * (select count(distinct window_id) from {{ ref('int_cross_section_pooled') }})
        * 2
        * (
            select count(distinct income_band)
            from {{ ref('int_cross_section_pooled') }}
            where {{ is_primary_cell("'any named occupation'", 'income_band') }}
        ) as rows_expected
),

actual as (
    select count(*) as rows_found from {{ ref('analysis_gap_decomposition') }}
)

select rows_expected, rows_found
from expected cross join actual
where rows_expected <> rows_found
