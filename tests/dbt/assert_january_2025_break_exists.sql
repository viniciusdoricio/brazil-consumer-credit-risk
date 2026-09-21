-- The January 2025 accounting break must be visible in the data (docs/data-landscape.md, Part A).
-- In the month Res. CMN 4.966 took effect, household problem assets and the 90-day rate step up
-- far beyond the same December-to-January move a year earlier, while the 15-90-day rate moves
-- like an ordinary January. Observed: +0.67 pp, +0.31 pp against +0.03 pp a year earlier, and
-- +0.03 pp. Returns a row, and fails, if any of that stops being true or the months are missing.

with steps as (
    select
        max(problem_asset_rate) filter (where month = date '2025-01-01')
        - max(problem_asset_rate) filter (where month = date '2024-12-01') as problem_asset_step,
        max(d90_rate) filter (where month = date '2025-01-01')
        - max(d90_rate) filter (where month = date '2024-12-01') as d90_step,
        max(d90_rate) filter (where month = date '2024-01-01')
        - max(d90_rate) filter (where month = date '2023-12-01') as d90_step_a_year_earlier,
        max(d15_rate) filter (where month = date '2025-01-01')
        - max(d15_rate) filter (where month = date '2024-12-01') as d15_step
    from {{ ref('mart_pf_monthly') }}
)

select *
from steps
where not coalesce(
    problem_asset_step >= 0.005
    and d90_step >= 0.0025
    and d90_step >= 5 * abs(d90_step_a_year_earlier)
    and abs(d15_step) <= 0.001,
    false
)
