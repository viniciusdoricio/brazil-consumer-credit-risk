"""Each chart's headline, chosen from the data.

The v1 decision wrote every headline in advance as a claim with a slot, with the headline that
replaces it if the data says the opposite (docs/v1-decision.md, section 4). These functions fill
the slot and pick the branch from the analysis models, using thresholds fixed here rather than
chosen after looking. Each returns the headline, a subtitle that states the numbers behind it,
and those numbers as facts, which the write-up cites.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from .style import (
    INCOME_BANDS,
    OCCUPATIONS_IN_TEXT,
    PAIRS,
    in_words,
    month_label,
    number,
    pct,
    pp,
)

# A rate difference under 0.1 pp counts as no difference, as in analysis_gap_decomposition.
MATERIAL = 0.001
# The dbt test's definition of a visible January 2025 break
# (tests/dbt/assert_january_2025_break_exists.sql).
BREAK_D90_STEP = 0.0025
BREAK_D90_MULTIPLE = 5
BREAK_D15_TOLERANCE = 0.001
# The v1 decision's falsification rule: a product-mix part above half the gap means the gap is
# mostly about which products each group holds (docs/v1-decision.md, section 6).
PRODUCT_MIX_MAJORITY = 0.5
PRODUCT_MIX_LITTLE = 0.25
# A correlation at least this strong, either way, across the calendar years counts as the
# occupation spread moving with unemployment. Eight points can't support a finer reading.
UNEMPLOYMENT_CORRELATION = 0.5
# A component explains a change "mostly" when it has the change's sign and over half its size.
MOSTLY = 0.5

INCOME_IN_TEXT = {
    "Até 1 salário mínimo": "até 1 salário mínimo",
    "Mais de 1 a 2 salários mínimos": "de 1 a 2 salários mínimos",
    "Mais de 2 a 3 salários mínimos": "de 2 a 3 salários mínimos",
    "Mais de 3 a 5 salários mínimos": "de 3 a 5 salários mínimos",
    "Mais de 5 a 10 salários mínimos": "de 5 a 10 salários mínimos",
    "Mais de 10 a 20 salários mínimos": "de 10 a 20 salários mínimos",
    "Acima de 20 salários mínimos": "acima de 20 salários mínimos",
}

COMPONENTS = {
    "pure_rate": "dentro de cada ocupação e produto",
    "product_mix": "da mudança no mix de produtos",
    "borrower_mix": "da mudança no mix de ocupações",
}


@dataclass
class Headline:
    title: str
    subtitle: str
    facts: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # A sentence that ends on "p.p." takes no second full stop.
        self.subtitle = self.subtitle.replace("p.p..", "p.p.")


def _at(frame: pd.DataFrame, column: str, month: str) -> float:
    rows = frame.loc[pd.to_datetime(frame["month"]) == pd.Timestamp(month), column]
    if len(rows) != 1:
        raise ValueError(f"expected one row for {month}, found {len(rows)}")
    return float(rows.iloc[0])


def the_trap(monthly: pd.DataFrame) -> Headline:
    """Chart 1. monthly: mart_pf_monthly (month, d90_rate, d15_rate)."""
    d90 = _at(monthly, "d90_rate", "2025-01-01") - _at(monthly, "d90_rate", "2024-12-01")
    d90_before = _at(monthly, "d90_rate", "2024-01-01") - _at(monthly, "d90_rate", "2023-12-01")
    d15 = _at(monthly, "d15_rate", "2025-01-01") - _at(monthly, "d15_rate", "2024-12-01")
    d15_before = _at(monthly, "d15_rate", "2024-01-01") - _at(monthly, "d15_rate", "2023-12-01")
    visible = d90 >= BREAK_D90_STEP and d90 >= BREAK_D90_MULTIPLE * abs(d90_before)
    flat = abs(d15) <= BREAK_D15_TOLERANCE

    if not visible:
        title = (
            "A mudança contábil de janeiro de 2025 não aparece como salto na inadimplência de "
            "90 dias das famílias"
        )
    elif flat:
        title = (
            "Parte da alta da inadimplência das famílias desde janeiro de 2025 vem de uma "
            "mudança contábil, não dos devedores; a de 15 a 90 dias não saltou"
        )
    else:
        title = (
            "Parte da alta da inadimplência das famílias desde janeiro de 2025 vem de uma "
            "mudança contábil, e até a de 15 a 90 dias saltou naquele mês"
        )
    subtitle = (
        "Inadimplência das pessoas físicas, % da carteira. De dezembro de 2024 para janeiro de "
        f"2025, a de 90 dias variou {pp(d90, sign=True)} (no janeiro anterior, "
        f"{pp(d90_before, sign=True)}) e a de 15 a 90 dias, {pp(d15, sign=True)} "
        f"({pp(d15_before, sign=True)})."
    )
    return Headline(
        title,
        subtitle,
        {
            "d90_step_january_2025": d90,
            "d90_step_january_2024": d90_before,
            "d15_step_january_2025": d15,
            "d15_step_january_2024": d15_before,
            "break_visible": visible,
            "d15_flat": flat,
        },
    )


def the_grid(grid: pd.DataFrame, period: str) -> Headline:
    """Chart 2. grid: analysis_grid rows for one window and the primary grid."""
    cells = grid[~grid["below_minimum_size"] & grid["income_band"].isin(INCOME_BANDS)]
    spreads = []
    for band, group in cells.groupby("income_band"):
        top = group.loc[group["d90_rate"].idxmax()]
        bottom = group.loc[group["d90_rate"].idxmin()]
        spreads.append(
            {
                "income_band": band,
                "highest": top["occupation"],
                "lowest": bottom["occupation"],
                "spread": float(top["d90_rate"] - bottom["d90_rate"]),
                "holds_with_lag": bool(top["d90_rate_lagged"] > bottom["d90_rate_lagged"]),
            }
        )
    held = [s for s in spreads if s["holds_with_lag"]]
    largest = max(held, key=lambda s: s["spread"], default=None)

    if largest is None or largest["spread"] < MATERIAL:
        title = "Dentro de uma mesma faixa de renda, a ocupação quase não muda a inadimplência"
        subtitle = (
            f"Inadimplência de 90 dias em {period}, por ocupação e faixa de renda, % da carteira. "
            "Em nenhuma faixa a diferença entre ocupações chega a 0,1 p.p. com a ordem mantida "
            "pelo denominador defasado."
        )
        return Headline(title, subtitle, {"spreads": spreads})

    smallest = min(s["spread"] for s in spreads)
    title = (
        "Na mesma faixa de renda, a inadimplência de 90 dias varia até "
        f"{pp(largest['spread'], 1)} conforme a ocupação"
    )
    subtitle = (
        f"Inadimplência de 90 dias em {period}, por ocupação e faixa de renda, % da carteira. A "
        f"maior diferença é entre {OCCUPATIONS_IN_TEXT[largest['highest']]} e "
        f"{OCCUPATIONS_IN_TEXT[largest['lowest']]} com renda "
        f"{INCOME_IN_TEXT[largest['income_band']]}. Mesmo na faixa em que as ocupações ficam "
        f"mais próximas, a diferença é de {pp(smallest)}."
    )
    return Headline(
        title,
        subtitle,
        {"largest_spread": largest, "smallest_spread": smallest, "spreads": spreads},
    )


def which_matters_more(dispersion: pd.DataFrame) -> Headline:
    """Chart 3. dispersion: analysis_dispersion, primary variant."""
    d90 = dispersion[dispersion["measure"] == "d90"]
    windows = d90[d90["period_kind"] == "window"].sort_values("start_month")
    years = d90[d90["period_kind"] == "calendar_year"].sort_values("start_month")
    ratios = windows["occupation_to_income_ratio"].tolist()

    if all(r < 1 for r in ratios):
        verdict = "income"
        title = "Na inadimplência de 90 dias, a renda separa o risco mais do que a ocupação"
    elif all(r > 1 for r in ratios):
        verdict = "occupation"
        title = "Na inadimplência de 90 dias, a ocupação separa o risco mais do que a renda"
    else:
        verdict = "mixed"
        title = "Na inadimplência de 90 dias, nem a ocupação nem a renda separa sempre mais o risco"

    correlation = float(
        years["spread_across_occupations_within_bands"].corr(years["unemployment_rate"])
    )
    if correlation >= UNEMPLOYMENT_CORRELATION:
        title += ", e a distância entre ocupações acompanhou o desemprego"
    elif correlation <= -UNEMPLOYMENT_CORRELATION:
        title += ", e a distância entre ocupações andou na contramão do desemprego"
    else:
        title += ", e a distância entre ocupações não acompanhou o desemprego"

    d15_years = dispersion[
        (dispersion["measure"] == "d15")
        & (dispersion["period_kind"] == "calendar_year")
        & (dispersion["occupation_to_income_ratio"] > 1)
    ]["period_id"].tolist()
    window_names = ", ".join(_window_name(row) for _, row in windows.iterrows())
    subtitle = (
        "Dispersão da inadimplência de 90 dias entre ocupações, dentro de cada faixa de renda, "
        "dividida pela dispersão entre faixas, dentro de cada ocupação: abaixo de 1, a renda "
        f"separa mais. Nos recortes do teste ({window_names}), a razão foi "
        f"{_join(number(r) for r in ratios)}. Correlação da dispersão entre ocupações com o "
        f"desemprego, {years['period_id'].iloc[0]} a {years['period_id'].iloc[-1]}: "
        f"{number(correlation)} ({in_words(len(years))} anos)."
    )
    if d15_years:
        subtitle += f" Na inadimplência de 15 a 90 dias, a razão passa de 1 em {_join(d15_years)}."
    return Headline(
        title,
        subtitle,
        {
            "verdict": verdict,
            "window_ratios": dict(zip(windows["period_id"], ratios, strict=True)),
            "unemployment_correlation": correlation,
            "d15_years_above_one": d15_years,
        },
    )


def _window_name(row) -> str:
    start, end = pd.Timestamp(row["start_month"]), pd.Timestamp(row["end_month"])
    if start.month == 1 and end.month == 12:
        return str(start.year)
    return f"{month_label(start)[:3]}–{month_label(end)}"


def _join(items) -> str:
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " e " + items[-1]


def stable_bands(gaps: pd.DataFrame, pair: str, scope: str) -> pd.DataFrame:
    """The bands where a pair's split can be read: a material gap, above the minimum size, in the
    same order with lagged denominators, and stable under the alternative product mapping."""
    rows = gaps[
        (gaps["pair_id"] == pair)
        & (gaps["product_scope"] == scope)
        & gaps["income_band"].isin(INCOME_BANDS)
    ]
    return rows[
        ~rows["below_minimum_size"]
        & (rows["gap"].abs() >= MATERIAL)
        & rows["gap_sign_holds_with_lag"].fillna(False).astype(bool)
        & rows["split_holds_under_alternative_mapping"].fillna(False).astype(bool)
    ]


def product_mix_share(bands: pd.DataFrame) -> float | None:
    """The product-mix part of the gap summed over bands, as a share of the summed gap; None if
    there are no bands or the gap changes sign between them, where a share means nothing."""
    if bands.empty or not ((bands["gap"] > 0).all() or (bands["gap"] < 0).all()):
        return None
    return float(bands["product_mix_gap"].sum() / bands["gap"].sum())


def job_or_product(
    gaps: pd.DataFrame, period: str, pair: str = "retiree_vs_self_employed"
) -> Headline:
    """Chart 4. gaps: analysis_gap_decomposition rows for one window."""
    a, b = PAIRS[pair]
    bands = stable_bands(gaps, pair, "all_products")
    share = product_mix_share(bands)
    share_without_rural = product_mix_share(stable_bands(gaps, pair, "excluding_rural"))

    if share is None:
        title = (
            f"Para {a} e {b}, a divisão entre ocupação e produto não é estável o bastante para "
            "uma conclusão"
        )
    elif share > PRODUCT_MIX_MAJORITY:
        title = (
            f"A maior parte da diferença entre {a} e {b} vem dos produtos de crédito de cada grupo"
        )
    elif share > PRODUCT_MIX_LITTLE:
        title = (
            f"Menos da metade da diferença entre {a} e {b} vem dos produtos de crédito de cada "
            "grupo"
        )
    else:
        title = (
            f"Pouco da diferença entre {a} e {b} vem dos produtos de crédito de cada grupo: ela "
            "aparece dentro dos mesmos produtos"
        )

    subtitle = (
        f"Diferença na inadimplência de 90 dias em {period} entre {a} e {b}, por faixa de renda, "
        "dividida entre a parte dentro dos mesmos produtos e a parte que vem do mix de produtos."
    )
    if share is not None:
        lower = a if bands["gap"].iloc[0] < 0 else b
        where = (
            "Na única faixa em que a divisão é estável"
            if len(bands) == 1
            else f"Nas {in_words(len(bands), feminine=True)} faixas em que a divisão é estável"
        )
        subtitle += (
            f" {where}, {lower} têm a menor taxa, e o mix de produtos responde por "
            f"{pct(share, 0)} da diferença"
        )
        subtitle += (
            f"; sem o crédito rural, por {pct(share_without_rural, 0)}."
            if share_without_rural is not None
            else "."
        )
    return Headline(
        title,
        subtitle,
        {
            "pair": pair,
            "stable_bands": [b for b in INCOME_BANDS if b in set(bands["income_band"])],
            "product_mix_share": share,
            "product_mix_share_excluding_rural": share_without_rural,
        },
    )


def _episode_name(row) -> str:
    return f"{pd.Timestamp(row['month_0']).year}–{pd.Timestamp(row['month_1']).year}"


def dominant_component(row) -> str | None:
    """The component that explains most of an episode's change, or None if none does."""
    change = row["change"]
    name = max(COMPONENTS, key=lambda c: abs(row[c]))
    value = row[name]
    if abs(change) >= MATERIAL and value * change > 0 and abs(value) > MOSTLY * abs(change):
        return name
    return None


