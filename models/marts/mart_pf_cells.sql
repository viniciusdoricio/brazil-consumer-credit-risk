-- Household cells with their rates. Rates are ratios of summed balances. d90_rate is only
-- comparable up to the last month before Res. CMN 4.966 changed write-offs; d15_rate runs
-- through the break (docs/data-landscape.md, section A.3).

select
    month,
    occupation,
    income_band,
    product_group,
    carteira_ativa,
    carteira_inadimplencia,
    vencido_de_15_ate_90_dias,
    ativo_problematico,
    operations_reported,
    rows_with_count_withheld,
    carteira_inadimplencia / nullif(carteira_ativa, 0) as d90_rate,
    vencido_de_15_ate_90_dias / nullif(carteira_ativa, 0) as d15_rate,
    ativo_problematico / nullif(carteira_ativa, 0) as problem_asset_rate,
    carteira_ativa / sum(carteira_ativa) over (partition by month) as share_of_pf,
    month <= cast('{{ var("d90_last_comparable_month") }}' as date) as d90_comparable
from {{ ref('int_pf_cells') }}
