-- Maturity buckets add up exactly on every published row, in every month since July 2012
-- (docs/data-dictionary.md, section 2.3). Returns the rows that don't.

select month, cliente, uf, segmento, modalidade, submodalidade
from {{ ref('stg_bcb__scrdata') }}
where
    carteira_a_vencer
    <> a_vencer_ate_90_dias
    + a_vencer_de_91_ate_360_dias
    + a_vencer_de_361_ate_1080_dias
    + a_vencer_de_1081_ate_1800_dias
    + a_vencer_de_1801_ate_5400_dias
    + a_vencer_acima_de_5400_dias
    or carteira_vencida <> vencido_de_15_ate_90_dias + vencido_acima_de_90_dias
