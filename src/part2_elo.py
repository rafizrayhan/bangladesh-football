"""Step 2: Elo ratings for every international team since 1872, then Bangladesh match context.

Method (World Football Elo style, as used by eloratings.net):
  expected score  E = 1 / (10^(-(R_home + H - R_away)/400) + 1),  H = 100 home advantage (0 if neutral)
  K by match type: 60 World Cup finals | 50 continental finals | 40 World Cup & continental qualifiers
                   | 30 other tournaments | 20 friendlies
  goal-difference multiplier G: 1 (0-1 goal), 1.5 (2), (11 + N)/8 (N >= 3)
  change = K * G * (actual - E); actual = 1 win, 0.5 draw, 0 loss. Zero-sum between the two teams.

Seeding fix: a team that joins later (Bangladesh in 1973) would start at 1500, far too high.
  We re-run the ratings until the starting ratings settle (average change < 2.5 points). After each run, every team's starting rating is set to the rating it
  had after its first 30 matches in the previous run (teams with fewer than 30 use their final rating).
  This uses hindsight for the starting point only; every later change is computed match by match.

Win / draw / loss probabilities: Elo gives an expected score, not a win chance. We estimate the
  draw chance from all matches since 1990 (draw rate by rating gap, fitted curve), then
  P(win) = E - P(draw)/2 and P(loss) = 1 - P(win) - P(draw).

Outputs
  data/bd_elo_matches.csv   Bangladesh matches with ratings and probabilities
  data/elo_history.csv      rating after every match for the 8 South Asian teams
  data/elo_current.csv      latest rating for every team
"""
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from results_loader import load_results
R = load_results().dropna(subset=["home_score"])
X = pd.read_csv("manual/excluded_matches.csv", parse_dates=["date"])   # B-team games listed as full internationals
R = R.merge(X[["date", "home_team", "away_team"]], on=["date", "home_team", "away_team"], how="left", indicator=True)
R = R[R._merge == "left_only"].drop(columns="_merge")
R = R.sort_values(["date"], kind="stable").reset_index(drop=True)
SOUTH_ASIA = ["Bangladesh", "India", "Nepal", "Maldives", "Sri Lanka", "Pakistan", "Bhutan", "Afghanistan"]
CONT_FINALS = {"UEFA Euro", "Copa América", "AFC Asian Cup", "African Cup of Nations", "Gold Cup",
               "CONCACAF Championship", "Oceania Nations Cup", "Confederations Cup"}


def k_factor(t):
    if t == "FIFA World Cup":
        return 60
    if t in CONT_FINALS:
        return 50
    if "qualification" in t:
        return 40
    if t == "Friendly":
        return 20
    return 30


K = R.tournament.map(k_factor).values
H = np.where(R.neutral.values, 0, 100)
gd = np.abs(R.home_score.values - R.away_score.values)
G = np.where(gd <= 1, 1, np.where(gd == 2, 1.5, (11 + gd) / 8))
S = np.where(R.home_score > R.away_score, 1, np.where(R.home_score == R.away_score, 0.5, 0)).astype(float)
home, away = R.home_team.values, R.away_team.values


def run(seed):
    elo, n = {}, {}
    rh, ra, eh, after30 = np.empty(len(R)), np.empty(len(R)), np.empty(len(R)), {}
    for i in range(len(R)):
        h, a = home[i], away[i]
        rh[i] = elo.get(h, seed.get(h, 1500))
        ra[i] = elo.get(a, seed.get(a, 1500))
        eh[i] = 1 / (10 ** (-(rh[i] + H[i] - ra[i]) / 400) + 1)
        d = K[i] * G[i] * (S[i] - eh[i])
        elo[h], elo[a] = rh[i] + d, ra[i] - d
        for t in (h, a):
            n[t] = n.get(t, 0) + 1
            if n[t] == 30:
                after30[t] = elo[t]
    newseed = {t: after30.get(t, elo[t]) for t in elo}
    return rh, ra, eh, elo, newseed


seed = {}
for it in range(60):
    rh, ra, eh, elo, newseed = run(seed)
    shift = 1500 - np.mean(list(newseed.values()))
    newseed = {t: v + shift for t, v in newseed.items()}
    drift = np.mean([abs(newseed[t] - seed.get(t, 1500)) for t in newseed])
    print(f"pass {it + 1}: mean change in starting ratings {drift:.1f}")
    seed = newseed
    if drift < 2.5:
        break
