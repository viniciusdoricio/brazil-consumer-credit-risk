-- Every month in which an occupation or income band's share of the household portfolio jumps by
-- more than var('weight_jump_threshold') must be in classification_events, for the months each
-- dimension is used in: occupations from January 2017, income bands from January 2017 to December
-- 2024 (docs/v1-decision.md, section 3). A jump in a later release fails the build until someone
-- records it, so a revision can't pass as a change in borrower mix. Returns the unrecorded jumps.

select month, dimension, category, share_before, share_after, change
from {{ ref('analysis_weight_jumps') }}
where
    classification_event is null
    and month >= cast('{{ var("first_comparable_month") }}' as date)
    and (
        dimension = 'occupation'
        or month <= cast('{{ var("d90_last_comparable_month") }}' as date)
    )
