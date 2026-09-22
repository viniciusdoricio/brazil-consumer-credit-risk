-- A consumer price index built from IPCA's monthly change (SGS 433), equal to 1 in the latest
-- month of SCR.data, so dividing a balance by it gives reais of that month. The index starts in
-- 2012, a few months before SCR.data V2.

with changes as (
    select month, value / 100 as monthly_change
    from {{ ref('stg_bcb__sgs') }}
    where sgs_code = 433 and month >= date '2012-01-01'
),

levels as (
    select month, exp(sum(ln(1 + monthly_change)) over (order by month)) as price_level
    from changes
),

base as (
    select levels.price_level as base_level
    from levels
    where levels.month = (select max(month) from {{ ref('int_pf_cells') }})
)

select levels.month, levels.price_level / base.base_level as price_index
from levels
cross join base