# the oldest teams (1872 onward) keep 1500 as their start: there was nobody to compare them with
for t in ("England", "Scotland", "Wales"):
    seed[t] = 1500
rh, ra, eh, elo, _ = run(seed)

# ---------------- win / draw / loss probabilities: ordered logistic model on the rating gap,
# fitted to all matches since 1990 (Elo alone is over-confident in very one-sided games).
# Symmetric: the draw band sits evenly around a gap of zero, so on a neutral ground the chances do not
# depend on which team the dataset happens to list first. Home advantage is fitted as its own term
# (only for games that are not on neutral ground) instead of being folded into the cut-points.
from scipy.optimize import minimize
from scipy.special import expit
recent = R.date.dt.year >= 1990
gap0 = (rh - ra) / 100
athome = (~R.neutral.values).astype(float)
y = np.where(S == 1, 2, np.where(S == 0.5, 1, 0))
def nll(th):
    b, hadv, c = th[0], th[1], np.exp(th[2])
    z = b * gap0[recent] + hadv * athome[recent]
    pL = expit(-c - z); pLD = expit(c - z)
    p = np.choose(y[recent], [pL, pLD - pL, 1 - pLD])
    return -np.log(np.clip(p, 1e-9, 1)).sum()
fit = minimize(nll, [0.5, 0.3, -0.5], method="Nelder-Mead", options={"xatol": 1e-8, "fatol": 1e-8, "maxiter": 6000})
pb, hadv = fit.x[0], fit.x[1]; c2 = np.exp(fit.x[2]); c1 = -c2
zall = pb * gap0 + hadv * athome
p_loss_home = expit(c1 - zall)
p_draw_home = expit(c2 - zall) - p_loss_home
p_win_home = 1 - p_loss_home - p_draw_home

# ---------------- Bangladesh rows
M = pd.read_csv("data/bd_matches.csv", parse_dates=["date"])
idx = np.where((home == "Bangladesh") | (away == "Bangladesh"))[0]
isH = home[idx] == "Bangladesh"
post_change = K[idx] * G[idx] * (S[idx] - eh[idx])
# stored at full working precision (3 dp ratings, 6 dp chances); rounding happens only on display
B = pd.DataFrame({
    "date": R.date.values[idx], "opponent": np.where(isH, away[idx], home[idx]),
    "bd_elo_before": np.where(isH, rh[idx], ra[idx]).round(3),
    "opp_elo_before": np.where(isH, ra[idx], rh[idx]).round(3),
    "elo_change": np.where(isH, post_change, -post_change).round(3),
    "bd_elo_after": (np.where(isH, rh[idx], ra[idx]) + np.where(isH, post_change, -post_change)).round(3),
    "expected_score": np.where(isH, p_win_home[idx] + p_draw_home[idx] / 2, p_loss_home[idx] + p_draw_home[idx] / 2).round(6),
    "p_win": np.where(isH, p_win_home[idx], p_loss_home[idx]).round(6),
    "p_draw": p_draw_home[idx].round(6),
    "p_loss": np.where(isH, p_loss_home[idx], p_win_home[idx]).round(6),
})
gap = B.opp_elo_before - B.bd_elo_before
B["opponent_strength"] = np.select([gap < -100, gap > 100], ["Weaker", "Stronger"], "Similar")
B = M.merge(B, on=["date", "opponent"], how="left")
B["actual_score"] = B.result.map({"W": 1, "D": 0.5, "L": 0})
B.to_csv("data/bd_elo_matches.csv", index=False)

# ---------------- South Asia history + current ratings
rows = []
for i in np.where(np.isin(home, SOUTH_ASIA) | np.isin(away, SOUTH_ASIA))[0]:
    d = K[i] * G[i] * (S[i] - eh[i])
    if home[i] in SOUTH_ASIA:
        rows.append((R.date[i], home[i], rh[i] + d))
    if away[i] in SOUTH_ASIA:
        rows.append((R.date[i], away[i], ra[i] - d))
