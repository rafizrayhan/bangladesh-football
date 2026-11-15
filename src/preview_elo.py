import os, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for f in fm.findSystemFonts(fontpaths=[os.path.expanduser("~/.fonts")]): fm.fontManager.addfont(f)
plt.rcParams["font.family"] = "Inter" if any("Inter" in f.name for f in fm.fontManager.ttflist) else "DejaVu Sans"
B = pd.read_csv("data/bd_elo_matches.csv", parse_dates=["date"]); H = pd.read_csv("data/elo_history.csv", parse_dates=["date"])
fig, (a1, a2) = plt.subplots(2, 1, figsize=(12, 8.5), dpi=120, gridspec_kw={"hspace": 0.45})
a1.plot(B.date, B.bd_elo_after, color="#006a4e", lw=1.8)
pk, lo = B.loc[B.bd_elo_after.idxmax()], B.loc[B.bd_elo_after.idxmin()]
a1.scatter([pk.date, lo.date], [pk.bd_elo_after, lo.bd_elo_after], color="#f42a41", zorder=3)
a1.annotate(f"peak {pk.bd_elo_after:.0f}\n{pk.date:%b %Y}", (pk.date, pk.bd_elo_after), xytext=(10, -26), textcoords="offset points", fontsize=9)
a1.annotate(f"low {lo.bd_elo_after:.0f}\n{lo.date:%b %Y}", (lo.date, lo.bd_elo_after), xytext=(10, -4), textcoords="offset points", fontsize=9)
a1.set_title("Bangladesh Elo rating after every match, 1973 to 2026", loc="left", fontsize=12, fontweight="bold", pad=14)
for s in ("top", "right"): a1.spines[s].set_visible(False)
H = H[H.date.dt.year >= 1975]; y = H.groupby([H.date.dt.year, "team"]).elo.last().unstack()
y = y.reindex(range(1975, 2027)).ffill()
for t in y.columns:  # no line before a team's first match
    first = H[H.team == t].date.dt.year.min(); y.loc[y.index < first, t] = None
for t in y.columns:
    a2.plot(y.index, y[t], color="#006a4e" if t == "Bangladesh" else "#c4c9cf", lw=2.4 if t == "Bangladesh" else 1.2, zorder=3 if t == "Bangladesh" else 1)
    last = y[t].dropna()
    off = {"Nepal": -22, "Pakistan": 0, "Bangladesh": 22, "Maldives": -18, "Sri Lanka": 14}.get(t, 0)
    a2.text(last.index[-1] + 0.4, last.iloc[-1] + off, t, fontsize=8.5, va="center", color="#006a4e" if t == "Bangladesh" else "#6b7280")
a2.set_xlim(1975, 2030); a2.set_title("South Asia · Elo at the end of each year", loc="left", fontsize=12, fontweight="bold")
for s in ("top", "right"): a2.spines[s].set_visible(False)
fig.savefig("previews/elo_preview.png", facecolor="white", bbox_inches="tight")
