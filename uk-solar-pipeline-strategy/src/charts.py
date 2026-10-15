"""Static charts for the README and memo (matplotlib, light theme, print-friendly)."""
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "outputs" / "figures"

SOLAR, BATTERY = "#2a78d6", "#eb6834"
AQUA, NEUTRAL = "#1baf7a", "#a3a29b"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e6e5e0"
SOURCE = "Source: DESNZ Renewable Energy Planning Database, Q2 2026 extract. Solar PV and battery projects of 1 MW or more."

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
    "savefig.facecolor": "#fcfcfb", "axes.spines.top": False, "axes.spines.right": False,
})


def _finish(fig, ax, name, subtitle=None, source=SOURCE):
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK2, fontsize=10, va="bottom")
    fig.text(0.01, 0.01, source, color=MUTED, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / name, dpi=200)
    plt.close(fig)


def pipeline_by_stage(t: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 4.6))
    y = np.arange(len(t))[::-1]
    h = 0.36
    for off, tech, col in [(h / 2 + 0.02, "Solar", SOLAR), (-h / 2 - 0.02, "Battery", BATTERY)]:
        ax.barh(y + off, t[tech], height=h, color=col, label=tech)
        for yi, v in zip(y + off, t[tech]):
            ax.text(v + 0.8, yi, f"{v:.1f} GW", va="center", fontsize=9, color=INK2)
    ax.set_yticks(y, t.index)
    ax.set_xlabel("Capacity (GW)")
    ax.xaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="lower right")
    total_wait = t.loc["Consented, not built", "Total"]
    total_op = t.loc["Operational", "Total"]
    ax.set_title(f"{total_wait:.0f} GW is consented but not built, {total_wait / total_op:.0f}x what is operating", pad=22)
    _finish(fig, ax, "01_pipeline_by_stage.png", "Where solar and battery capacity in the planning system sits today")


def applications_by_year(t: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 4.4))
    for tech, col in [("Solar", SOLAR), ("Battery", BATTERY)]:
        ax.plot(t.index, t[tech], color=col, lw=2, marker="o", ms=4)
        ax.text(t.index[-1] + 0.2, t[tech].iloc[-1], f"{tech}\n{t[tech].iloc[-1]:.1f} GW", color=INK2,
                va="center", fontsize=9)
    ax.set_xlim(t.index[0] - 0.3, t.index[-1] + 1.3)
    ax.set_xticks(t.index)
    ax.set_ylabel("GW of applications submitted")
    ax.yaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    ax.set_title("Battery applications have grown roughly fivefold since 2021", pad=22)
    _finish(fig, ax, "02_applications_by_year.png", "New planning applications per year, by capacity")


def cohort_outcomes(t: pd.DataFrame):
    cols = [("Operational", SOLAR), ("Under construction", AQUA),
            ("Consented, not built", BATTERY), ("Expired or abandoned", NEUTRAL)]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    y = np.arange(len(t))[::-1]
    left = np.zeros(len(t))
    for c, col in cols:
        vals = t[c].values
        ax.barh(y, vals, left=left, color=col, height=0.62, label=c, edgecolor="#fcfcfb", linewidth=2)
        for yi, l, v in zip(y, left, vals):
            if v >= 0.06:
                ax.text(l + v / 2, yi, f"{v:.0%}", ha="center", va="center", fontsize=9,
                        color="white" if col in (SOLAR,) else INK)
        left += vals
    ax.set_yticks(y, [f"{i} (n={n})" for i, n in zip(t.index, t["projects"])])
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12), fontsize=9)
    ax.set_title("Fewer than half of 2019-2022 consents have reached construction", pad=22)
    _finish(fig, ax, "03_consent_cohort_outcomes.png", "Status today of projects, by the year planning permission was granted")


def approval_vs_buildout(s: pd.DataFrame):
    r = s[s["ranked"]].sort_values("build_out_rate")
    fig, ax = plt.subplots(figsize=(9, 5))
    y = np.arange(len(r))
    ax.hlines(y, r["build_out_rate"], r["approval_rate"], color=GRID, lw=3, zorder=1)
    ax.errorbar(r["build_out_rate"], y, xerr=[r["build_out_rate"] - r["build_out_ci_low"],
                r["build_out_ci_high"] - r["build_out_rate"]], fmt="none", ecolor=BATTERY, alpha=0.35,
                capsize=3, zorder=2)
    ax.scatter(r["build_out_rate"], y, color=BATTERY, s=60, zorder=3, label="Build-out rate (2019-22 consents now built or building)")
    ax.scatter(r["approval_rate"], y, color=SOLAR, s=60, zorder=3, label="Planning approval rate (2021-24 applications)")
    ax.set_yticks(y, r.index)
    ax.set_xlim(0, 1.02)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.xaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=1, fontsize=9)
    ax.set_title("Planning is not the bottleneck: delivery is", pad=22)
    _finish(fig, ax, "04_approval_vs_buildout.png",
            "By region. Faint bars show 90% confidence intervals for build-out. Regions with <20 consents excluded.")


