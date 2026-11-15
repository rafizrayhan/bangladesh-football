"""Step 7: web/data.json for the HTML dashboard, built from the tableau/ tables.

m:   one row per Bangladesh match
s:   every match by the 8 South Asian teams (for the peer table)
elo: end-of-year Elo for the 8 South Asian teams, 1973-2026, forward-filled, null before a team's first match
"""
import json
import sys

import pandas as pd

M = pd.read_csv("tableau/bd_matches.csv")
S = pd.read_csv("tableau/sa_matches.csv")
H = pd.read_csv("tableau/sa_elo_history.csv")
SAFF = pd.read_csv("tableau/saff_finishes.csv")
COACH = pd.read_csv("manual/coaches.csv")
SA = ["Bangladesh", "India", "Nepal", "Maldives", "Sri Lanka", "Pakistan", "Bhutan", "Afghanistan"]
YEARS = list(range(1973, 2027))
COMPS = ["World Cup qualifiers", "Asian Cup finals", "Asian Cup qualifiers", "SAFF Cup", "AFC Challenge Cup", "Asian Games",
         "South Asian Games", "FIFA ASEAN Cup", "Invitational tournaments", "Friendlies"]
nz = lambda v: "" if pd.isna(v) else v

# chances and ratings keep full working precision; the page rounds them once, for display
m = [[r.date, int(r.year), r.opponent, r.competition, r.venue, int(r.gf), int(r.ga), r.result, round(float(r.expected_score), 6),
      round(float(r.p_win), 6), round(float(r.p_draw), 6), round(float(r.p_loss), 6), round(float(r.bd_elo_before), 3),
      round(float(r.bd_elo_after), 3), round(float(r.opp_elo_before), 3), r.opponent_strength, nz(r.shootout), int(r.spell),
      r.tournament, nz(r.city), int(r.south_asia)] for r in M.itertuples()]
# friendly matches that belonged to small named tournaments (Wikipedia + a second source, see manual/honours.csv)
EVENT = {"1995-10-26": "Burma Tournament (4-nation Tiger Trophy)", "1995-11-01": "Burma Tournament (4-nation Tiger Trophy)",
         "1995-11-04": "Burma Tournament (4-nation Tiger Trophy)", "2020-11-13": "Mujib Borsho FIFA International Series",
         "2020-11-17": "Mujib Borsho FIFA International Series", "2021-03-27": "Three Nations Cup (Nepal)", "2021-03-29": "Three Nations Cup (Nepal)"}
for row in m:
    if row[0] in EVENT:
        assert row[18] == "Friendly", row
        row[18] = EVENT[row[0]]
assert sum(row[18] in EVENT.values() for row in m) == 7
CAMP = pd.read_csv("manual/campaigns.csv", dtype=str).fillna("")
camps = [[r.sheet, int(r.edition), [int(y) for y in r.match_years.split(";")] if r.match_years else [], r.stage,
          int(r.level) if r.level else None, r.teams_note, r.source] for r in CAMP.itertuples()]
SHEET_OF = {"World Cup qualifiers": ["World Cup qualifiers"], "Asian Cup": ["Asian Cup qualifiers", "Asian Cup finals"], "South Asian Games": ["South Asian Games"],
            "AFC Challenge Cup": ["AFC Challenge Cup"], "Asian Games": ["Asian Games"], "FIFA ASEAN Cup": ["FIFA ASEAN Cup"]}
for c in camps:  # every match in a listed year belongs to exactly one edition
    n = sum(1 for row in m if row[3] in SHEET_OF[c[0]] and row[1] in c[2])
    assert (n > 0) == bool(c[2]), c
for sh, cats in SHEET_OF.items():
    yrs = [y for c in camps if c[0] == sh for y in c[2]]
    assert len(yrs) == len(set(yrs)), sh
    loose = [row[0] for row in m if row[3] in cats and row[1] not in yrs]
    assert not loose, (sh, loose)
HON = pd.read_csv("manual/honours.csv", dtype=str).fillna("")
honours = [[int(r.year), r.event, r.finish, r.where, r.in_list, r.note, r.source] for r in HON.itertuples()]
s = [[r.team, int(r.year), r.venue, r.competition, int(r.gf), int(r.ga), r.result] for r in S.itertuples()]
elo = {}
for t in sorted(SA):
    h = H[H.team == t].sort_values("date")
    vals, last = [], None
    for y in YEARS:
        hy = h[h.year == y]
        if len(hy): last = round(float(hy.elo.iloc[-1]), 3)
        vals.append(last)
    elo[t] = vals
