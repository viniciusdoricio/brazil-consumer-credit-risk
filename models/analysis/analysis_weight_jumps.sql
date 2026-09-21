-- Every month in which an occupation or income band's share of the household portfolio moved by
-- more than var('weight_jump_threshold'): the rule the design uses to tell reclassification from
-- lending (docs/analysis-design.md, section 1.5). Each jump is matched to classification_events,
-- and a test fails on any that isn't there, so a revision in a later release shows up rather than
-- passing as a change in borrower mix. A category missing in a month counts as a zero share.

with balances as (
    select month, 'occupation' as dimension, occupation as category, sum(carteira_ativa) as balance
    from {{ ref('int_pf_cells') }}
    group by all
    union all
    select month, 'income', income_band, sum(carteira_ativa)
    from {{ ref('int_pf_cells') }}
    group by all
),

grid as (
    select months.month, categories.dimension, categories.category
    from (select distinct month from balances) as months
    cross join (select distinct dimension, category from balances) as categories
),

shares as (
    select
        grid.month,
        grid.dimension,
        grid.category,
        coalesce(balances.balance, 0)
        / sum(coalesce(balances.balance, 0)) over (partition by grid.month, grid.dimension) as share
    from grid
    left join balances
        on grid.month = balances.month
        and grid.dimension = balances.dimension
        and grid.category = balances.category
),

changes as (
    select
        month,
        dimension,
        category,
        lag(share) over (partition by dimension, category order by month) as share_before,
        share as share_after
    from shares
)

select
    changes.month,
    changes.dimension,
    changes.category,
    changes.share_before,
    changes.share_after,
    changes.share_after - changes.share_before as change,
    events.description as classification_event
from changes
left join {{ ref('classification_events') }} as events
    on changes.month = events.month
    and changes.dimension = events.dimension
where abs(changes.share_after - changes.share_before) > {{ var('weight_jump_threshold') }}
