"""The six figures. Each takes the rows of its analysis model and the headline chosen for it, and
returns a matplotlib Figure; nothing here decides what the chart says."""

from __future__ import annotations

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib import colormaps
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import FuncFormatter, MultipleLocator

from . import headlines as h
from .headlines import Headline
from .language import PT, Language
from .style import (
    BLUE,
    FAINT,
    INCOME_BANDS,
    INK,
    MUTED,
    ORANGE,
    PAIRS,
    SKY,
    VERMILLION,
    canvas,
)

# BCB's estimate of how much of the first half of 2025's rise in 90-day delinquency came from the
# new accounting rules: 0.53 of 0.78 pp for the whole financial system, with a similar share for
# households. Relatório de Política Monetária, September 2025, box on the new accounting rules
# (bcb.gov.br/content/ri/relatorioinflacao/202509/rpm202509b6p.pdf); docs/data-landscape.md, A.3.
BCB_REGULATORY_PP = 0.53
BCB_TOTAL_PP = 0.78

ACCOUNTING_CHANGE = pd.Timestamp("2025-01-01")
LAST_COMPARABLE = pd.Timestamp("2024-12-01")


def _percent_axis(ax, lang: Language, axis: str = "y", decimals: int = 0) -> None:
    formatter = FuncFormatter(lambda v, _: f"{lang.number(v, decimals)}%")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(formatter)


def _pp_axis(ax, lang: Language, axis: str = "x", decimals: int = 1) -> None:
    formatter = FuncFormatter(lambda v, _: lang.number(v, decimals, sign=v > 0))
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(formatter)


def the_trap(monthly: pd.DataFrame, headline: Headline, footer: str, lang: Language = PT) -> Figure:
    fig, spec = canvas(headline.title, headline.subtitle, footer, body_height=3.3, right=0.86)
    ax = fig.add_subplot(spec[0])
    month = pd.to_datetime(monthly["month"])
    d90 = 100 * monthly["d90_rate"]
    d15 = 100 * monthly["d15_rate"]
    sgs = 100 * monthly["sgs_21084_rate"]

    ax.plot(month, sgs, color=MUTED, lw=1, ls=":", label=lang.t("trap.official"))
    comparable = month <= LAST_COMPARABLE
    ax.plot(month[comparable], d90[comparable], color=BLUE, lw=2, label=lang.t("trap.d90"))
    ax.plot(
        month[month >= LAST_COMPARABLE],
        d90[month >= LAST_COMPARABLE],
        color=BLUE,
        lw=2,
        ls=(0, (3, 1.5)),
        label=lang.t("trap.d90_after"),
    )
    ax.plot(month, d15, color=VERMILLION, lw=2)

    ax.axvline(ACCOUNTING_CHANGE, color=INK, lw=0.8)
    top = max(d90.max(), sgs.max()) * 1.12
    ax.set_ylim(0, top)
    ax.text(
        ACCOUNTING_CHANGE - pd.Timedelta(days=20),
        top * 0.98,
        lang.t("trap.rule"),
        ha="right",
        va="top",
        fontsize=8,
        color=INK,
    )
    ax.text(
        pd.Timestamp("2024-10-01"),
        top * 0.36,
        lang.t(
            "trap.bcb",
            regulatory=lang.number(BCB_REGULATORY_PP),
            total=lang.number(BCB_TOTAL_PP),
        ),
        ha="right",
        va="center",
        fontsize=7.5,
        color=MUTED,
    )
    for series, label, color in ((d90, lang.t("d90"), BLUE), (d15, lang.t("d15"), VERMILLION)):
        ax.text(
            month.iloc[-1] + pd.Timedelta(days=45),
            series.iloc[-1],
            label,
            color=color,
            fontsize=9,
            fontweight="bold",
            va="center",
        )

    ax.set_xlim(month.min() - pd.Timedelta(days=45), month.max() + pd.Timedelta(days=30))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    _percent_axis(ax, lang, "y")
    ax.set_ylabel(lang.t("trap.ylabel"))
    ax.grid(axis="y")
    ax.legend(loc="upper left", fontsize=8, handlelength=2.5)
    return fig


