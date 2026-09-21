"""The look shared by every figure: fonts, colours, Portuguese labels, number formats, and the
title, subtitle and footer around the plot."""

from __future__ import annotations

import textwrap
from datetime import date

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

# Okabe-Ito, which stays distinguishable under the common forms of colour blindness.
BLUE = "#0072B2"
SKY = "#56B4E9"
ORANGE = "#E69F00"
VERMILLION = "#D55E00"
INK = "#1F2328"
MUTED = "#59636E"
FAINT = "#C9D1D9"

FIGURE_WIDTH = 8.0
DPI = 200

MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

OCCUPATIONS = {
    "Aposentado/pensionista": "Aposentados e pensionistas",
    "Autônomo": "Autônomos",
    "Empregado de empresa privada": "Empregados do setor privado",
    "Servidor ou empregado público": "Servidores e empregados públicos",
    "Empresário": "Empresários",
    "MEI": "MEI",
    "Empregado de entidades sem fins lucrativos": "Empregados de entidades\nsem fins lucrativos",
    "Outros": "Outros",
}
# Lower-case forms for use inside a sentence.
OCCUPATIONS_IN_TEXT = {
    "Aposentado/pensionista": "aposentados e pensionistas",
    "Autônomo": "autônomos",
    "Empregado de empresa privada": "empregados do setor privado",
    "Servidor ou empregado público": "servidores e empregados públicos",
    "Empresário": "empresários",
    "MEI": "MEI",
    "Empregado de entidades sem fins lucrativos": "empregados de entidades sem fins lucrativos",
    "Outros": "outros",
}

# Named income bands in order, with the short label used on axes.
INCOME_BANDS = {
    "Até 1 salário mínimo": "Até 1",
    "Mais de 1 a 2 salários mínimos": "1 a 2",
    "Mais de 2 a 3 salários mínimos": "2 a 3",
    "Mais de 3 a 5 salários mínimos": "3 a 5",
    "Mais de 5 a 10 salários mínimos": "5 a 10",
    "Mais de 10 a 20 salários mínimos": "10 a 20",
    "Acima de 20 salários mínimos": "Acima de 20",
}

PAIR_TITLES = {
    "retiree_vs_self_employed": "Aposentados − autônomos",
    "public_vs_private_employee": "Servidores − empregados privados",
    "mei_vs_business_owner": "MEI − empresários",
}

PAIRS = {
    "retiree_vs_self_employed": ("aposentados", "autônomos"),
    "public_vs_private_employee": ("servidores públicos", "empregados do setor privado"),
    "mei_vs_business_owner": ("MEI", "empresários"),
}

SOURCE = (
    "Elaboração própria com dados do Banco Central do Brasil (SCR.data e SGS, licença ODbL). "
    "Pessoas físicas."
)


def use_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
            "font.size": 9.5,
            "axes.edgecolor": MUTED,
            "axes.labelcolor": INK,
            "axes.titlesize": 10,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "grid.color": FAINT,
            "grid.linewidth": 0.6,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.labelcolor": INK,
            "ytick.labelcolor": INK,
            "legend.frameon": False,
            "savefig.dpi": DPI,
            "axes.unicode_minus": True,
        }
    )


def number(x: float, decimals: int = 2, sign: bool = False) -> str:
    """A number the Brazilian way: decimal comma, thousands point, and a true minus sign."""
    text = f"{abs(x):,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    if x < 0 and float(f"{abs(x):.{decimals}f}") != 0:
        return "−" + text
    return ("+" + text) if sign else text


def in_words(n: int, feminine: bool = False) -> str:
    """Counts up to ten spelled out, as Portuguese prose expects."""
    words = {
        1: "um",
        2: "dois",
        3: "três",
        4: "quatro",
        5: "cinco",
        6: "seis",
        7: "sete",
        8: "oito",
        9: "nove",
        10: "dez",
    }
    if feminine and n in (1, 2):
        return {1: "uma", 2: "duas"}[n]
    return words.get(n, str(n))


def pp(rate: float, decimals: int = 2, sign: bool = False) -> str:
    """A rate difference, stored as a fraction, in percentage points."""
    return f"{number(100 * rate, decimals, sign)} p.p."


def pct(rate: float, decimals: int = 1, sign: bool = False) -> str:
    """A rate or growth, stored as a fraction, as a percentage."""
    return f"{number(100 * rate, decimals, sign)}%"


def month_label(month: date) -> str:
    return f"{MONTHS[month.month - 1]}/{month.year}"


def canvas(
    title: str,
    subtitle: str,
    footer: str,
    body_height: float,
    left: float = 0.09,
    right: float = 0.97,
    bottom_space: float = 0.45,
    **grid,
) -> tuple[Figure, GridSpec]:
    """A figure with the headline, subtitle and footer set outside the plot area.

    The height grows with the wrapped text, so a long generated headline never overlaps the plot.
    Returns the figure and a GridSpec covering the plot area; body_height is in inches, and
    bottom_space leaves room under it for tick labels and an axis label.
    """
    title_lines = textwrap.wrap(title, 74)
    subtitle_lines = [line for part in subtitle.split("\n") for line in textwrap.wrap(part, 112)]
    footer_lines = [line for part in footer.split("\n") for line in textwrap.wrap(part, 132)]

    pad = 0.18
    title_h = len(title_lines) * 13 * 1.25 / 72
    subtitle_h = len(subtitle_lines) * 9 * 1.35 / 72
    footer_h = len(footer_lines) * 7.5 * 1.35 / 72
    header = pad + title_h + 0.08 + subtitle_h + 0.22
    below = bottom_space + footer_h + pad
    height = header + body_height + below

    fig = plt.figure(figsize=(FIGURE_WIDTH, height))
    x = 0.02
    y = 1 - pad / height
    fig.text(
        x,
        y,
        "\n".join(title_lines),
        ha="left",
        va="top",
        fontsize=13,
        fontweight="bold",
        color=INK,
        linespacing=1.15,
    )
    y -= (title_h + 0.08) / height
    fig.text(
        x,
        y,
        "\n".join(subtitle_lines),
        ha="left",
        va="top",
        fontsize=9,
        color=MUTED,
        linespacing=1.3,
    )
    fig.text(
        x,
        pad / height,
        "\n".join(footer_lines),
        ha="left",
        va="bottom",
        fontsize=7.5,
        color=MUTED,
        linespacing=1.3,
    )

    grid.setdefault("nrows", 1)
    grid.setdefault("ncols", 1)
    spec = fig.add_gridspec(
        top=1 - header / height, bottom=below / height, left=left, right=right, **grid
    )
    return fig, spec
