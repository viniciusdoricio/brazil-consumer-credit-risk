-- Every published SCR.data month has a price index, so no real balance is silently dropped.
-- Returns the months without one.

select monthly.month
from {{ ref('mart_pf_monthly') }} as monthly
left join {{ ref('int_price_index') }} as prices on monthly.month = prices.month
where prices.price_index is null
