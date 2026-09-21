-- Each month's cell shares of the household portfolio sum to one. Returns the months that don't.

select month, sum(share_of_pf) as total_share
from {{ ref('mart_pf_cells') }}
group by month
having abs(sum(share_of_pf) - 1) > 1e-9
