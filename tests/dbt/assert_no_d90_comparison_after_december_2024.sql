-- No 90-day comparison may reach past the last month before Res. CMN 4.966 changed write-offs
-- (docs/analysis-design.md, section 1.3). Returns the comparisons that do.

select comparison_id, variant, month_0, month_1
from {{ ref('analysis_shift_share') }}
where
    measure = 'd90'
    and month_1 > cast('{{ var("d90_last_comparable_month") }}' as date)
