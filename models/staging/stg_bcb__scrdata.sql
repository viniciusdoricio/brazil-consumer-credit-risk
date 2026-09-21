-- SCR.data V2 as published: one row per cell, with a month key. Only the two broken labels are
-- changed (see the clean_label macro); every value is otherwise as BCB released it.

select
    cast(date_trunc('month', data_base) as date) as month,
    data_base,
    uf,
    segmento,
    cliente,
    cnae_ocupacao,
    porte,
    {{ clean_label('modalidade') }} as modalidade,
    {{ clean_label('submodalidade') }} as submodalidade,
    origem,
    indexador,
    numero_de_operacoes,
    a_vencer_ate_90_dias,
    a_vencer_de_91_ate_360_dias,
    a_vencer_de_361_ate_1080_dias,
    a_vencer_de_1081_ate_1800_dias,
    a_vencer_de_1801_ate_5400_dias,
    a_vencer_acima_de_5400_dias,
    carteira_a_vencer,
    vencido_de_15_ate_90_dias,
    vencido_acima_de_90_dias,
    carteira_vencida,
    carteira_ativa,
    carteira_inadimplencia,
    ativo_problematico
from {{ source('bcb', 'scrdata') }}
