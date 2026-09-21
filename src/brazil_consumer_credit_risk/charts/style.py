"""The look shared by every figure, in any language: fonts, colours, and the title, subtitle and
footer around the plot."""

from __future__ import annotations

import textwrap

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

# Named income bands in order, as published. Their labels live in `language`.
INCOME_BANDS = (
    "Até 1 salário mínimo",
    "Mais de 1 a 2 salários mínimos",
    "Mais de 2 a 3 salários mínimos",
    "Mais de 3 a 5 salários mínimos",
    "Mais de 5 a 10 salários mínimos",
    "Mais de 10 a 20 salários mínimos",
    "Acima de 20 salários mínimos",
)

# The three headline comparisons, in the order the charts show them (seeds/occupation_pairs.csv).
PAIRS = ("retiree_vs_self_employed", "public_vs_private_employee", "mei_vs_business_owner")


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


def canvas(
    title: str,
    subtitle: str,
    footer: str,
    body_height: float,
    left: float = 0.09,
    right: float = 0.97,
    bottom_space: float = 0.45,
    panel_titles: bool = False,
    **grid,
) -> tuple[Figure, GridSpec]:
    """A figure with the headline, subtitle and footer set outside the plot area.

    The height grows with the wrapped text, so a long generated headline never overlaps the plot.
    Returns the figure and a GridSpec covering the plot area; body_height is in inches, and
    bottom_space leaves room under it for tick labels and an axis label. panel_titles leaves room
    above it for the titles of side-by-side panels.
    """

    def wrap(text: str, width: int) -> list[str]:
        # Only at spaces: "micro-entrepreneurs" stays whole.
        return [
            line
            for part in text.split("\n")
            for line in textwrap.wrap(part, width, break_on_hyphens=False)
        ]

    title_lines = wrap(title, 74)
    subtitle_lines = wrap(subtitle, 112)
    footer_lines = wrap(footer, 132)

    pad = 0.18
    title_h = len(title_lines) * 13 * 1.25 / 72
    subtitle_h = len(subtitle_lines) * 9 * 1.35 / 72
    footer_h = len(footer_lines) * 7.5 * 1.35 / 72
    header = pad + title_h + 0.08 + subtitle_h + 0.22 + (0.2 if panel_titles else 0)
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
