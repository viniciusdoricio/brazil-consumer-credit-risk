{% macro clean_label(column) -%}
    {#-
        BCB's files carry a Windows-1252 en dash decoded as the control character U+0096 in one
        sub-modality label, and a doubled space in the rural modality label
        (docs/data-dictionary.md, section 2.1). Both would break joins on the label.
    -#}
    regexp_replace(replace({{ column }}, chr(150), '–'), ' {2,}', ' ', 'g')
{%- endmacro %}