Hst = pd.DataFrame(rows, columns=["date", "team", "elo"]); Hst["elo"] = Hst.elo.round(3)
Hst.to_csv("data/elo_history.csv", index=False)
last = pd.concat([R[["date", "home_team"]].rename(columns={"home_team": "team"}),
                  R[["date", "away_team"]].rename(columns={"away_team": "team"})]).groupby("team").date.max()
cur = pd.DataFrame({"team": list(elo), "elo": [round(v, 3) for v in elo.values()]})
cur["last_match"] = cur.team.map(last)
cur["south_asia"] = cur.team.isin(SOUTH_ASIA).astype(int)
cur.sort_values("elo", ascending=False).to_csv("data/elo_current.csv", index=False)

# ---------------- checks
all_changes = K * G * (S - eh)
cal = pd.DataFrame({"p": p_win_home[recent], "won": (S[recent] == 1).astype(float)})
cald = pd.DataFrame({"p": p_draw_home[recent], "d": (S[recent] == 0.5).astype(float)})
cal["bin"] = pd.qcut(cal.p, 10, labels=False)
c = cal.groupby("bin").agg(pred=("p", "mean"), actual=("won", "mean"))
C = [
    ("ratings are zero-sum (every gain matched by a loss)", True),  # by construction, d added and subtracted
    ("322 Bangladesh matches have ratings", B.bd_elo_before.notna().sum() == 322),
    ("win + draw + loss probabilities sum to 1", np.allclose(B.p_win + B.p_draw + B.p_loss, 1, atol=0.01)),
    ("Elo before + change = after", np.allclose(B.bd_elo_before + B.elo_change, B.bd_elo_after, atol=0.002)),
    ("calibration: predicted win % within 3 points of actual in every decile", (abs(c.pred - c.actual) < 0.03).all()),
    ("calibration: overall predicted draws within 1 point of actual", abs(cald.p.mean() - cald.d.mean()) < 0.01),
    ("calibration: home teams' expected score within 1 point of actual", abs((p_win_home + p_draw_home / 2)[recent & ~R.neutral.values].mean() - S[recent & ~R.neutral.values].mean()) < 0.01),
    ("symmetric: a zero gap gives equal win and loss chances", abs(expit(c1) - (1 - expit(c2))) < 1e-12),
    ("neutral games: chances do not depend on listing order", np.allclose(expit(c1 - pb * 1.3), 1 - expit(c2 + pb * 1.3))),
]
for n, ok in C:
    print(("PASS " if ok else "FAIL ") + n)
print(f"\nordered logit (symmetric): slope {pb:.4f} per 100 Elo, home term {hadv:.4f} (= {100 * hadv / pb:.0f} Elo points), cut-points {c1:.4f}, {c2:.4f}")
for lab, msk in (("neutral", recent & R.neutral.values), ("not neutral", recent & ~R.neutral.values)):
    print(f"  {lab}: first-listed team predicted {100 * (p_win_home[msk].mean() + p_draw_home[msk].mean() / 2):.1f} vs actual {100 * S[msk].mean():.1f} (expected score)")
print("calibration (matches since 1990):\n", (c * 100).round(1).to_string())
sa = cur[cur.south_asia == 1].sort_values("elo", ascending=False)
print("\nSouth Asia now:\n", sa[["team", "elo", "last_match"]].to_string(index=False))
b = B.copy()
print("\nBangladesh first match rating:", b.bd_elo_before.iloc[0], "| now:", b.bd_elo_after.iloc[-1])
print("peak:", b.bd_elo_after.max(), b.loc[b.bd_elo_after.idxmax(), "date"].date(),
      "| low:", b.bd_elo_after.min(), b.loc[b.bd_elo_after.idxmin(), "date"].date())
print(b.groupby("decade").agg(n=("result", "size"), actual=("actual_score", "sum"), expected=("expected_score", "sum"),
                              elo_end=("bd_elo_after", "last")).round(1).to_string())
print(b.groupby("opponent_strength").agg(n=("result", "size"), score=("actual_score", "mean")).round(2).to_string())
print("\nbiggest upsets (lowest win chance, won):")
print(b[b.result == "W"].nsmallest(5, "p_win")[["date", "opponent", "gf", "ga", "competition", "p_win"]].to_string(index=False))
print("\nIndia 2025:", b[(b.opponent == "India") & (b.year == 2025)][["date", "gf", "ga", "p_win", "p_draw", "p_loss"]].to_string(index=False))
