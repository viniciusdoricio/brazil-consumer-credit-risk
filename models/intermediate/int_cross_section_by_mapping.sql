-- Household balances pooled over each cross-section window by product group, under two ways of
-- grouping sub-modalities: the primary mapping (pf_product_groups), and an alternative that moves
-- the ambiguous sub-modalities and separates card purchases from card credit
-- (product_group_alternatives). Chart 4's split is run on both, and is unstable where its terms
-- move by more than var('max_crosswalk_shift') of the gap (docs/v1-decision.md, section 6). The
-- rural scope is defined by the primary mapping in both, so the two rearrange the same balances
-- and the gap itself is identical.

with windows as (
    select window_id, start_month, end_month
    from {{ ref('analysis_windows') }}
    where kind = 'cross_section'
),

mappings as (
    select
        modalidade,
        submodalidade,
        product_group as primary_group,
        'primary' as product_mapping,
        product_group
    from {{ ref('pf_product_groups') }}
    union all
    select
        groups.modalidade,
        groups.submodalidade,
        groups.product_group,
        'alternative',
        coalesce(alternatives.alternative_group, groups.product_group)
    from {{ ref('pf_product_groups') }} as groups
    left join {{ ref('product_group_alternatives') }} as alternatives
        on groups.modalidade = alternatives.modalidade
        and groups.submodalidade = alternatives.submodalidade
),

pf as (
    select
        windows.window_id,
        scr.cnae_ocupacao as occupation,
        scr.porte as income_band,
        scr.modalidade,
        scr.submodalidade,
        sum(scr.carteira_ativa) as carteira_ativa,
        sum(scr.carteira_inadimplencia) as carteira_inadimplencia
    from {{ ref('stg_bcb__scrdata') }} as scr
    inner join windows
        on scr.month between windows.start_month and windows.end_month
    where scr.cliente = 'PF'
    group by all
),

scopes as (
    select 'all_products' as product_scope
    union all
    select 'excluding_rural'
)

select
    pf.window_id,
    mappings.product_mapping,
    scopes.product_scope,
    pf.income_band,
    pf.occupation,
    mappings.product_group,
    sum(pf.carteira_ativa) as carteira_ativa,
    sum(pf.carteira_inadimplencia) as carteira_inadimplencia
from pf
inner join mappings
    on pf.modalidade = mappings.modalidade
    and pf.submodalidade = mappings.submodalidade
cross join scopes
where scopes.product_scope = 'all_products' or mappings.primary_group <> 'Rural'
group by all