def the_grid(grid: pd.DataFrame, headline: Headline, footer: str, lang: Language = PT) -> Figure:
    bands = [b for b in INCOME_BANDS if b in set(grid["income_band"])]
    eligible = grid[~grid["below_minimum_size"]]
    # Rows by the plain average of their bands: weighting by balance would sort occupations by
    # their income mix, which is what the columns already separate.
    order = eligible.groupby("occupation")["d90_rate"].mean().sort_values().index.tolist()
    order += sorted(set(grid["occupation"]) - set(order))

    fig, spec = canvas(
        headline.title,
        headline.subtitle,
        footer,
        body_height=3.6,
        left=0.27,
        right=0.98,
        bottom_space=0.55,
    )
    ax = fig.add_subplot(spec[0])
    values = eligible["d90_rate"] * 100
    lo, hi = values.min(), values.max()
    cmap = colormaps["YlOrRd"]

    for i, occupation in enumerate(order):
        for j, band in enumerate(bands):
            cell = grid[(grid["occupation"] == occupation) & (grid["income_band"] == band)]
            if cell.empty:
                continue
            cell = cell.iloc[0]
            if cell["below_minimum_size"]:
                ax.add_patch(Rectangle((j, i), 1, 1, facecolor="#F3F4F6", edgecolor="white", lw=2))
                ax.text(j + 0.5, i + 0.5, "–", ha="center", va="center", color=MUTED)
                continue
            rate = cell["d90_rate"] * 100
            shade = 0.12 + 0.78 * (rate - lo) / (hi - lo if hi > lo else 1)
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=cmap(shade), edgecolor="white", lw=2))
            ink = "white" if shade > 0.6 else INK
            ax.text(
                j + 0.5,
                i + 0.42,
                f"{lang.number(rate, 2)}%",
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
                color=ink,
            )
            ax.text(
                j + 0.5,
                i + 0.72,
                lang.t("grid.balance", bn=lang.number(cell["average_balance_bn"], 0)),
                ha="center",
                va="center",
                fontsize=6.5,
                color=ink,
            )

    largest = headline.facts.get("largest_spread")
    if largest:
        j = bands.index(largest["income_band"])
        for occupation in (largest["highest"], largest["lowest"]):
            i = order.index(occupation)
            ax.add_patch(
                Rectangle((j + 0.04, i + 0.04), 0.92, 0.92, fill=False, edgecolor=INK, lw=1.4)
            )

    ax.set_xlim(0, len(bands))
    ax.set_ylim(len(order), 0)
    ax.set_xticks(np.arange(len(bands)) + 0.5, [lang.label("band", b) for b in bands])
    ax.set_yticks(np.arange(len(order)) + 0.5, [lang.label("occupation", o) for o in order])
    ax.tick_params(length=0)
    ax.set_xlabel(lang.t("income_axis"))
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    return fig


