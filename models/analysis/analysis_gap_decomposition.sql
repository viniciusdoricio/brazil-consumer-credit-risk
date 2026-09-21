-- Chart 4, job or product: each headline occupation pair's 90-day gap within an income band, split
-- into the part that comes from different rates in the same products and the part that comes from
-- holding different products (int_gap_terms). The gap is also recomputed with lagged denominators:
-- if its sign flips, the ranking of the two occupations is not reported as a finding
-- (docs/analysis-design.md, section 2.2). The split is also run with the alternative product
-- mapping: where its product-mix part moves by more than var('max_crosswalk_shift') of the gap,
-- the split depends on how products are grouped and is reported as unstable (docs/v1-decision.md,
-- section 6).

with occupations as (
    select
        window_id,
        product_scope,
        income_band,
        occupation,
        sum(carteira_ativa) / max(months) / 1e9 as average_balance_bn,
        sum(carteira_inadimplencia) / sum(carteira_ativa) as rate,
        sum(carteira_inadimplencia) / nullif(sum(carteira_ativa_12_months_before), 0) as rate_lagged
    from {{ ref('int_cross_section_pooled') }}
    group by all
),

terms as (
    select
        pair_id,
        window_id,
        product_scope,
        income_band,
        sum(same_product_term) filter (where product_mapping = 'primary') as same_product_gap,
        sum(product_mix_term) filter (where product_mapping = 'primary') as product_mix_gap,
        sum(same_product_term) filter (where product_mapping = 'alternative')
            as same_product_gap_alternative_mapping,
        sum(product_mix_term) filter (where product_mapping = 'alternative')
            as product_mix_gap_alternative_mapping
    from {{ ref('int_gap_terms') }}
    group by all
)

select
    terms.pair_id,
    pairs.occupation_a,
    pairs.occupation_b,
    terms.window_id,
    terms.product_scope,
    terms.income_band,
    a.rate as rate_a,
    b.rate as rate_b,
    a.rate - b.rate as gap,
    terms.same_product_gap,
    terms.product_mix_gap,
    case
        when abs(a.rate - b.rate) >= 0.001 then terms.product_mix_gap / (a.rate - b.rate)
    end as product_mix_share_of_gap,
    terms.same_product_gap_alternative_mapping,
    terms.product_mix_gap_alternative_mapping,
    case
        when abs(a.rate - b.rate) >= 0.001
            then abs(terms.product_mix_gap_alternative_mapping - terms.product_mix_gap)
            <= {{ var('max_crosswalk_shift') }} * abs(a.rate - b.rate)
    end as split_holds_under_alternative_mapping,
    a.average_balance_bn as balance_a_bn,
    b.average_balance_bn as balance_b_bn,
    least(a.average_balance_bn, b.average_balance_bn) < {{ var('min_cell_balance_bn') }}
        as below_minimum_size,
    a.rate_lagged - b.rate_lagged as gap_lagged,
    sign(a.rate - b.rate) = sign(a.rate_lagged - b.rate_lagged) as gap_sign_holds_with_lag
from terms
inner join {{ ref('occupation_pairs') }} as pairs on terms.pair_id = pairs.pair_id
inner join occupations as a
    on terms.window_id = a.window_id
    and terms.product_scope = a.product_scope
    and terms.income_band = a.income_band
    and a.occupation = pairs.occupation_a
inner join occupations as b
    on terms.window_id = b.window_id
    and terms.product_scope = b.product_scope
    and terms.income_band = b.income_band
    and b.occupation = pairs.occupation_b
where {{ is_primary_cell('pairs.occupation_a', 'terms.income_band') }}
