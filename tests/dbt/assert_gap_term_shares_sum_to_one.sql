-- Within each pair, window, product mapping, scope and income band, each occupation's product
-- shares add up to one, so the terms cover its whole balance and nothing is counted twice.
-- Returns the groups where either side's shares don't, to 1e-9.

select
    pair_id, window_id, product_mapping, product_scope, income_band,
    sum(share_a) as shares_a,
    sum(share_b) as shares_b
from {{ ref('int_gap_terms') }}
group by all
having abs(sum(share_a) - 1) > 1e-9 or abs(sum(share_b) - 1) > 1e-9