def which_matters_more(
    dispersion: pd.DataFrame, headline: Headline, footer: str, lang: Language = PT
) -> Figure:
    fig, spec = canvas(
        headline.title,
        headline.subtitle,
        footer,
        body_height=3.6,
        right=0.85,
        nrows=2,
        height_ratios=[2.4, 1],
        hspace=0.35,
    )
    top = fig.add_subplot(spec[0])
    bottom = fig.add_subplot(spec[1], sharex=top)
    years = dispersion[dispersion["period_kind"] == "calendar_year"].copy()
    years["year"] = years["period_id"].astype(int)

    for measure, color, style, label in (
        ("d90", BLUE, "-", lang.t("d90")),
        ("d15", VERMILLION, "--", lang.t("d15")),
    ):
        rows = years[years["measure"] == measure].sort_values("year")
        top.plot(
            rows["year"],
            rows["occupation_to_income_ratio"],
            color=color,
            ls=style,
            lw=2,
            marker="o",
            ms=4,
        )
        top.text(
            rows["year"].iloc[-1] + 0.2,
            rows["occupation_to_income_ratio"].iloc[-1],
            label,
            color=color,
            fontsize=9,
            fontweight="bold",
            va="center",
        )

    windows = dispersion[(dispersion["period_kind"] == "window") & (dispersion["measure"] == "d90")]
    top.scatter(
        pd.to_datetime(windows["start_month"]).dt.year,
        windows["occupation_to_income_ratio"],
        s=110,
        facecolors="none",
        edgecolors=INK,
        lw=1,
        zorder=3,
        label=lang.t("dispersion.windows"),
    )
    top.axhline(1, color=INK, lw=0.8)
    # Mid-period, where both lines sit well below 1, so the labels never touch a point.
    label_x = years["year"].min() + 2.6
    top.text(
        label_x,
        1.02,
        lang.t("dispersion.above"),
        fontsize=7.5,
        color=MUTED,
        va="bottom",
    )
    top.text(
        label_x,
        0.98,
        lang.t("dispersion.below"),
        fontsize=7.5,
        color=MUTED,
        va="top",
    )
    top.set_ylim(0, max(1.4, years["occupation_to_income_ratio"].max() * 1.1))
    top.yaxis.set_major_formatter(FuncFormatter(lambda v, _: lang.number(v, 1)))
    top.set_ylabel(lang.t("dispersion.ylabel"))
    top.legend(loc="lower left", fontsize=8)
    top.grid(axis="y")
    top.tick_params(labelbottom=False)

    unemployment = years[years["measure"] == "d90"].sort_values("year")
    bottom.plot(
        unemployment["year"],
        100 * unemployment["unemployment_rate"],
        color=MUTED,
        lw=2,
        marker="o",
        ms=3,
    )
    bottom.set_ylim(0, 100 * unemployment["unemployment_rate"].max() * 1.25)
    bottom.yaxis.set_major_locator(MultipleLocator(5))
    _percent_axis(bottom, lang, "y")
    bottom.set_ylabel(lang.t("dispersion.unemployment"))
    bottom.set_xticks(unemployment["year"])
    bottom.grid(axis="y")
    return fig


def _stacked_barh(ax, y, parts, **kwargs) -> None:
    """Horizontal bars whose parts stack away from zero on their own side, so a negative part
    never hides a positive one."""
    positive = np.zeros(len(y))
    negative = np.zeros(len(y))
    for values, style in parts:
        values = np.asarray(values, dtype=float)
        base = np.where(values >= 0, positive, negative)
        ax.barh(y, values, left=base, **style, **kwargs)
        positive += np.where(values >= 0, values, 0)
        negative += np.where(values < 0, values, 0)


