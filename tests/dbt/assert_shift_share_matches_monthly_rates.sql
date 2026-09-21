-- With every occupation kept, the rates at both ends of each comparison are the published national
-- rates in mart_pf_monthly, so the decomposition explains the series the charts show. Returns the
-- comparisons where they differ by more than 1e-12.

select shift.comparison_id, shift.measure, shift.month_0, shift.month_1
from {{ ref('analysis_shift_share') }} as shift
inner join {{ ref('mart_pf_monthly') }} as start_month on start_month.month = shift.month_0
inner join {{ ref('mart_pf_monthly') }} as end_month on end_month.month = shift.month_1
where
    shift.variant = 'all'
    and (
        abs(shift.rate_0 - case shift.measure when 'd90' then start_month.d90_rate else start_month.d15_rate end) > 1e-12
        or abs(shift.rate_1 - case shift.measure when 'd90' then end_month.d90_rate else end_month.d15_rate end) > 1e-12
    )
