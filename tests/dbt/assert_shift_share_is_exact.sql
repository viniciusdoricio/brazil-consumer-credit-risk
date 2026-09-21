-- Pure rate, product mix and borrower mix add up to the change in the national rate for every
-- comparison (docs/analysis-design.md, section 1.6). Returns the rows where they don't, to 1e-12.

select comparison_id, measure, variant, change, pure_rate, product_mix, borrower_mix
from {{ ref('analysis_shift_share') }}
where
    abs(change - (pure_rate + product_mix + borrower_mix)) > 1e-12
    or change is null
    or pure_rate is null
    or product_mix is null
    or borrower_mix is null
