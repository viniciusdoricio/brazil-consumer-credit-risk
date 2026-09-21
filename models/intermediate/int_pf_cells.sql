-- Household (PF) credit by month, occupation, income band and product group: the cells every v1
-- comparison is built from. Balances are summed first by modality and sub-modality, then mapped to
-- product groups, so the mapping touches a few thousand rows rather than tens of millions.

with pf as (
    select
        month,
        cnae_ocupacao as occupation,
        porte as income_band,
        modalidade,
        submodalidade,
        sum(carteira_ativa) as carteira_ativa,
        sum(carteira_inadimplencia) as carteira_inadimplencia,
        sum(vencido_de_15_ate_90_dias) as vencido_de_15_ate_90_dias,
        sum(vencido_acima_de_90_dias) as vencido_acima_de_90_dias,
        sum(ativo_problematico) as ativo_problematico,
        sum(numero_de_operacoes) filter (where numero_de_operacoes >= 0) as operations_reported,
        count(*) filter (where numero_de_operacoes = -1) as rows_with_count_withheld
    from {{ ref('stg_bcb__scrdata') }}
    where cliente = 'PF'
    group by all
)

select
    pf.month,
    pf.occupation,
    pf.income_band,
    product_groups.product_group,
    sum(pf.carteira_ativa) as carteira_ativa,
    sum(pf.carteira_inadimplencia) as carteira_inadimplencia,
    sum(pf.vencido_de_15_ate_90_dias) as vencido_de_15_ate_90_dias,
    sum(pf.vencido_acima_de_90_dias) as vencido_acima_de_90_dias,
    sum(pf.ativo_problematico) as ativo_problematico,
    sum(pf.operations_reported) as operations_reported,
    sum(pf.rows_with_count_withheld) as rows_with_count_withheld
from pf
left join {{ ref('pf_product_groups') }} as product_groups
    on pf.modalidade = product_groups.modalidade
    and pf.submodalidade = product_groups.submodalidade
group by all
