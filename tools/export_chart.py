"""Export a real, shareable closing-price and volume chart from frozen source data."""
import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol", nargs="?", default="ADI")
    args = parser.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    fixture = json.loads((ROOT / "data/market_snapshot.json").read_text())
    symbol = args.symbol.upper()
    if symbol not in fixture["records"]:
        parser.error(f"unknown symbol {symbol}")
    bars = fixture["records"][symbol]["candles"]
    if not bars:
        parser.error(f"no historical chart available for {symbol}")
    dates = [date.fromisoformat(b["d"]) for b in bars]
    closes = [b["c"] for b in bars]
    volumes = [b["v"] for b in bars]
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": "#476269", "axes.labelcolor": "#a5c0bb", "xtick.color": "#9db5af", "ytick.color": "#9db5af", "text.color": "#e4efec"})
    fig, (ax, vol) = plt.subplots(2, 1, figsize=(14, 7), dpi=125, sharex=True, gridspec_kw={"height_ratios": [4, 1], "hspace": .09})
    fig.patch.set_facecolor("#091722")
    for x in (ax, vol):
        x.set_facecolor("#102530")
        x.spines[["top", "right"]].set_visible(False)
        x.grid(axis="y", color="#335057", alpha=.55, lw=.6)
    ax.plot(dates, closes, color="#b4e283", linewidth=1.7)
    ax.fill_between(dates, closes, min(closes), color="#b4e283", alpha=.07)
    ax.set_ylabel("Clôture (MAD)")
    ax.set_title(f"{symbol} — {fixture['records'][symbol]['name']}  •  {len(bars)} séances", loc="left", pad=19, fontsize=17, fontweight="bold")
    ax.text(.99, 1.03, f"Dernière séance {dates[-1]} : {closes[-1]:,.2f} MAD".replace(",", " "), transform=ax.transAxes, ha="right", fontsize=10, color="#b4e283")
    vol.bar(dates, volumes, color="#376754", width=1.6)
    vol.set_ylabel("Titres")
    vol.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    vol.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
    fig.text(.09, .02, "Source : archive BVC Analyzer du 25/09/2026 · historique disponible, pas de flux en direct", color="#829ca0", fontsize=9)
    output = ROOT / "web" / f"{symbol}_historique.png"
    fig.savefig(output, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(output)


if __name__ == "__main__":
    main()
