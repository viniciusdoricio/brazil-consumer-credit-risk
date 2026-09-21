-- Each row of product_group_alternatives must name a sub-modality in the primary mapping and move
-- it to a different group; otherwise the alternative mapping isn't testing what it says it tests.
-- Returns the rows that don't.

select alternatives.modalidade, alternatives.submodalidade, alternatives.alternative_group
from {{ ref('product_group_alternatives') }} as alternatives
left join {{ ref('pf_product_groups') }} as groups
    on alternatives.modalidade = groups.modalidade
    and alternatives.submodalidade = groups.submodalidade
where groups.product_group is null
    or groups.product_group = alternatives.alternative_group