def job_or_product(
    gaps: pd.DataFrame, headline: Headline, footer: str, lang: Language = PT
) -> Figure:
    fig, spec = canvas(
        headline.title,
        headline.subtitle,
        footer,
        body_height=3.2,
        left=0.15,
        right=0.98,
        bottom_space=1.2,
        panel_titles=True,
        ncols=len(PAIRS),
        wspace=0.12,
    )
    bands = list(INCOME_BANDS)
    y = np.arange(len(bands))
    scale = (
        100 * gaps[gaps["income_band"].isin(bands)][["gap", "same_product_gap"]].abs().max().max()
    )
    limit = np.ceil(scale * 1.15 * 2) / 2

    for k, pair in enumerate(PAIRS):
        ax = fig.add_subplot(spec[k])
        rows = (
            gaps[(gaps["pair_id"] == pair) & (gaps["product_scope"] == "all_products")]
            .set_index("income_band")
            .reindex(bands)
        )
        rural = (
            gaps[(gaps["pair_id"] == pair) & (gaps["product_scope"] == "excluding_rural")]
            .set_index("income_band")
            .reindex(bands)
        )
        stable = set(h.stable_bands(gaps, pair, "all_products")["income_band"])
        for i, band in enumerate(bands):
            row = rows.loc[band]
            if pd.isna(row["gap"]) or row["below_minimum_size"]:
                ax.text(
                    0,
                    i,
                    lang.t("split.small"),
                    ha="center",
                    va="center",
                    fontsize=7,
                    color=MUTED,
                )
                continue
            readable = abs(row["gap"]) >= h.MATERIAL and bool(row["gap_sign_holds_with_lag"])
            style = {"alpha": 1.0 if band in stable else (0.55 if readable else 0.25)}
            hatch = None if band in stable or not readable else "////"
            _stacked_barh(
                ax,
                [i],
                [
                    ([100 * row["same_product_gap"]], {"color": BLUE, "hatch": hatch, **style}),
                    ([100 * row["product_mix_gap"]], {"color": SKY, "hatch": hatch, **style}),
                ],
                height=0.62,
                edgecolor="white",
                linewidth=0.5,
            )
            ax.plot(100 * row["gap"], i, marker="|", ms=14, mew=2, color=INK)
            if not pd.isna(rural.loc[band, "gap"]):
                ax.plot(
                    100 * rural.loc[band, "gap"],
                    i,
                    marker="D",
                    ms=5,
                    mfc="white",
                    mec=ORANGE,
                    mew=1.5,
                )

        ax.set_title(lang.label("pair_title", pair), fontsize=9, loc="left")
        ax.axvline(0, color=INK, lw=0.8)
        ax.set_xlim(-limit, limit)
        ax.set_ylim(len(bands) - 0.5, -0.5)
        ax.set_yticks(y, [lang.label("band", b) for b in bands] if k == 0 else [])
        ax.tick_params(axis="y", length=0)
        _pp_axis(ax, lang, "x")
        ax.grid(axis="x")
        ax.spines["left"].set_visible(False)
        if k == 0:
            ax.set_ylabel(lang.t("income_axis"))
        if k == 1:
            ax.set_xlabel(lang.t("split.xlabel"))

    handles = [
        Patch(color=BLUE, label=lang.t("split.within")),
        Patch(color=SKY, label=lang.t("split.mix")),
        Line2D([], [], marker="|", ms=12, mew=2, color=INK, ls="none", label=lang.t("split.total")),
        Line2D(
            [],
            [],
            marker="D",
            ms=5,
            mfc="white",
            mec=ORANGE,
            mew=1.5,
            ls="none",
            label=lang.t("split.without_rural"),
        ),
        Patch(
            facecolor=BLUE,
            alpha=0.55,
            hatch="////",
            edgecolor="white",
            label=lang.t("split.unstable"),
        ),
        Patch(
            facecolor=BLUE,
            alpha=0.25,
            label=lang.t("split.unreadable", material=lang.pp(h.MATERIAL, 1)),
        ),
    ]
    # Between the x-axis label and the footer.
    below_axes = spec.get_subplot_params(fig).bottom - 0.5 / fig.get_figheight()
    fig.legend(
        handles=handles,
        loc="upper left",
        ncols=3,
        fontsize=7.5,
        bbox_to_anchor=(0.02, below_axes),
        bbox_transform=fig.transFigure,
        handlelength=1.6,
        columnspacing=1.2,
    )
    return fig


def mix_versus_rate(
    episodes: pd.DataFrame, headline: Headline, footer: str, lang: Language = PT
) -> Figure:
    fig, spec = canvas(
        headline.title, headline.subtitle, footer, body_height=3.0, right=0.97, bottom_space=0.8
    )
    ax = fig.add_subplot(spec[0])
    episodes = episodes.sort_values("month_0").reset_index(drop=True)
    x = np.arange(len(episodes))
    parts = [
        ("pure_rate", BLUE, lang.t("mix.pure_rate")),
        ("product_mix", SKY, lang.t("mix.product_mix")),
        ("borrower_mix", ORANGE, lang.t("mix.borrower_mix")),
    ]
    positive = np.zeros(len(x))
    negative = np.zeros(len(x))
    for column, color, label in parts:
        values = 100 * episodes[column].to_numpy(dtype=float)
        base = np.where(values >= 0, positive, negative)
        ax.bar(
            x,
            values,
            bottom=base,
            width=0.55,
            color=color,
            label=label,
            edgecolor="white",
            linewidth=0.5,
        )
        positive += np.where(values >= 0, values, 0)
        negative += np.where(values < 0, values, 0)
    change = 100 * episodes["change"].to_numpy(dtype=float)
    ax.hlines(change, x - 0.36, x + 0.36, color=INK, lw=2.5, zorder=3, label=lang.t("mix.total"))
    for i, value in enumerate(change):
        ax.text(
            i + 0.4,
            value,
            lang.pp(value / 100, sign=True),
            fontsize=8.5,
            fontweight="bold",
            va="center",
            color=INK,
        )

    labels = []
    for _, row in episodes.iterrows():
        name = h.episode_name(row)
        labels.append(name + ("*" if row["spans_occupation_reclassification"] else ""))
    ax.set_xticks(x, labels)
    ax.set_xlim(-0.6, len(x) - 0.4 + 0.35)  # room for the last total's label
    ax.axhline(0, color=INK, lw=0.8)
    _pp_axis(ax, lang, "y")
    ax.set_ylabel(lang.pp_unit)
    ax.grid(axis="y")
    below_axes = spec.get_subplot_params(fig).bottom - 0.3 / fig.get_figheight()
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(0.02, below_axes),
        bbox_transform=fig.transFigure,
        ncols=4,
        fontsize=8,
    )
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(axis="x", length=0)
    return fig


