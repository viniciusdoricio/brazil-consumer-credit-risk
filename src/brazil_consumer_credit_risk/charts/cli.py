"""Build the six charts from the dbt database.

    uv run make-charts                       reads data/brazil_consumer_credit_risk.duckdb
    uv run make-charts --out analysis/figures

Writes one PNG per chart and headlines.json, which holds each chart's headline, subtitle and the
numbers behind them, for the write-up to cite. Needs a full build (make fetch, make build): the
charts span 2016 to the latest month.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import figures, headlines  # noqa: E402
from .style import SOURCE, use_style  # noqa: E402

log = logging.getLogger("make-charts")

# The headline cross-section: calendar 2024, the last full year before the accounting change
# (docs/v1-decision.md, section 3).
HEADLINE_WINDOW = "cs_2024"
HEADLINE_PERIOD = "2024"
# Chart 1 starts when the reporting threshold fell to R$200, the start of the comparable national
# series (docs/v1-decision.md, section 4).
TRAP_START = "2016-06-01"

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


def build(frames: dict[str, pd.DataFrame]) -> dict[str, tuple[headlines.Headline, plt.Figure]]:
    """Every chart's headline and figure, keyed by the file name it is saved under."""
    use_style()
    latest = pd.Timestamp(frames["monthly"]["month"].max()).date()
    footer = f"{SOURCE} {headlines.as_of(latest)}"
    specs = {
        "chart1_trap": (
            headlines.the_trap(frames["monthly"]),
            figures.the_trap,
            frames["monthly"],
            "",
        ),
        "chart2_grid": (
            headlines.the_grid(frames["grid"], HEADLINE_PERIOD),
            figures.the_grid,
            frames["grid"],
            " Células abaixo de R$ 1 bi de saldo médio não são mostradas. Contornos: a maior "
            "diferença numa faixa.",
        ),
        "chart3_dispersion": (
            headlines.which_matters_more(frames["dispersion"]),
            figures.which_matters_more,
            frames["dispersion"],
            " Ocupações e faixas nomeadas, células acima de R$ 1 bi. Desemprego: média anual "
            "da PNAD Contínua (SGS 24369).",
        ),
        "chart4_job_or_product": (
            headlines.job_or_product(frames["gaps"], HEADLINE_PERIOD),
            figures.job_or_product,
            frames["gaps"],
            " Divisão estável: diferença de ao menos 0,1 p.p., mesma ordem com o denominador "
            "de 12 meses antes e parte do mix que muda menos de 25% da diferença quando produtos "
            "ambíguos trocam de grupo.",
        ),
        "chart5_mix_vs_rate": (
            headlines.mix_versus_rate(frames["episodes"]),
            figures.mix_versus_rate,
            frames["episodes"],
            " Episódios de janeiro a dezembro; a taxa de 90 dias é comparável até dez/2024.",
        ),
        "chart6_current_read": (
            headlines.current_read(frames["current"]),
            figures.current_read,
            frames["current"],
            " Desde 2025, valores vencidos incluem juros contratuais até o ativo ser "
            "problemático, o que pode elevar um pouco os saldos com 60 a 90 dias de atraso.",
        ),
    }
    return {
        name: (headline, draw(frame, headline, footer + note))
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

    args.out.mkdir(parents=True, exist_ok=True)
    record = {}
    for name, (headline, fig) in build(frames).items():
        path = args.out / f"{name}.png"
        fig.savefig(path)
        plt.close(fig)
        record[name] = {
            "title": headline.title,
            "subtitle": headline.subtitle,
            "facts": headline.facts,
        }
        log.info("%s: %s", path, headline.title)
    (args.out / "headlines.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2, default=_plain) + "\n"
    )
    return 0
