-- Income bands shift every January with the minimum wage, so a cross-section window must sit
-- inside one calendar year (docs/data-dictionary.md, section 10.5). Returns the windows that
-- span a January.

select window_id, start_month, end_month
from {{ ref('analysis_windows') }}
where kind = 'cross_section' and year(start_month) <> year(end_month)
