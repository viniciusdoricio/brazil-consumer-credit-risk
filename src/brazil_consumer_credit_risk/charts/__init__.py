"""The six v1 charts (docs/v1-decision.md, section 4), built from the dbt analysis models.

Each chart's headline is chosen from the data by a function in `headlines`, between the claim the
v1 decision wrote in advance and the one that replaces it if the data says the opposite, so no
headline or number is written by hand. Text is in Portuguese, the write-up's language, and all of
it lives in `style` and `headlines`.
"""
