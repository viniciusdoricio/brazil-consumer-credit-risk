from datetime import date

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from brazil_consumer_credit_risk.charts import cli, headlines  # noqa: E402
from brazil_consumer_credit_risk.charts.style import (  # noqa: E402
    INCOME_BANDS,
    in_words,
    number,
    pct,
    pp,
)

BANDS = list(INCOME_BANDS)


def test_numbers_use_the_brazilian_format():
    assert number(1234.5, 1) == "1.234,5"
    assert number(-0.314) == "−0,31"
    assert number(0.004, sign=True) == "+0,00"
    assert number(-0.004) == "0,00"
    assert pp(0.0031, sign=True) == "+0,31 p.p."
    assert pct(0.0928, sign=True) == "+9,3%"
    assert in_words(3) == "três" and in_words(2, feminine=True) == "duas"


def monthly(d90_step=0.0031, d90_before=0.0003, d15_step=0.0003):
    months = pd.date_range("2016-06-01", "2026-07-01", freq="MS")
    frame = pd.DataFrame(
        {"month": months, "d90_rate": 0.037, "d15_rate": 0.009, "sgs_21084_rate": 0.036}
    )
    frame.loc[frame["month"] >= "2024-01-01", "d90_rate"] += d90_before
    frame.loc[frame["month"] >= "2025-01-01", "d90_rate"] += d90_step
    frame.loc[frame["month"] >= "2025-01-01", "d15_rate"] += d15_step
    return frame


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({}, "não saltou"),
        ({"d15_step": 0.004}, "até a de 15 a 90 dias saltou"),
        ({"d90_step": 0.001}, "não aparece como salto"),
        ({"d90_before": 0.001}, "não aparece como salto"),
    ],
)
def test_the_trap_follows_the_break_test(kwargs, expected):
    assert expected in headlines.the_trap(monthly(**kwargs)).title


def grid(rates: dict[str, list[float]], lagged_offset=0.0, flip_band=None, small=()):
    rows = []
    for occupation, values in rates.items():
        for band, rate in zip(BANDS, values, strict=True):
            lag = rate + lagged_offset
            if band == flip_band and occupation == "MEI":
                lag = 0.0
            rows.append(
                {
                    "occupation": occupation,
                    "income_band": band,
                    "d90_rate": rate,
                    "d90_rate_lagged": lag,
                    "d15_rate": rate / 4,
                    "average_balance_bn": 10.0,
                    "below_minimum_size": occupation in small,
                    "in_primary_grid": True,
                }
            )
    return pd.DataFrame(rows)


def test_the_grid_reports_the_largest_gap_whose_order_survives_the_lag():
    rates = {"MEI": [0.06] * 6 + [0.08], "Autônomo": [0.03] * 7}
    result = headlines.the_grid(grid(rates), "2024")
    assert "até 5,0 p.p." in result.title

    flipped = headlines.the_grid(grid(rates, flip_band=BANDS[-1]), "2024")
    assert "até 3,0 p.p." in flipped.title


def test_the_grid_says_so_when_occupation_barely_matters():
    rates = {"MEI": [0.0305] * 7, "Autônomo": [0.03] * 7}
    assert "quase não muda" in headlines.the_grid(grid(rates), "2024").title


def dispersion(window_ratios, occupation_spreads, unemployment):
    rows = []
    for (period, start, end), ratio in zip(
        [
            ("cs_2019", "2019-03-01", "2019-12-01"),
            ("cs_2022", "2022-01-01", "2022-12-01"),
            ("cs_2024", "2024-01-01", "2024-12-01"),
        ],
        window_ratios,
        strict=True,
    ):
        rows.append(("window", period, start, end, "d90", ratio, 0.005, 0.1))
    for year, spread, rate in zip(range(2017, 2025), occupation_spreads, unemployment, strict=True):
        start, end = f"{year}-01-01", f"{year}-12-01"
        rows.append(("calendar_year", str(year), start, end, "d90", 0.6, spread, rate))
        rows.append(("calendar_year", str(year), start, end, "d15", 0.7, spread, rate))
    frame = pd.DataFrame(
        rows,
        columns=[
            "period_kind",
            "period_id",
            "start_month",
            "end_month",
            "measure",
            "occupation_to_income_ratio",
            "spread_across_occupations_within_bands",
            "unemployment_rate",
        ],
    )
    frame["start_month"] = pd.to_datetime(frame["start_month"])
    frame["end_month"] = pd.to_datetime(frame["end_month"])
    frame["spread_across_bands_within_occupations"] = 0.01
    frame["reclassifications_inside"] = 0
    return frame


RISING = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]


@pytest.mark.parametrize(
    ("ratios", "spreads", "expected"),
    [
        ([0.6, 0.4, 0.5], RISING, "a renda separa o risco mais"),
        ([1.2, 1.1, 1.3], RISING, "a ocupação separa o risco mais"),
        ([0.9, 1.1, 0.8], RISING, "nem a ocupação nem a renda"),
        ([0.6, 0.4, 0.5], RISING, "acompanhou o desemprego"),
        ([0.6, 0.4, 0.5], RISING[::-1], "na contramão do desemprego"),
        ([0.6, 0.4, 0.5], [0.5, 0.1, 0.5, 0.1, 0.5, 0.1, 0.5, 0.1], "não acompanhou"),
    ],
)
def test_which_matters_more_uses_the_three_windows(ratios, spreads, expected):
    frame = dispersion(ratios, spreads, [x / 10 for x in RISING])
    assert expected in headlines.which_matters_more(frame).title