def mix_versus_rate(episodes: pd.DataFrame) -> Headline:
    """Chart 5. episodes: analysis_shift_share, 90-day episodes, all occupations."""
    episodes = episodes.sort_values("month_0")
    dominant = [dominant_component(row) for _, row in episodes.iterrows()]
    first = pd.Timestamp(episodes["month_0"].iloc[0]).year
    last = pd.Timestamp(episodes["month_1"].iloc[-1]).year

    if dominant and dominant[0] is not None and len(set(dominant)) == 1:
        title = (
            f"Em cada um dos {in_words(len(episodes))} episódios de {first} a {last}, a "
            f"inadimplência de 90 dias das famílias mudou sobretudo {COMPONENTS[dominant[0]]}"
        )
    else:
        biggest = episodes.loc[episodes["change"].abs().idxmax()]
        which = dominant_component(biggest)
        direction = "alta" if biggest["change"] > 0 else "queda"
        title = (
            f"A {direction} de {pp(abs(biggest['change']))} na inadimplência de 90 dias das "
            f"famílias em {_episode_name(biggest)} "
        )
        title += f"veio sobretudo {COMPONENTS[which]}" if which else "não teve uma fonte dominante"

    changes = "; ".join(
        f"{_episode_name(row)}, {pp(row['change'], sign=True)}" for _, row in episodes.iterrows()
    )
    subtitle = (
        "Variação da inadimplência de 90 dias das pessoas físicas em cada episódio, dividida em "
        "três partes que somam exatamente a variação: taxa dentro de cada ocupação e produto, mix "
        f"de produtos e mix de ocupações. Variação total: {changes}."
    )
    flagged = [
        _episode_name(row)
        for _, row in episodes.iterrows()
        if row["spans_occupation_reclassification"]
    ]
    if flagged:
        subtitle += (
            f" {_join(f'{name}*' for name in flagged)}: há uma reclassificação de ocupações dentro "
            "do episódio, e ela entra no mix de ocupações."
        )
    return Headline(
        title,
        subtitle,
        {
            "dominant_component": dict(zip(episodes["comparison_id"], dominant, strict=True)),
            "episodes_with_reclassification": flagged,
        },
    )


