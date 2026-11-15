"""Step 3: assign every Bangladesh match to the head coach in charge.

Source: Wikipedia, "List of Bangladesh national football team managers" (accessed 6 Nov 2026),
transcribed to manual/coaches.csv. Dates given only as a month cover the whole month.
A match falling in two spells (the outgoing and incoming coach share a boundary month) goes to the
outgoing coach: in both such cases (Aug 1984, Apr 1985) that matches Wikipedia's records exactly.
"""
import calendar
import pandas as pd

C = pd.read_csv("manual/coaches.csv", dtype=str)
def start(s):
    return pd.Timestamp(s + "-01") if len(s) == 7 else pd.Timestamp(s)
def end(s):
    if not isinstance(s, str) or s == "":
        return pd.Timestamp("2100-01-01")
    if len(s) == 7:
        y, m = map(int, s.split("-"))
        return pd.Timestamp(y, m, calendar.monthrange(y, m)[1])
    return pd.Timestamp(s)
C["start"], C["end"] = C["from"].map(start), C["to"].map(end)
for c in ("wiki_p", "wiki_w", "wiki_d", "wiki_l"):
    C[c] = C[c].astype(int)

M = pd.read_csv("data/bd_elo_matches.csv", parse_dates=["date"])
cand = [list(C[(C.start <= d) & (C.end >= d)].spell) for d in M.date]
M["n_cand"] = [len(c) for c in cand]
M["spell"] = [c[0] if c else None for c in cand]   # outgoing coach keeps a shared month
amb = M[M.n_cand > 1][["date", "opponent", "gf", "ga"]].assign(spells=[c for c in cand if len(c) > 1])
none = M[M.n_cand == 0][["date", "opponent", "gf", "ga", "competition"]]

rec = M.dropna(subset=["spell"]).groupby("spell").result.value_counts().unstack(fill_value=0)
for r in "WDL":
    if r not in rec: rec[r] = 0
rec["P"] = rec[["W", "D", "L"]].sum(axis=1)
chk = C.set_index("spell")[["coach", "wiki_p", "wiki_w", "wiki_d", "wiki_l"]].join(rec[["P", "W", "D", "L"]], how="left").fillna(0)
chk["match"] = (chk.wiki_p == chk.P) & (chk.wiki_w == chk.W) & (chk.wiki_d == chk.D) & (chk.wiki_l == chk.L)
print(f"matches with one coach: {(M.n_cand == 1).sum()} | shared-month: {len(amb)} | no coach listed: {len(none)}")
print(f"spells whose W-D-L matches Wikipedia exactly: {chk.match.sum()} of {len(chk)}")
print("\nspells that differ (ours vs Wikipedia):")
print(chk[~chk.match][["coach", "P", "W", "D", "L", "wiki_p", "wiki_w", "wiki_d", "wiki_l"]].astype({"P": int, "W": int, "D": int, "L": int}).to_string())
print("\nshared-month matches:\n", amb.to_string(index=False))
print("\nmatches with no coach listed:\n", none.to_string(index=False))

# ---------------- outputs
M["spell"] = M.spell.astype(int)
info = C.set_index("spell")[["coach", "nationality", "start", "end"]]
info.index = info.index.astype(int)
M = M.join(info[["coach"]], on="spell")
M.drop(columns=["n_cand"]).to_csv("data/bd_matches_full.csv", index=False)
sp = M.groupby("spell").agg(matches=("result", "size"), w=("result", lambda s: (s == "W").sum()),
                            d=("result", lambda s: (s == "D").sum()), l=("result", lambda s: (s == "L").sum()),
                            actual=("actual_score", "sum"), expected=("expected_score", "sum"),
                            elo_start=("bd_elo_before", "first"), elo_end=("bd_elo_after", "last"),
                            first=("date", "min"), last=("date", "max"))
sp = info.join(sp, how="inner")
sp["elo_change"] = (sp.elo_end - sp.elo_start).round(1)
sp["vs_expected"] = (sp.actual - sp.expected).round(2)
sp.reset_index().rename(columns={"index": "spell"}).to_csv("data/bd_coach_spells.csv", index=False)
major = sp[sp.matches >= 10].sort_values("first")
print("\ncoaches with 10+ matches in a spell:")
print(major[["coach", "first", "last", "matches", "w", "d", "l", "vs_expected", "elo_change"]].to_string())