def gaps(mix_share=0.1, stable=True, lag_holds=True):
    rows = []
    for pair in ("retiree_vs_self_employed", "public_vs_private_employee", "mei_vs_business_owner"):
        for scope in ("all_products", "excluding_rural"):
            for band in BANDS:
                gap = -0.02
                rows.append(
                    {
                        "pair_id": pair,
                        "product_scope": scope,
                        "income_band": band,
                        "gap": gap,
                        "product_mix_gap": gap * mix_share,
                        "same_product_gap": gap * (1 - mix_share),
                        "gap_sign_holds_with_lag": lag_holds,
                        "split_holds_under_alternative_mapping": stable,
                        "below_minimum_size": False,
                    }
                )
    return pd.DataFrame(rows)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"mix_share": 0.7}, "A maior parte da diferença"),
        ({"mix_share": 0.4}, "Menos da metade"),
        ({"mix_share": 0.1}, "Pouco da diferença"),
        ({"stable": False}, "não é estável"),
        ({"lag_holds": False}, "não é estável"),
    ],
)
def test_job_or_product_applies_the_falsification_rule(kwargs, expected):
    assert expected in headlines.job_or_product(gaps(**kwargs), "2024").title


def test_product_mix_share_refuses_gaps_of_both_signs():
    bands = pd.DataFrame({"gap": [0.01, -0.02], "product_mix_gap": [0.001, -0.001]})
    assert headlines.product_mix_share(bands) is None


def episodes(components):
    rows = []
    for i, (pure, product, borrower) in enumerate(components):
        rows.append(
            {
                "comparison_id": f"ep_{i}",
                "month_0": pd.Timestamp(f"{2018 + 3 * i}-01-01"),
                "month_1": pd.Timestamp(f"{2020 + 3 * i}-12-01"),
                "pure_rate": pure,
                "product_mix": product,
                "borrower_mix": borrower,
                "change": pure + product + borrower,
                "spans_occupation_reclassification": i == 2,
            }
        )
    return pd.DataFrame(rows)


def test_mix_versus_rate_names_a_shared_dominant_source():
    frame = episodes([(-0.01, 0.001, 0.0), (0.008, 0.001, 0.0), (-0.004, 0.0, 0.0003)])
    result = headlines.mix_versus_rate(frame)
    assert result.title.startswith("Em cada um dos três episódios")
    assert "dentro de cada ocupação e produto" in result.title
    assert "2024–2026*" in result.subtitle


def test_mix_versus_rate_falls_back_to_the_biggest_episode():
    frame = episodes([(-0.012, 0.001, 0.0), (0.001, 0.008, 0.0), (-0.004, 0.0, 0.0003)])
    title = headlines.mix_versus_rate(frame).title
    assert title.startswith("A queda de 1,10 p.p.")
    assert "dentro de cada ocupação e produto" in title


def current(changes, lagged=None, growth=0.05):
    occupations = ["Autônomo", "MEI", "Empresário"]
    return pd.DataFrame(
        {
            "occupation": occupations,
            "latest_month": date(2026, 7, 1),
            "d15_change": changes,
            "d15_change_lagged": lagged or changes,
            "real_balance_growth": growth,
            "possible_tightening": [False, False, True],
            "named_occupation": True,
        }
    )


@pytest.mark.parametrize(
    ("frame", "expected"),
    [
        (
            current([0.005, 0.002, 0.001]),
            "subiu mais entre autônomos, e o crédito a eles continuou",
        ),
        (current([0.005, 0.002, 0.001], growth=-0.02), "encolheu"),
        (current([0.005, 0.002, 0.001], lagged=[0.001, 0.006, 0.001]), "depende do denominador"),
        (current([0.0015, 0.001, 0.0012]), "de forma parecida"),
    ],
)
def test_current_read_checks_the_ranking_with_the_lag(frame, expected):
    assert expected in headlines.current_read(frame).title


def test_subtitles_never_end_on_a_double_full_stop():
    assert "p.p.." not in headlines.current_read(current([0.005, 0.002, 0.001])).subtitle


def test_every_chart_builds_with_its_headline_as_the_title():
    grid_rates = {
        occupation: [0.03 + 0.001 * i + 0.002 * j for j in range(7)]
        for i, occupation in enumerate(
            [
                "Aposentado/pensionista",
                "Autônomo",
                "MEI",
                "Empresário",
                "Empregado de empresa privada",
                "Servidor ou empregado público",
            ]
        )
    }
    frames = {
        "monthly": monthly(),
        "grid": grid(grid_rates),
        "dispersion": dispersion([0.6, 0.4, 0.5], RISING, [x / 10 for x in RISING]),
        "gaps": gaps(),
        "episodes": episodes([(-0.01, 0.001, 0.0), (0.008, 0.001, 0.0), (-0.004, 0.0, 0.0003)]),
        "current": current([0.005, 0.002, 0.001]),
    }
    built = cli.build(frames)
    assert len(built) == 6
    for headline, fig in built.values():
        title = fig.texts[0].get_text()
        assert " ".join(title.split()) == headline.title
        plt.close(fig)
