"""Build the six charts from the dbt database.

    uv run make-charts                       reads data/brazil_consumer_credit_risk.duckdb
    uv run make-charts --out analysis/figures

Writes, for each language, one PNG per chart and headlines.json, which holds each chart's
headline, subtitle and the numbers behind them, into <out>/pt and <out>/en. Needs a full build
(make fetch, make build): the charts span 2016 to the latest month.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import duckdb
import matplotlib
import yaml

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import figures, headlines  # noqa: E402
from .language import LANGUAGES, PT, Language  # noqa: E402
from .style import use_style  # noqa: E402

log = logging.getLogger("make-charts")

# The headline cross-section: calendar 2024, the last full year before the accounting change
# (docs/v1-decision.md, section 3).
HEADLINE_WINDOW = "cs_2024"
HEADLINE_PERIOD = "2024"
# Chart 1 starts when the reporting threshold fell to R$200, the start of the comparable national
# series (docs/v1-decision.md, section 4).
TRAP_START = "2016-06-01"
# Design parameters the chart notes quote, read from where the models take them.
_DESIGN = yaml.safe_load((Path(__file__).parents[3] / "dbt_project.yml").read_text())["vars"]
MIN_CELL_BALANCE_BN = _DESIGN["min_cell_balance_bn"]
MAX_CROSSWALK_SHIFT = _DESIGN["max_crosswalk_shift"]

QUERIES = {
    "monthly": f"""
        select month, d90_rate, d15_rate, sgs_21084_rate
        from mart_pf_monthly where month >= date '{TRAP_START}' order by month""",
    "grid": f"""
        select * from analysis_grid
        where window_id = '{HEADLINE_WINDOW}' and in_primary_grid""",
    "dispersion": "select * from analysis_dispersion where variant = 'primary'",
    "gaps": f"select * from analysis_gap_decomposition where window_id = '{HEADLINE_WINDOW}'",
    "episodes": """
        select * from analysis_shift_share
        where kind = 'episode' and measure = 'd90' and variant = 'all'""",
    "current": "select * from analysis_current_read where named_occupation",
}


def load(con: duckdb.DuckDBPyConnection) -> dict[str, pd.DataFrame]:
    return {name: con.execute(sql).df() for name, sql in QUERIES.items()}


def build(
    frames: dict[str, pd.DataFrame], lang: Language = PT
) -> dict[str, tuple[headlines.Headline, plt.Figure]]:
    """Every chart's headline and figure in one language, keyed by the file it is saved as."""
    use_style()
    latest = pd.Timestamp(frames["monthly"]["month"].max()).date()
    footer = f"{lang.t('source')} {lang.t('as_of', month=lang.month(latest))}"
    material = lang.pp(headlines.MATERIAL, 1)
    min_cell = lang.number(MIN_CELL_BALANCE_BN, 0)
    specs = {
        "chart1_trap": (
            headlines.the_trap(frames["monthly"], lang),
            figures.the_trap,
            frames["monthly"],
            "",
        ),
        "chart2_grid": (
            headlines.the_grid(frames["grid"], HEADLINE_PERIOD, lang),
            figures.the_grid,
            frames["grid"],
            lang.t("grid.note", min_cell=min_cell),
        ),
        "chart3_dispersion": (
            headlines.which_matters_more(frames["dispersion"], lang),
            figures.which_matters_more,
            frames["dispersion"],
            lang.t("dispersion.note", min_cell=min_cell),
        ),
        "chart4_job_or_product": (
            headlines.job_or_product(frames["gaps"], HEADLINE_PERIOD, lang=lang),
            figures.job_or_product,
            frames["gaps"],
            lang.t("split.note", material=material, shift=lang.pct(MAX_CROSSWALK_SHIFT, 0)),
        ),
        "chart5_mix_vs_rate": (
            headlines.mix_versus_rate(frames["episodes"], lang),
            figures.mix_versus_rate,
            frames["episodes"],
            lang.t("mix.note"),
        ),
        "chart6_current_read": (
            headlines.current_read(frames["current"], lang),
            figures.current_read,
            frames["current"],
            lang.t("current.note"),
        ),
    }
    return {
        name: (headline, draw(frame, headline, footer + note, lang))
        for name, (headline, draw, frame, note) in specs.items()
    }


def _plain(value):
    """JSON for numpy scalars and dates in the facts."""
    if isinstance(value, np.generic):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"not JSON serialisable: {type(value).__name__}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="make-charts", description=__doc__.splitlines()[0])
    parser.add_argument(
        "--database", type=Path, default=Path("data/brazil_consumer_credit_risk.duckdb")
    )
    parser.add_argument("--out", type=Path, default=Path("analysis/figures"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.database.exists():
        parser.error(f"{args.database} not found: run make fetch and make build first")
    with duckdb.connect(str(args.database), read_only=True) as con:
        frames = load(con)

    for lang in LANGUAGES.values():
        out = args.out / lang.code
        out.mkdir(parents=True, exist_ok=True)
        record = {}
        for name, (headline, fig) in build(frames, lang).items():
            path = out / f"{name}.png"
            fig.savefig(path)
            plt.close(fig)
            record[name] = {
                "title": headline.title,
                "subtitle": headline.subtitle,
                "facts": headline.facts,
            }
            log.info("%s: %s", path, headline.title)
        (out / "headlines.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2, default=_plain) + "\n"
        )
    return 0