def region_matrix(s: pd.DataFrame):
    r = s[s["ranked"]]
    bm, mm = s.attrs["build_median"], s.attrs["market_median"]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.axvline(bm, color=MUTED, lw=1, ls="--")
    ax.axhline(mm, color=MUTED, lw=1, ls="--")
    ax.scatter(r["build_out_rate"], r["gw_applied_2021_24"], s=70, color=SOLAR, zorder=3,
               edgecolor="#fcfcfb", linewidth=2)
    nudge = {"South East": (6, 5), "North West": (-8, 5), "South West": (-8, -11),
             "West Midlands": (6, -11), "Wales": (6, -4)}
    for name, row in r.iterrows():
        dx, dy = nudge.get(name, (6, 4))
        ax.annotate(name, (row["build_out_rate"], row["gw_applied_2021_24"]), xytext=(dx, dy),
                    textcoords="offset points", fontsize=9, color=INK,
                    ha="right" if dx < 0 else "left")
    xmin, xmax = 0.22, 0.50
    ymin, ymax = 0, r["gw_applied_2021_24"].max() * 1.12
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    kw = dict(fontsize=10, fontweight="bold", color=INK2, alpha=0.9)
    ax.text(xmax - 0.005, ymax * 0.97, "GO NOW", ha="right", va="top", **kw)
    ax.text(xmin + 0.005, ymax * 0.97, "CROWDED: GRID-FIRST ONLY", ha="left", va="top", **kw)
    ax.text(xmax - 0.005, ymin + ymax * 0.02, "SELECTIVE NICHE", ha="right", va="bottom", **kw)
    ax.text(xmin + 0.005, ymin + ymax * 0.02, "DEPRIORITISE", ha="left", va="bottom", **kw)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_xlabel("Deliverability: share of 2019-22 consents now built or under construction")
    ax.set_ylabel("Market depth: GW of applications, 2021-24")
    ax.set_title("Regional prioritisation for a solar and battery developer", pad=22)
    _finish(fig, ax, "05_region_matrix.png",
            "Dashed lines are medians across ranked regions. South East and South West sit close to the lines.")


def pipeline_map(df: pd.DataFrame):
    gb = df[(df["Country"] != "Northern Ireland") & df["stage"].isin(["Operational", "Consented, not built"])].copy()
    gb["x"] = pd.to_numeric(gb["X-coordinate"].astype(str).str.replace(",", ""), errors="coerce")
    gb["y"] = pd.to_numeric(gb["Y-coordinate"].astype(str).str.replace(",", ""), errors="coerce")
    gb = gb.dropna(subset=["x", "y"])
    pts = gpd.GeoDataFrame(gb, geometry=gpd.points_from_xy(gb["x"], gb["y"]), crs=27700)

    fig, axes = plt.subplots(1, 2, figsize=(10, 7.4))
    for ax, (stage, col) in zip(axes, [("Operational", SOLAR), ("Consented, not built", BATTERY)]):
        pts.plot(ax=ax, markersize=1, color=GRID, linewidth=0)  # all projects, for geographic context
        sub = pts[pts["stage"] == stage]
        sub.plot(ax=ax, markersize=np.clip(sub["mw"] / 4, 2, 120), color=col, alpha=0.45, linewidth=0)
        ax.set_title(f"{stage}: {sub['mw'].sum() / 1000:.0f} GW", fontsize=12)
        ax.set_xlim(0, 700_000)
        ax.set_ylim(0, 1_000_000)
        ax.set_axis_off()
    fig.suptitle("The consented backlog is concentrated in Scotland, Yorkshire, the Midlands and the East", x=0.02, ha="left",
                 fontsize=13, fontweight="bold")
    fig.text(0.02, 0.92, "Solar PV and battery projects in Great Britain (grey dots: both stages, for context). Circle size proportional to capacity.",
             color=INK2, fontsize=10)
    fig.text(0.01, 0.01, SOURCE + " Northern Ireland excluded (different grid reference system).", color=MUTED, fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 0.9))
    fig.savefig(FIG / "06_pipeline_map.png", dpi=200)
    plt.close(fig)
