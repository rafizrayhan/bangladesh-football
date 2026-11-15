"""Python previews of the six Power BI pages (all years, all competitions, all venues)."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager as fm

for f in fm.findSystemFonts(fontpaths=[os.path.expanduser("~/.fonts")]):
    fm.fontManager.addfont(f)
plt.rcParams["font.family"] = "Inter" if any("Inter" in f.name for f in fm.fontManager.ttflist) else "DejaVu Sans"
D = "data/pbi"
F = pd.read_csv(f"{D}/fact_matches.csv", parse_dates=["date"])
S = pd.read_csv(f"{D}/fact_sa_matches.csv", parse_dates=["date"])
H = pd.read_csv(f"{D}/fact_elo_history.csv", parse_dates=["date"])
CO = pd.read_csv(f"{D}/dim_coach.csv")
SAFF = pd.read_csv(f"{D}/fact_saff.csv")
COMP = pd.read_csv(f"{D}/dim_competition.csv")
GREEN, RED, GREY, WIN, DRAW, LOSS = "#006a4e", "#f42a41", "#9aa3ae", "#639922", "#b4b2a9", "#e24b4a"
os.makedirs("previews", exist_ok=True)


def header(fig, page, sub=""):
    fig.text(0.02, 0.965, f"Bangladesh men's national team · {page}", fontsize=17, fontweight="bold")
    fig.text(0.02, 0.935, "1973 to 2026 · all competitions · all venues · data: international_results (open data) + own Elo model",
             fontsize=9.5, color="#555")
    if sub:
        fig.text(0.98, 0.95, sub, fontsize=9, color="#777", ha="right")


def tiles(fig, items, y=0.825):
    w = 0.96 / len(items)
    for i, (lab, val, note) in enumerate(items):
        ax = fig.add_axes([0.02 + i * w, y, w - 0.01, 0.08])
        ax.set_facecolor("#f2f4f7"); ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values(): s.set_visible(False)
        ax.text(0.05, 0.74, lab, fontsize=9, color="#555", transform=ax.transAxes)
        ax.text(0.05, 0.28, val, fontsize=16, fontweight="bold", transform=ax.transAxes)
        ax.text(0.05, 0.06, note, fontsize=8, color="#555", transform=ax.transAxes)


def clean(ax):
    for s in ("top", "right"): ax.spines[s].set_visible(False)


def wdl_bars(ax, labels, w, d, l, title, show_n=True):
    y = np.arange(len(labels))[::-1]
    t = np.array(w) + np.array(d) + np.array(l)
    ax.barh(y, np.array(w) / t, color=WIN); ax.barh(y, np.array(d) / t, left=np.array(w) / t, color=DRAW)
    ax.barh(y, np.array(l) / t, left=(np.array(w) + np.array(d)) / t, color=LOSS)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9); ax.set_xlim(0, 1.13); ax.set_xticks([])
    for yi, wi, ti in zip(y, w, t):
        ax.text(wi / ti / 2, yi, f"{100 * wi / ti:.0f}%", ha="center", va="center", fontsize=7.5, color="white")
        if show_n: ax.text(1.02, yi, f"{ti}", va="center", fontsize=8, color="#555")
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title(title, loc="left", fontsize=11)


now, first26 = F.bd_elo_after.iloc[-1], F[F.year == 2026].bd_elo_before.iloc[0]
rc = F.result.value_counts()

# ================================================= page 1: overview
fig = plt.figure(figsize=(14, 9.5), dpi=110); header(fig, "Overview")
hv = F[F.venue == "Home"].result.value_counts()
tiles(fig, [("Matches", f"{len(F)}", "since July 1973"),
            ("Won · drawn · lost", f"{rc.W} · {rc.D} · {rc.L}", f"{100 * rc.W / len(F):.0f}% win rate"),
            ("Goals for · against", f"{F.gf.sum()} · {F.ga.sum()}", f"{F.gf.mean():.2f} vs {F.ga.mean():.2f} per match"),
            ("Home win rate", f"{100 * hv.W / hv.sum():.0f}%", f"away {100 * (F[F.venue == 'Away'].result == 'W').mean():.0f}% · neutral {100 * (F[F.venue == 'Neutral'].result == 'W').mean():.0f}%"),
            ("Elo rating now", f"{now:.0f}", f"{now - first26:+.0f} in 2026")])
dec = F.assign(decade=(F.year // 10 * 10).astype(str) + "s").groupby("decade").result.value_counts().unstack(fill_value=0)
wdl_bars(fig.add_axes([0.07, 0.43, 0.40, 0.33]), dec.index.tolist(), dec.W, dec.D, dec.L, "Results by decade · won / drawn / lost")
ax = fig.add_axes([0.55, 0.43, 0.43, 0.33]); ax.axis("off"); ax.set_title("Last 10 results", loc="left", fontsize=11)
for i, r in enumerate(F.tail(10).itertuples()):
    c = {"W": WIN, "D": DRAW, "L": LOSS}[r.result]
    ax.add_patch(plt.Rectangle((i * 0.1, 0.62), 0.085, 0.28, color=c, transform=ax.transAxes))
    ax.text(i * 0.1 + 0.0425, 0.76, r.result, ha="center", va="center", color="white", fontsize=12, fontweight="bold", transform=ax.transAxes)
    ax.text(i * 0.1 + 0.0425, 0.52, f"{r.opponent}\n{r.gf}-{r.ga}", ha="center", va="top", fontsize=7, transform=ax.transAxes)
ax = fig.add_axes([0.02, 0.05, 0.45, 0.30]); ax.axis("off"); ax.set_title("Most-played opponents", loc="left", fontsize=11)
op = F.groupby("opponent").result.value_counts().unstack(fill_value=0); op["P"] = op.sum(axis=1)
op = op.sort_values("P", ascending=False).head(6)
tb = ax.table(cellText=[[o, int(r.P), int(r.W), int(r.D), int(r.L), f"{100 * r.W / r.P:.0f}%"] for o, r in op.iterrows()],
              colLabels=["Opponent", "P", "W", "D", "L", "Win %"], loc="upper left", cellLoc="left", edges="horizontal")
tb.auto_set_font_size(False); tb.set_fontsize(9); tb.scale(1, 1.5)
v = F.groupby("venue").result.value_counts().unstack(fill_value=0).reindex(["Home", "Away", "Neutral"])
wdl_bars(fig.add_axes([0.6, 0.08, 0.37, 0.24]), v.index.tolist(), v.W, v.D, v.L, "Record by venue")
fig.savefig("previews/page1_overview.png", facecolor="white")

# ================================================= page 2: strength over time
fig = plt.figure(figsize=(14, 9.5), dpi=110); header(fig, "Strength over time", "Elo: World Football Elo method, own calculation")
pk, lo = F.loc[F.bd_elo_after.idxmax()], F.loc[F.bd_elo_after.idxmin()]
tiles(fig, [("Elo rating now", f"{now:.0f}", f"{now - first26:+.0f} in 2026"),
            ("Highest", f"{pk.bd_elo_after:.0f}", f"{pk.date:%b %Y}"),
            ("Lowest", f"{lo.bd_elo_after:.0f}", f"{lo.date:%b %Y}"),
            ("Points vs expected", f"{F.points_elo.sum() - F.expected_score.sum():+.1f}",
             f"{F.points_elo.sum():.1f} won vs {F.expected_score.sum():.1f} expected (1 per win, ½ per draw)")])
ax = fig.add_axes([0.05, 0.43, 0.92, 0.33]); ax.plot(F.date, F.bd_elo_after, color=GREEN, lw=1.8); clean(ax)
ax.scatter([pk.date, lo.date], [pk.bd_elo_after, lo.bd_elo_after], color=RED, zorder=3)
ax.set_title("Elo rating after every match", loc="left", fontsize=11)
dx = F.assign(decade=(F.year // 10 * 10).astype(str) + "s").groupby("decade")[["points_elo", "expected_score"]].sum()
ax = fig.add_axes([0.05, 0.06, 0.42, 0.28]); x = np.arange(len(dx))
ax.bar(x - 0.2, dx.expected_score, 0.4, color="#c9ced6", label="expected"); ax.bar(x + 0.2, dx.points_elo, 0.4, color=GREEN, label="actual")
ax.set_xticks(x); ax.set_xticklabels(dx.index, fontsize=9); ax.legend(frameon=False, fontsize=8); clean(ax)
for xi, (a, e) in enumerate(zip(dx.points_elo, dx.expected_score)):
    ax.text(xi, max(a, e) + 0.6, f"{a - e:+.1f}", ha="center", fontsize=8, color=GREEN if a >= e else RED)
ax.set_title("Points vs expected, by decade", loc="left", fontsize=11)
ax = fig.add_axes([0.55, 0.06, 0.43, 0.28]); ax.axis("off"); ax.set_title("Biggest upset wins", loc="left", fontsize=11)
up = F[F.result == "W"].nsmallest(6, "p_win")
tb = ax.table(cellText=[[f"{r.date:%d %b %Y}", r.opponent, f"{r.gf}-{r.ga}", r.competition, f"{100 * r.p_win:.0f}%"] for r in up.itertuples()],
              colLabels=["Date", "Opponent", "Score", "Competition", "Win chance"], loc="upper left", cellLoc="left", edges="horizontal",
              colWidths=[0.17, 0.17, 0.1, 0.38, 0.15])
tb.auto_set_font_size(False); tb.set_fontsize(8.5); tb.scale(1, 1.45)
fig.savefig("previews/page2_strength.png", facecolor="white")

# ================================================= page 3: opponents
fig = plt.figure(figsize=(14, 9.5), dpi=110); header(fig, "Opponents", "strength = Elo gap before kick-off (±100)")
st = F.groupby("opponent_strength").agg(n=("result", "size"), s=("points_elo", "mean"))
tiles(fig, [(f"Points share vs weaker teams", f"{100 * st.s['Weaker']:.0f}%", f"{st.n['Weaker']} matches"),
            (f"vs similar teams", f"{100 * st.s['Similar']:.0f}%", f"{st.n['Similar']} matches"),
            (f"vs stronger teams", f"{100 * st.s['Stronger']:.0f}%", f"{st.n['Stronger']} matches")])
op = F.groupby("opponent").agg(P=("result", "size"), W=("result", lambda s: (s == "W").sum()), D=("result", lambda s: (s == "D").sum()),
                               L=("result", lambda s: (s == "L").sum()), GF=("gf", "sum"), GA=("ga", "sum"), elo=("opp_elo_before", "mean"))
op["win"] = 100 * op.W / op.P
ax = fig.add_axes([0.02, 0.05, 0.50, 0.71]); ax.axis("off"); ax.set_title("Head to head (12 most-played)", loc="left", fontsize=11)
t12 = op.sort_values("P", ascending=False).head(12)
tb = ax.table(cellText=[[o, int(r.P), int(r.W), int(r.D), int(r.L), int(r.GF), int(r.GA), f"{r.win:.0f}%", f"{r.elo:.0f}"] for o, r in t12.iterrows()],
              colLabels=["Opponent", "P", "W", "D", "L", "GF", "GA", "Win %", "Avg opp. Elo"], loc="upper left", cellLoc="left", edges="horizontal")
tb.auto_set_font_size(False); tb.set_fontsize(9); tb.scale(1, 1.6)
ax = fig.add_axes([0.58, 0.08, 0.40, 0.66]); clean(ax)
ax.scatter(op.P, op.win, s=40, color=np.where(op.index.isin(S.team.unique()), GREEN, GREY), alpha=0.85)
for o, r in op[op.P >= 8].iterrows(): ax.annotate(o, (r.P, r.win), xytext=(4, 3), textcoords="offset points", fontsize=8)
ax.set_xlabel("Matches played", fontsize=9); ax.set_ylabel("Win %", fontsize=9)
ax.set_title("Win % vs games played · green = South Asia", loc="left", fontsize=11)
fig.savefig("previews/page3_opponents.png", facecolor="white")

# ================================================= page 4: South Asia
fig = plt.figure(figsize=(14, 9.5), dpi=110); header(fig, "South Asia", "8 teams on the same Elo scale")
cur = H.sort_values("date").groupby("team").elo.last().sort_values(ascending=False)
bsa = F[F.opponent.isin(cur.index)]
tiles(fig, [("Position in South Asia (Elo)", f"{list(cur.index).index('Bangladesh') + 1} of 8", f"{cur.index[0]} top"),
            ("Gap to top team", f"{cur['Bangladesh'] - cur.iloc[0]:+.0f}", f"vs {cur.index[0]} ({cur.iloc[0]:.0f})"),
            ("Win rate vs South Asia", f"{100 * (bsa.result == 'W').mean():.0f}%", f"{(bsa.result == 'W').sum()} wins"),
            ("Matches vs South Asia", f"{len(bsa)}", f"of {len(F)} total")])
ax = fig.add_axes([0.05, 0.40, 0.80, 0.36]); clean(ax)
y = H.groupby([H.date.dt.year, "team"]).elo.last().unstack().reindex(range(1973, 2027)).ffill()
for t in y.columns:
    firsty = H[H.team == t].date.dt.year.min(); y.loc[y.index < firsty, t] = None
    ax.plot(y.index, y[t], color=GREEN if t == "Bangladesh" else "#c4c9cf", lw=2.6 if t == "Bangladesh" else 1.2, zorder=3 if t == "Bangladesh" else 1)
    off = {"Bangladesh": 28, "Pakistan": 0, "Nepal": -28, "Sri Lanka": 12, "Maldives": -12}.get(t, 0)
    ax.text(2026.5, y[t].dropna().iloc[-1] + off, t, fontsize=8, va="center", color=GREEN if t == "Bangladesh" else "#6b7280")
ax.set_xlim(1973, 2031); ax.set_title("Elo at the end of each year", loc="left", fontsize=11)
pt = S.groupby("team").agg(P=("result", "size"), win=("result", lambda s: 100 * (s == "W").mean()),
                           gf=("gf", "mean"), ga=("ga", "mean"))
hw = S[S.venue == "Home"].groupby("team").result.apply(lambda s: 100 * (s == "W").mean())
aw = S[S.venue == "Away"].groupby("team").result.apply(lambda s: 100 * (s == "W").mean())
pt["home_adv"] = hw - aw; pt["elo"] = cur; pt = pt.sort_values("elo", ascending=False)
ax = fig.add_axes([0.02, 0.04, 0.96, 0.30]); ax.axis("off"); ax.set_title("Peer table · since 1973", loc="left", fontsize=11)
tb = ax.table(cellText=[[t, f"{r.elo:.0f}", int(r.P), f"{r.win:.0f}%", f"{r.home_adv:+.0f} pts", f"{r.gf:.2f}", f"{r.ga:.2f}"] for t, r in pt.iterrows()],
              colLabels=["Team", "Elo now", "Matches", "Win %", "Home minus away win %", "Goals for / match", "Against / match"],
              loc="upper left", cellLoc="left", edges="horizontal")
tb.auto_set_font_size(False); tb.set_fontsize(9); tb.scale(1, 1.4)
fig.savefig("previews/page4_south_asia.png", facecolor="white")

# ================================================= page 5: competitions and coaches
fig = plt.figure(figsize=(14, 9.5), dpi=110); header(fig, "Competitions and coaches", "coach dates: Wikipedia list of managers")
cp = F[F.competition != "Friendlies"]
coached = F.merge(CO[["spell", "coach"]], on="spell")
tiles(fig, [("Competitive matches", f"{len(cp)}", "all except friendlies"),
            ("Competitive win rate", f"{100 * (cp.result == 'W').mean():.0f}%", f"friendlies {100 * (F[F.competition == 'Friendlies'].result == 'W').mean():.0f}%"),
            ("SAFF Cup best finish", "Champions", "2003 · runners-up 1999, 2005"),
            ("Head coaches covered", f"{coached.coach.nunique()}", f"{coached.spell.nunique()} spells")])
cr = F.groupby("competition").result.value_counts().unstack(fill_value=0).reindex(COMP.competition)
wdl_bars(fig.add_axes([0.15, 0.43, 0.32, 0.33]), cr.index.tolist(), cr.W, cr.D, cr.L, "Record by competition")
ax = fig.add_axes([0.55, 0.45, 0.43, 0.30]); clean(ax)
sf = SAFF[SAFF.position.notna()]
ax.scatter(sf.year, sf.position, s=90, color=[GREEN if p == 1 else (WIN if p == 2 else GREY) for p in sf.position], zorder=3)
ax.plot(sf.year, sf.position, color="#d5d9de", lw=1, zorder=1); ax.invert_yaxis(); ax.set_yticks(range(1, 8))
for r in sf.itertuples():
    if r.position <= 2: ax.annotate(r.finish, (r.year, r.position), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8)
ax.set_ylabel("Finish", fontsize=9); ax.set_title("SAFF Cup finish by edition", loc="left", fontsize=11)
sp = pd.read_csv("data/bd_coach_spells.csv"); sp = sp[sp.matches >= 10].sort_values("first")
ax = fig.add_axes([0.02, 0.04, 0.96, 0.32]); ax.axis("off"); ax.set_title("Head coaches · spells of 10+ matches", loc="left", fontsize=11)
tb = ax.table(cellText=[[r.coach, f"{r.first[:4]}–{r.last[:4]}", r.matches, f"{r.w}-{r.d}-{r.l}", f"{r.vs_expected:+.1f}", f"{r.elo_change:+.0f}"] for r in sp.itertuples()],
              colLabels=["Coach", "Years", "Matches", "W-D-L", "Points vs expected", "Elo change"], loc="upper left", cellLoc="left", edges="horizontal")
tb.auto_set_font_size(False); tb.set_fontsize(9); tb.scale(1, 1.45)
fig.savefig("previews/page5_competitions_coaches.png", facecolor="white")

# ================================================= page 6: match list (drill-through example: India)
ind = F[F.opponent == "India"].sort_values("date", ascending=False)
c = ind.result.value_counts()
fig = plt.figure(figsize=(14, 9.5), dpi=110); header(fig, "Match list · drill-through example: India")
fig.text(0.02, 0.89, f"{len(ind)} matches · {c.get('W', 0)} W, {c.get('D', 0)} D, {c.get('L', 0)} L", fontsize=12)
ax = fig.add_axes([0.02, 0.03, 0.96, 0.83]); ax.axis("off")
tb = ax.table(cellText=[[f"{r.date:%d %b %Y}", f"{r.gf}-{r.ga}" + (f" (pens {r.shootout.lower()})" if isinstance(r.shootout, str) and r.shootout else ""),
                         r.result, r.competition, r.venue, f"{100 * r.p_win:.0f}% / {100 * r.p_draw:.0f}% / {100 * r.p_loss:.0f}%", f"{r.elo_change:+.1f}"]
                        for r in ind.head(16).itertuples()],
              colLabels=["Date", "Score", "Result", "Competition", "Venue", "Win / draw / loss chance", "Elo change"],
              loc="upper left", cellLoc="left", edges="horizontal")
tb.auto_set_font_size(False); tb.set_fontsize(9.5); tb.scale(1, 1.65)
fig.savefig("previews/page6_match_list.png", facecolor="white")
print("saved 6 previews")
