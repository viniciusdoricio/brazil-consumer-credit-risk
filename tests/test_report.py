import re
from datetime import date
from pathlib import Path

import pytest

from brazil_consumer_credit_risk import report
from brazil_consumer_credit_risk.charts.language import EN, LANGUAGES, PT

ANALYSIS = Path(__file__).resolve().parents[1] / "analysis"
DOCUMENTS = {"pt": ANALYSIS / "index.qmd", "en": ANALYSIS / "en" / "index.qmd"}


def cited(path: Path) -> set[str]:
    return set(re.findall(r"`\{python\} N\.(\w+)`", path.read_text()))


def sample() -> dict:
    """Facts shaped like report.facts(), for a data release that matches the text."""
    return {
        "months": 169,
        "first_month": date(2012, 7, 1),
        "latest_month": date(2026, 7, 1),
        "portfolio_bn": 4680.6,
        "sgs_gap_low": -0.0009,
        "sgs_gap_high": 0.0013,
        "rural_self_employed": 0.423,
        "outros_low": 0.241,
        "outros_high": 0.267,
        "unexplained_jumps": 9,
        "occupations": 8,
        "income_bands": 9,
        "product_groups": 7,
        "min_cell_balance_bn": 1.0,
        "max_crosswalk_shift": 0.25,
        "weight_jump_threshold": 0.005,
        "material": 0.001,
        "bcb_regulatory_pp": 0.53,
        "bcb_total_pp": 0.78,
        "d90_step_january_2025": 0.0031,
        "d90_step_january_2024": 0.0003,
        "d15_step_january_2025": 0.0003,
        "d15_step_january_2024": 0.0001,
        "break_visible": True,
        "d15_flat": True,
        "largest_spread": {
            "spread": 0.0254,
            "highest": "MEI",
            "lowest": "Empregado de empresa privada",
            "income_band": "Acima de 20 salários mínimos",
        },
        "smallest_spread": 0.0186,
        "small_cells": 7,
        "small_cell_occupations": [report.NON_PROFIT],
        "bands_shown": 7,
        "top_two_riskiest": 5,
        "safest": 5,
        "verdict": "income",
        "ratios": [0.62, 0.43, 0.48],
        "every_year_below_one": True,
        "unemployment_correlation": 0.46,
        "years": 8,
        "d15_years_above_one": ["2024"],
        "stable_bands": ["Mais de 1 a 2 salários mínimos", "Mais de 2 a 3 salários mínimos"],
        "product_mix_share": 0.14,
        "product_mix_share_excluding_rural": 0.30,
        "material_splits": 19,
        "stable_by_pair": {
            "retiree_vs_self_employed": 4,
            "public_vs_private_employee": 2,
            "mei_vs_business_owner": 3,
        },
        "pair_shares": {
            "retiree_vs_self_employed": 0.14,
            "public_vs_private_employee": 0.32,
            "mei_vs_business_owner": 0.25,
        },
        "top_product": "Cartão",
        "top_product_share": 0.36,
        "widest_rate_gap": "Cartão",
        "self_employed_higher_everywhere": True,
        "product_rates": {"Cartão": (0.085, 0.049), "Consignado": (0.031, 0.019)},
        "episodes": 3,
        "dominant_components": ["pure_rate"],
        "episodes_with_reclassification": ["2023–2024"],
        "pure_low": 0.82,
        "pure_high": 1.15,
        "mix_max": 0.18,
        "flagged_borrower_mix": 0.0003,
        "fastest": "Autônomo",
        "fastest_with_lagged_denominator": "Autônomo",
        "fastest_change": 0.0053,
        "fastest_growth": 0.093,
        "slowest": "Aposentado/pensionista",
        "slowest_change": 0.0015,
        "slowest_growth": -0.037,
        "all_rising": True,
        "outros_balance_share": 0.255,
        "outros_loan_share": 0.508,
        "outros_lowest_band_share": 0.558,
        "retiree_above_one_wage_share": 0.92,
        "private_payroll_before_bn": 53.0,
        "private_payroll_latest_bn": 94.0,
        "private_payroll_d15_before": 0.0051,
        "private_payroll_d15_latest": 0.0079,
        **report.EXTERNAL,
    }


def test_both_languages_cite_the_same_figures():
    assert cited(DOCUMENTS["pt"]) == cited(DOCUMENTS["en"])


@pytest.mark.parametrize("code", list(LANGUAGES))
def test_every_cited_figure_exists_and_every_figure_is_cited(code):
    assert set(report.values(sample(), LANGUAGES[code])) == cited(DOCUMENTS[code])


def test_the_two_languages_format_the_same_facts():
    pt, en = report.values(sample(), PT), report.values(sample(), EN)
    assert pt["grid_spread"] == "2,5 p.p." and en["grid_spread"] == "2.5 pp"
    assert pt["portfolio"] == "R$ 4,7 trilhões" and en["portfolio"] == "R$4.7 trillion"
    assert pt["fastest"] == "autônomos" and en["fastest"] == "the self-employed"
    assert pt["split_band_names"] == "1 a 2 e 2 a 3 salários mínimos"
    assert en["split_band_names"] == "1 to 2 and 2 to 3 minimum wages"


def test_check_passes_when_the_results_match_the_text():
    report.check(sample())


@pytest.mark.parametrize(
    ("change", "claim"),
    [
        ({"verdict": "occupation"}, "income separates risk more in all three windows"),
        ({"product_mix_share": 0.6}, "little of the retiree-self-employed gap"),
        ({"fastest_with_lagged_denominator": "MEI"}, "the fastest riser is the same"),
        ({"d15_years_above_one": []}, "disagrees in exactly one year"),
        ({"dominant_components": ["product_mix"]}, "within occupation and product"),
        ({"outros_loan_share": 0.2}, "Outros holds a larger share of loans"),
        ({"private_payroll_d15_latest": 0.004}, "private-sector payroll loans grew"),
    ],
)
def test_check_names_the_claim_that_no_longer_holds(change, claim):
    with pytest.raises(AssertionError, match=claim):
        report.check({**sample(), **change})
