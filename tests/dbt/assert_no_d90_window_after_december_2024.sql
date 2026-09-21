-- Cross-section windows and decomposition episodes compare 90-day rates, so none may run past the
-- last month before Res. CMN 4.966 changed write-offs (docs/analysis-design.md, section 1.3).
-- Returns the windows that do.

select window_id, kind, end_month
from {{ ref('analysis_windows') }}
where
    kind in ('cross_section', 'episode')
    and end_month > cast('{{ var("d90_last_comparable_month") }}' as date)