def current_read(
    current: pd.DataFrame, headline: Headline, footer: str, lang: Language = PT
) -> Figure:
    fig, spec = canvas(
        headline.title,
        headline.subtitle,
        footer,
        body_height=2.9,
        left=0.30,
        right=0.97,
        bottom_space=0.7,
        panel_titles=True,
        ncols=2,
        width_ratios=[1.3, 1],
        wspace=0.08,
    )
    rows = current.sort_values("d15_change").reset_index(drop=True)
    y = np.arange(len(rows))
    fastest = headline.facts.get("fastest")

    left = fig.add_subplot(spec[0])
    colors = [VERMILLION if o == fastest else BLUE for o in rows["occupation"]]
    left.barh(y, 100 * rows["d15_change"], color=colors, height=0.62)
    left.scatter(
        100 * rows["d15_change_lagged"],
        y,
        marker="|",
        s=120,
        lw=1.8,
        color=INK,
        zorder=3,
        label=lang.t("current.lagged"),
    )
    # Past the bar or the lagged marker, whichever reaches further.
    ends = 100 * np.maximum(rows["d15_change"], rows["d15_change_lagged"])
    for i, (value, end) in enumerate(zip(100 * rows["d15_change"], ends, strict=True)):
        left.text(end + 0.015, i, lang.number(value, 2, sign=True), va="center", fontsize=8)
    left.set_yticks(y, [lang.label("occupation", o) for o in rows["occupation"]])
    left.set_title(lang.t("current.rate_title"), fontsize=9)
    left.set_xlim(
        min(0, 100 * rows["d15_change"].min() * 1.2), 100 * rows["d15_change"].max() * 1.3
    )
    _pp_axis(left, lang, "x", 1)
    left.legend(loc="upper left", bbox_to_anchor=(-0.02, -0.12), fontsize=7.5)
    left.tick_params(axis="y", length=0)
    left.spines["left"].set_visible(False)
    left.axvline(0, color=INK, lw=0.8)

    right = fig.add_subplot(spec[1], sharey=left)
    growth = 100 * rows["real_balance_growth"]
    right.barh(y, growth, color=[MUTED if g >= 0 else FAINT for g in growth], height=0.62)
    for i, value in enumerate(growth):
        right.text(
            value + (0.6 if value >= 0 else -0.6),
            i,
            f"{lang.number(value, 1, sign=True)}%",
            va="center",
            ha="left" if value >= 0 else "right",
            fontsize=8,
        )
    right.set_title(lang.t("current.balance_title"), fontsize=9)
    right.axvline(0, color=INK, lw=0.8)
    span = max(growth.abs().max() * 1.35, 5)
    right.set_xlim(min(0, growth.min() * 1.35), span)
    right.xaxis.set_major_formatter(FuncFormatter(lambda v, _: lang.number(v, 0, sign=v > 0)))
    right.tick_params(axis="y", length=0, labelleft=False)
    right.spines["left"].set_visible(False)
    return fig
