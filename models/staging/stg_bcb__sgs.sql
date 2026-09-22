-- The SGS series, one row per series and month. Values are as published: percentages for 21084
-- (household 90-day delinquency), 21129 (household credit-card 90-day delinquency), 24369
-- (unemployment) and 433 (IPCA monthly change), and reais for 1619 (minimum wage).

select
    code as sgs_code,
    cast(date as date) as month,
    value
from {{ source('bcb', 'sgs') }}