coaches = {str(int(r.spell)): [r.coach, r.nationality] for r in COACH.itertuples()}
saff = [[int(r.year), r.finish, None if pd.isna(r.position) else int(r.position)] for r in SAFF.itertuples()]
# ---- published World Football Elo (eloratings.net yearly archive, via github.com/JGravier/soccer-elo), to check our ratings
import numpy as np
from scipy.stats import spearmanr
P = pd.read_csv("raw/eloratings_yearly_sa.csv")
P["rating"] = pd.to_numeric(P.rating, errors="coerce")
pub = {t: [None if P[(P.team == t) & (P.year == y)].empty else float(P[(P.team == t) & (P.year == y)].rating.iloc[0]) for y in YEARS] for t in SA}
pairs = [(t, y, elo[t][i], pub[t][i]) for t in SA for i, y in enumerate(YEARS) if elo[t][i] is not None and pub[t][i] is not None]
Q = pd.DataFrame(pairs, columns=["team", "year", "ours", "pub"])
b = Q[Q.team == "Bangladesh"].set_index("year")
ch = b[["ours", "pub"]].diff().dropna(); ch = ch[(ch.ours != 0) | (ch.pub != 0)]
same_pos, rho = 0, []
for y, g in Q.groupby("year"):
    if len(g) < 4: continue
    rho.append(spearmanr(g.ours, g.pub).correlation)
    same_pos += g.sort_values("ours", ascending=False).team.tolist().index("Bangladesh") == g.sort_values("pub", ascending=False).team.tolist().index("Bangladesh")
last = Q[Q.year == Q.year.max()]
elo_check = dict(first=int(Q.year.min()), last=int(Q.year.max()), pairs=len(Q), corr_all=round(float(Q.ours.corr(Q.pub)), 3),
                 corr_change=round(float(ch.ours.corr(ch.pub)), 3), same_dir=int((np.sign(ch.ours) == np.sign(ch.pub)).sum()), n_change=len(ch),
                 rho_median=round(float(np.median(rho)), 2), same_pos=int(same_pos), n_years=len(rho),
                 last_ours_pos=int(last.sort_values("ours", ascending=False).team.tolist().index("Bangladesh") + 1),
                 last_pub_pos=int(last.sort_values("pub", ascending=False).team.tolist().index("Bangladesh") + 1),
                 mean_gap=round(float((b.ours - b.pub).mean())),
                 bd_corr_all=round(float(b.ours.corr(b.pub)), 2), bd_corr_1985=round(float(b[b.index >= 1985].ours.corr(b[b.index >= 1985].pub)), 2),
                 bd_gap_1985=round(float((b[b.index >= 1985].ours - b[b.index >= 1985].pub).abs().mean())))
REC = pd.read_csv("manual/record_holders.csv")
records = {k: [[r.player, int(r.caps), int(r.goals), r.career] for r in REC[REC.list == k].itertuples()] for k in ("caps", "goals")}
CS = pd.read_csv("manual/clean_sheets.csv")
records["cs"] = [[r.player, int(r.caps), int(r.clean_sheets), r.career] for r in CS.itertuples()]
G = pd.read_csv("raw/goalscorers.csv")
known = int(len(G[G.team == "Bangladesh"].merge(M[["date"]], on="date")))
FI = pd.read_csv("manual/fifa_ranking.csv")
fifa = {r.item: [int(r.rank), r.when] for r in FI.itertuples()}
out = dict(m=m, s=s, elo=elo, years=YEARS, coaches=coaches, saff=saff, comps=COMPS, eloPub=pub["Bangladesh"], eloCheck=elo_check,
           records=records, fifa=fifa, knownScorers=known, camps=camps, honours=honours)
print("elo check", elo_check)
path = sys.argv[1] if len(sys.argv) > 1 else "web/data.json"
json.dump(out, open(path, "w"), separators=(",", ":"), ensure_ascii=False)
print("wrote", path, "matches", len(m), "sa rows", len(s))
