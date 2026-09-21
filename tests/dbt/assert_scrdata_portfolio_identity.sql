{{ config(warn_if='>0', error_if='>1') }}

-- carteira_ativa equals performing plus overdue balances. Before 2017 thousands of rows break this
-- (24,524 household rows, R$709.7 mn in total over 2012-2016), so the check covers the analysis
-- window only. From 2017 exactly one published row breaks it: December 2024, PR, fintech, payroll
-- loans, R$3,088.53 short. The test warns on that row and fails if any other appears.

select month, cliente, uf, segmento, cnae_ocupacao, porte, modalidade, submodalidade,
    carteira_ativa - (carteira_a_vencer + carteira_vencida) as difference
from {{ ref('stg_bcb__scrdata') }}
where
    month >= date '2017-01-01'
    and carteira_ativa <> carteira_a_vencer + carteira_vencida
