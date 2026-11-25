"""README charts. Colors: Xbox green / PlayStation blue (brand meaning), checked for colorblind separation
(OKLab dE >= 8 under protan/deutan/tritan) and >= 3:1 contrast on the surface; every line is direct-labeled."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, MaxNLocator, PercentFormatter  # noqa: E402

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
XBOX, PLAYSTATION = "#107c10", "#2a78d6"
MIX = {"rev_digital_software": ("#2a78d6", "Digital software & add-ons"),
       "rev_network_services": ("#eb6834", "Network services (PS Plus etc.)"),
       "rev_hardware_other": ("#1baf7a", "Hardware & others")}
SOURCE = "Source: SEC EDGAR 10-K (Microsoft) / 20-F (Sony) XBRL."


def _axes(title, subtitle):
    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, length=0, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    fig.text(0.06, 0.95, title, fontsize=14, fontweight="bold", color=INK, ha="left")
    fig.text(0.06, 0.905, subtitle, fontsize=9.5, color=INK2, ha="left")
    fig.subplots_adjust(left=0.08, right=0.80, top=0.80, bottom=0.17)
    return fig, ax


def _line(ax, xs, ys, color, label, fmt):
    ax.plot(xs, ys, color=color, linewidth=2, marker="o", markersize=5,
            markeredgecolor=SURFACE, markeredgewidth=1.5, label=label, solid_capstyle="round")
    ax.annotate(f"{label}\n{fmt(ys[-1])}", (xs[-1], ys[-1]), xytext=(10, 0), textcoords="offset points",
                va="center", fontsize=9, color=INK)


def _save(fig, out_dir, name, footnote):
    fig.text(0.06, 0.065, footnote, fontsize=7.5, color=INK2, ha="left")
    fig.text(0.06, 0.03, SOURCE, fontsize=7.5, color=INK2, ha="left")
    path = Path(out_dir) / name
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
    return path


def write_charts(con, out_dir: Path) -> list[Path]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    paths = []

    rows = con.execute("SELECT fiscal_year, xbox_usd, playstation_usd FROM v_head_to_head").fetchall()
    fys = [r[0] for r in rows]
    fig, ax = _axes("Xbox vs PlayStation: gaming revenue", "Annual segment revenue, USD billions")
    _line(ax, fys, [r[2] / 1e9 for r in rows], PLAYSTATION, "PlayStation", lambda v: f"${v:,.1f}B")
    _line(ax, fys, [r[1] / 1e9 for r in rows], XBOX, "Xbox", lambda v: f"${v:,.1f}B")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}B"))
    ax.set_ylim(bottom=0)
    if 2024 in fys:
        ax.axvline(2023.8, color=INK2, linewidth=1, linestyle=(0, (2, 3)))
        ax.annotate("Activision Blizzard\ndeal closes (Oct 2023)", (2023.8, ax.get_ylim()[1] * 0.12),
                    xytext=(-6, 0), textcoords="offset points", ha="right", fontsize=8, color=INK2)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.01), ncol=3, frameon=False, fontsize=9, labelcolor=INK)
    paths.append(_save(fig, out_dir, "revenue_usd.png",
                       "Fiscal years: Microsoft ends June, Sony ends March. Sony converted at each FY's average JPY/USD."))

    mix = con.execute("SELECT fiscal_year, bucket, share FROM v_sony_mix ORDER BY fiscal_year").fetchall()
    fig, ax = _axes("What PlayStation sells", "Share of Game & Network Services sales to outside customers")
    for bucket, (color, label) in MIX.items():
        pts = [(fy, s) for fy, b, s in mix if b == bucket]
        if pts:
            _line(ax, [p[0] for p in pts], [p[1] for p in pts], color, label, lambda v: f"{v:.0%}")
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_ylim(0, max([s for _, _, s in mix], default=0.6) * 1.15)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.01), ncol=3, frameon=False, fontsize=9, labelcolor=INK)
    paths.append(_save(fig, out_dir, "sony_mix.png", "Sony's own product categories; split reported from FY2017."))

    margin = con.execute("SELECT fiscal_year, margin FROM v_sony_margin ORDER BY fiscal_year").fetchall()
    fig, ax = _axes("PlayStation operating margin", "Game & Network Services operating income / segment revenue")
    _line(ax, [m[0] for m in margin], [m[1] for m in margin], PLAYSTATION, "Margin", lambda v: f"{v:.1%}")
    ax.axhline(0, color=INK2, linewidth=0.8)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    paths.append(_save(fig, out_dir, "sony_margin.png",
                       "Microsoft does not disclose gaming operating income. US GAAP to FY2020, IFRS from FY2021."))
    return paths
