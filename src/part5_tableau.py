"""Step 5: Tableau-ready files (wide tables, lookups already joined in).

tableau/bd_matches.csv     one row per Bangladesh match: result, Elo, probabilities, coach, opponent info
tableau/sa_matches.csv     every match of the 8 South Asian teams since 1973 (peer table)
tableau/sa_elo_history.csv rating after every match, 8 South Asian teams
tableau/saff_finishes.csv  Bangladesh finish in each SAFF Cup edition
"""
import os

import pandas as pd

D, OUT = "data/pbi", "tableau"
os.makedirs(OUT, exist_ok=True)
F = pd.read_csv(f"{D}/fact_matches.csv")
comp = pd.read_csv(f"{D}/dim_competition.csv")
ven = pd.read_csv(f"{D}/dim_venue.csv")
opp = pd.read_csv(f"{D}/dim_opponent.csv")
coach = pd.read_csv(f"{D}/dim_coach.csv")

M = (F.merge(comp, on="competition").merge(ven, on="venue")
      .merge(opp[["opponent", "south_asia", "region", "elo_now"]].rename(columns={"elo_now": "opp_elo_now"}), on="opponent")
      .merge(coach[["spell", "coach", "nationality", "spell_label"]], on="spell"))
M["decade"] = (M.year // 10 * 10).astype(str) + "s"
M["wins"] = (M.result == "W").astype(int)
M["draws"] = (M.result == "D").astype(int)
M["losses"] = (M.result == "L").astype(int)
M = M.sort_values("date")
M.to_csv(f"{OUT}/bd_matches.csv", index=False)

S = pd.read_csv(f"{D}/fact_sa_matches.csv")
S["wins"] = (S.result == "W").astype(int)
S.to_csv(f"{OUT}/sa_matches.csv", index=False)
pd.read_csv(f"{D}/fact_elo_history.csv").to_csv(f"{OUT}/sa_elo_history.csv", index=False)
pd.read_csv(f"{D}/fact_saff.csv").to_csv(f"{OUT}/saff_finishes.csv", index=False)

C = [("322 matches", len(M) == 322), ("no rows lost in joins", M.match_id.nunique() == 322),
     ("87 wins, 66 draws, 169 losses", (M.wins.sum(), M.draws.sum(), M.losses.sum()) == (87, 66, 169)),
     ("every match has a coach and competition order", M.coach.notna().all() and M.comp_order.notna().all())]
for n, ok in C:
    print(("PASS " if ok else "FAIL ") + n)
for f in sorted(os.listdir(OUT)):
    d = pd.read_csv(f"{OUT}/{f}")
    print(f"{f:20s} {len(d):>5} rows {d.shape[1]:>3} cols")
