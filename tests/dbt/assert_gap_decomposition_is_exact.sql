-- The same-product and product-mix parts of every occupation gap add up to the gap itself
-- (docs/analysis-design.md, section 1.4), under both product mappings. Returns the rows where they
-- don't, to 1e-12.

select
    pair_id, window_id, product_scope, income_band, gap, same_product_gap, product_mix_gap,
    same_product_gap_alternative_mapping, product_mix_gap_alternative_mapping
from {{ ref('analysis_gap_decomposition') }}
where abs(gap - (same_product_gap + product_mix_gap)) > 1e-12
    or abs(gap - (same_product_gap_alternative_mapping + product_mix_gap_alternative_mapping)) > 1e-12
    or gap is null
    or same_product_gap is null
    or product_mix_gap is null
    or same_product_gap_alternative_mapping is null
    or product_mix_gap_alternative_mapping is null
