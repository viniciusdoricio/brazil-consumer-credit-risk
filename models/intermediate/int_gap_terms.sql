-- The per-product terms of each occupation pair's 90-day gap, within an income band, window and
-- product scope (docs/analysis-design.md, section 1.4). For a pair A and B and a product p, with
-- v the product's share of the occupation's balance and r its 90-day rate:
--     same-product term = (v_A + v_B) / 2 * (r_A - r_B)
--     product-mix term  = (r_A + r_B) / 2 * (v_A - v_B)
-- Summed over products, the two terms add up exactly to the gap between the two occupations'
-- rates. Where an occupation has no balance in a product, its rate is taken as the other's: that
-- keeps the identity exact and puts the whole difference in the product-mix term. Every term is
-- computed under both product mappings (int_cross_section_by_mapping).

with totals as (
    select
        window_id, product_mapping, product_scope, income_band, occupation,
        sum(carteira_ativa) as occupation_balance
    from {{ ref('int_cross_section_by_mapping') }}
    group by all
),

products as (
    select
        pooled.window_id,
        pooled.product_mapping,
        pooled.product_scope,
        pooled.income_band,
        pooled.occupation,
        pooled.product_group,
        pooled.carteira_ativa / totals.occupation_balance as product_share,
        pooled.carteira_inadimplencia / nullif(pooled.carteira_ativa, 0) as product_rate
    from {{ ref('int_cross_section_by_mapping') }} as pooled
    inner join totals
        on pooled.window_id = totals.window_id
        and pooled.product_mapping = totals.product_mapping
        and pooled.product_scope = totals.product_scope
        and pooled.income_band = totals.income_band
        and pooled.occupation = totals.occupation
),

side_a as (
    select pairs.pair_id, products.*
    from products
    inner join {{ ref('occupation_pairs') }} as pairs on products.occupation = pairs.occupation_a
),

side_b as (
    select pairs.pair_id, products.*
    from products
    inner join {{ ref('occupation_pairs') }} as pairs on products.occupation = pairs.occupation_b
),

paired as (
    select
        coalesce(a.pair_id, b.pair_id) as pair_id,
        coalesce(a.window_id, b.window_id) as window_id,
        coalesce(a.product_mapping, b.product_mapping) as product_mapping,
        coalesce(a.product_scope, b.product_scope) as product_scope,
        coalesce(a.income_band, b.income_band) as income_band,
        coalesce(a.product_group, b.product_group) as product_group,
        coalesce(a.product_share, 0) as share_a,
        coalesce(b.product_share, 0) as share_b,
        coalesce(a.product_rate, b.product_rate) as rate_a,
        coalesce(b.product_rate, a.product_rate) as rate_b
    from side_a as a
    full outer join side_b as b
        on a.pair_id = b.pair_id
        and a.window_id = b.window_id
        and a.product_mapping = b.product_mapping
        and a.product_scope = b.product_scope
        and a.income_band = b.income_band
        and a.product_group = b.product_group
)

select
    *,
    (share_a + share_b) / 2 * (rate_a - rate_b) as same_product_term,
    (rate_a + rate_b) / 2 * (share_a - share_b) as product_mix_term
from paired
