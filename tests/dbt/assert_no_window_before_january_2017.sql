-- Occupations were reclassified in January 2017, when every named occupation's 90-day rate jumped
-- while the national rate didn't (docs/data-dictionary.md, section 10.2), so no window may start
-- before it. Returns the windows that do.

select window_id, kind, start_month
from {{ ref('analysis_windows') }}
where start_month < cast('{{ var("first_comparable_month") }}' as date)
