-- The household card group's 90-day rate stays within 0.75 pp of BCB's official series for
-- household credit cards, SGS 21129, in every month from 2017 to 2024 (observed: -0.03 to
-- +0.69 pp, usually about +0.3 pp, as SGS covers non-earmarked credit only). It is the one
-- product-level check of the product grouping against an official series: moving card purchases
-- or financed card balances out of the group would push the rate far outside the tolerance. After
-- 2024 the two diverge as the 90-day stock builds up under Res. CMN 4.966, so those months are not
-- held to it. Returns the months outside the tolerance or missing the official value.

with ours as (
    select month, sum(carteira_inadimplencia) / sum(carteira_ativa) as card_rate
    from {{ ref('mart_pf_cells') }}
    where product_group = 'Cartão'
    group by month
),

official as (
    select month, value / 100 as sgs_21129_rate
    from {{ ref('stg_bcb__sgs') }}
    where sgs_code = 21129
)

select ours.month, ours.card_rate, official.sgs_21129_rate
from ours
left join official using (month)
where
    ours.month between cast('{{ var("first_comparable_month") }}' as date)
    and cast('{{ var("d90_last_comparable_month") }}' as date)
    and (
        official.sgs_21129_rate is null
        or abs(ours.card_rate - official.sgs_21129_rate) > 0.0075
    )
