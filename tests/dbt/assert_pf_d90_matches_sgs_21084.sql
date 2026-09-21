-- SCR.data's household 90-day rate stays within 0.2 pp of the official series, SGS 21084, in
-- every month from 2017 to 2024 (observed: -0.10 to +0.13 pp). After 2024 the gap widens for
-- reasons not yet explained (docs/data-dictionary.md, U13), so those months are not held to it.
-- Returns the months outside the tolerance or missing the official value.

select month, d90_rate, sgs_21084_rate, d90_gap_to_sgs
from {{ ref('mart_pf_monthly') }}
where
    month between date '2017-01-01' and date '2024-12-01'
    and (sgs_21084_rate is null or abs(d90_gap_to_sgs) > 0.002)