def current_read(current: pd.DataFrame) -> Headline:
    """Chart 6. current: analysis_current_read, named occupations."""
    latest = pd.Timestamp(current["latest_month"].iloc[0]).date()
    spread = float(current["d15_change"].max() - current["d15_change"].min())
    fastest = current.loc[current["d15_change"].idxmax()]
    fastest_lagged = current.loc[current["d15_change_lagged"].idxmax(), "occupation"]
    base = (
        "Variação da inadimplência de 15 a 90 dias entre 2024 e os 12 meses até "
        f"{month_label(latest)}, por ocupação, ao lado da variação real do saldo (IPCA)."
    )

    if spread < MATERIAL:
        title = (
            "Desde a mudança contábil, a inadimplência de 15 a 90 dias subiu de forma parecida "
            "em todas as ocupações"
        )
    elif fastest_lagged != fastest["occupation"]:
        title = (
            "Desde a mudança contábil, a inadimplência de 15 a 90 dias subiu de forma desigual, "
            "mas qual ocupação subiu mais depende do denominador"
        )
    else:
        growth = "continuou crescendo" if fastest["real_balance_growth"] > 0 else "encolheu"
        title = (
            "Desde a mudança contábil, a inadimplência de 15 a 90 dias subiu mais entre "
            f"{OCCUPATIONS_IN_TEXT[fastest['occupation']]}, e o crédito a eles {growth} em "
            "termos reais"
        )
    who = OCCUPATIONS_IN_TEXT[fastest["occupation"]]
    subtitle = base + (
        f" Entre {who}: {pp(fastest['d15_change'], sign=True)} na taxa e "
        f"{pct(fastest['real_balance_growth'], sign=True)} no saldo; entre as ocupações, a alta "
        f"vai de {pp(current['d15_change'].min())} a {pp(current['d15_change'].max())}."
    )
    tightening = current.loc[current["possible_tightening"], "occupation"].tolist()
    if tightening:
        subtitle += (
            f" Taxa e saldo em queda juntos ({_join(OCCUPATIONS_IN_TEXT[o] for o in tightening)}) "
            "sugerem crédito mais restrito, não devedores melhores."
        )
    return Headline(
        title,
        subtitle,
        {
            "latest_month": latest.isoformat(),
            "fastest": fastest["occupation"],
            "fastest_with_lagged_denominator": fastest_lagged,
            "spread": spread,
            "possible_tightening": tightening,
        },
    )


def as_of(latest: date) -> str:
    return f"Dados até {month_label(latest)}."
