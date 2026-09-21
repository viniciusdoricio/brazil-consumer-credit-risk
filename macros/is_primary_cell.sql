{% macro is_primary_cell(occupation, income_band) -%}
    {#-
        True for the cells v1 compares: named occupations and named income bands. The residual
        categories stay in every total but are left out of comparisons (docs/v1-decision.md,
        section 3); the lists are dbt variables.
    -#}
    (
        {{ occupation }} not in (
            {%- for value in var('residual_occupations') %}'{{ value }}'{{ ", " if not loop.last }}{% endfor -%}
        )
        and {{ income_band }} not in (
            {%- for value in var('residual_income_bands') %}'{{ value }}'{{ ", " if not loop.last }}{% endfor -%}
        )
    )
{%- endmacro %}
