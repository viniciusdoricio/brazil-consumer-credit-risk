-- National household (PF) credit by month: the rates every chart and check starts from, next to
-- the official series (SGS 21084) and the classification events of that month.

with totals as (
    select
        month,
        sum(carteira_ativa) as carteira_ativa,
        sum(carteira_inadimplencia) as carteira_inadimplencia,
        sum(vencido_de_15_ate_90_dias) as vencido_de_15_ate_90_dias,
        sum(ativo_problematico) as ativo_problematico
    from {{ ref('int_pf_cells') }}
    group by month
),

rates as (
    select
        month,
        carteira_ativa,
        carteira_inadimplencia / carteira_ativa as d90_rate,
        vencido_de_15_ate_90_dias / carteira_ativa as d15_rate,
        ativo_problematico / carteira_ativa as problem_asset_rate
    from totals
),

sgs as (
    select month, value / 100 as sgs_21084_rate
    from {{ ref('stg_bcb__sgs') }}
    where sgs_code = 21084
),

events as (
    select
        month,
        string_agg(dimension || ': ' || description, '; ' order by dimension) as classification_events
    from {{ ref('classification_events') }}
    group by month
)

select
    rates.month,
    rates.carteira_ativa,
    rates.d90_rate,
    rates.d15_rate,
    rates.problem_asset_rate,
    rates.month <= cast('{{ var("d90_last_comparable_month") }}' as date) as d90_comparable,
    sgs.sgs_21084_rate,
    rates.d90_rate - sgs.sgs_21084_rate as d90_gap_to_sgs,
    events.classification_events
from rates
left join sgs on rates.month = sgs.month
left join events on rates.month = events.month
