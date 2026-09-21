-- int_cross_section_by_mapping rebuilds the pooled cells from staging so it can regroup
-- sub-modalities. Under the primary mapping it must reproduce int_cross_section_pooled exactly;
-- this also catches a sub-modality the inner join to the mappings would drop. Returns the cells
-- that differ or exist on one side only.

with by_mapping as (
    select *
    from {{ ref('int_cross_section_by_mapping') }}
    where product_mapping = 'primary'
)

select
    coalesce(by_mapping.window_id, pooled.window_id) as window_id,
    coalesce(by_mapping.product_scope, pooled.product_scope) as product_scope,
    coalesce(by_mapping.income_band, pooled.income_band) as income_band,
    coalesce(by_mapping.occupation, pooled.occupation) as occupation,
    coalesce(by_mapping.product_group, pooled.product_group) as product_group,
    by_mapping.carteira_ativa as rebuilt_balance,
    pooled.carteira_ativa as pooled_balance
from by_mapping
full outer join {{ ref('int_cross_section_pooled') }} as pooled
    on by_mapping.window_id = pooled.window_id
    and by_mapping.product_scope = pooled.product_scope
    and by_mapping.income_band = pooled.income_band
    and by_mapping.occupation = pooled.occupation
    and by_mapping.product_group = pooled.product_group
where by_mapping.carteira_ativa is distinct from pooled.carteira_ativa
    or by_mapping.carteira_inadimplencia is distinct from pooled.carteira_inadimplencia
