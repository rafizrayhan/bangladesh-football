"""Step 4: star-schema tables for the Power BI dashboard.

Lookup tables
  dim_year         1973-2026, with decade         -> year slider on every page
  dim_competition  competition group, competitive flag, sort order
  dim_venue        Home / Away / Neutral
  dim_opponent     every Bangladesh opponent, South Asia flag, current Elo
  dim_coach        one row per coaching spell (68)
  dim_team_sa      the 8 South Asian teams (page 4)
Fact tables
  fact_matches     Bangladesh matches with result, Elo, probabilities, coach
  fact_sa_matches  every match of the 8 South Asian teams since 1973 (peer table)
  fact_elo_history rating after every match, 8 South Asian teams
  fact_saff        Bangladesh finish in each SAFF Cup edition
"""
import os

import numpy as np
import pandas as pd

OUT = "data/pbi"
os.makedirs(OUT, exist_ok=True)
SA = ["Bangladesh", "India", "Nepal", "Maldives", "Sri Lanka", "Pakistan", "Bhutan", "Afghanistan"]
COMP_ORDER = ["World Cup qualifiers", "Asian Cup finals", "Asian Cup qualifiers", "SAFF Cup", "AFC Challenge Cup",
              "Asian Games", "South Asian Games", "FIFA ASEAN Cup", "Invitational tournaments", "Friendlies"]

M = pd.read_csv("data/bd_matches_full.csv", parse_dates=["date"])
CUR = pd.read_csv("data/elo_current.csv")
H = pd.read_csv("data/elo_history.csv", parse_dates=["date"])
C = pd.read_csv("manual/coaches.csv")
SP = pd.read_csv("data/bd_coach_spells.csv")
SAFF = pd.read_csv("manual/saff_finishes.csv")

# ---------------- dimensions
dim_year = pd.DataFrame({"year": range(1973, 2027)})
dim_year["decade"] = (dim_year.year // 10 * 10).astype(str) + "s"
dim_competition = pd.DataFrame({"competition": COMP_ORDER, "comp_order": range(1, len(COMP_ORDER) + 1)})
dim_competition["competitive"] = (dim_competition.competition != "Friendlies").astype(int)
dim_venue = pd.DataFrame({"venue": ["Home", "Away", "Neutral"], "venue_order": [1, 2, 3]})
elo_now = dict(zip(CUR.team, CUR.elo))
dim_opponent = (M.groupby("opponent").agg(matches=("match_id", "size")).reset_index())
dim_opponent["south_asia"] = dim_opponent.opponent.isin(SA).astype(int)
dim_opponent["region"] = np.where(dim_opponent.south_asia == 1, "South Asia", "Rest of the world")
dim_opponent["elo_now"] = dim_opponent.opponent.map(elo_now).round(0)
dim_coach = C[["spell", "coach", "nationality", "from", "to"]].copy()
dim_coach["to"] = dim_coach["to"].fillna("present")
dim_coach["spell_label"] = dim_coach.coach + " (" + dim_coach["from"].str[:4] + "–" + dim_coach["to"].str[:4].replace("pres", "now") + ")"
dim_team_sa = pd.DataFrame({"team": SA, "elo_now": [round(elo_now[t]) for t in SA]})
dim_team_sa["is_bangladesh"] = (dim_team_sa.team == "Bangladesh").astype(int)

# ---------------- fact_matches
F = M.copy()
F["date"] = F.date.dt.date
F["points_elo"] = F.actual_score                      # 1 win, 0.5 draw (used for points vs expected)
F["is_upset_win"] = ((F.result == "W") & (F.p_win < 0.25)).astype(int)
fact_matches = F[["match_id", "date", "year", "opponent", "competition", "venue", "spell", "city", "country", "tournament",
                  "gf", "ga", "result", "points", "points_elo", "expected_score", "p_win", "p_draw", "p_loss",
                  "bd_elo_before", "bd_elo_after", "elo_change", "opp_elo_before", "opponent_strength",
                  "shootout", "is_upset_win", "label"]]

# ---------------- fact_sa_matches: same competition grouping and venue logic for every South Asian team
from results_loader import load_results
R = load_results().dropna(subset=["home_score"])
X = pd.read_csv("manual/excluded_matches.csv", parse_dates=["date"])
R = R.merge(X[["date", "home_team", "away_team"]], how="left", indicator=True)
R = R[(R._merge == "left_only") & (R.date.dt.year >= 1973)].drop(columns="_merge")
GROUP = {"FIFA World Cup qualification": "World Cup qualifiers", "AFC Asian Cup qualification": "Asian Cup qualifiers",
         "AFC Asian Cup": "Asian Cup finals", "SAFF Cup": "SAFF Cup", "South Asian Games": "South Asian Games",
         "Asian Games": "Asian Games", "AFC Challenge Cup": "AFC Challenge Cup",
         "AFC Challenge Cup qualification": "AFC Challenge Cup", "FIFA ASEAN Cup": "FIFA ASEAN Cup", "Friendly": "Friendlies"}
rows = []
for side, opp, gf, ga in (("home_team", "away_team", "home_score", "away_score"), ("away_team", "home_team", "away_score", "home_score")):
    d = R[R[side].isin(SA)].copy()
    d["team"], d["opponent"], d["gf"], d["ga"] = d[side], d[opp], d[gf].astype(int), d[ga].astype(int)
    d["venue"] = np.where(d.neutral, "Neutral", "Home" if side == "home_team" else "Away")
    rows.append(d)
S = pd.concat(rows)
S["result"] = np.select([S.gf > S.ga, S.gf < S.ga], ["W", "L"], "D")
S["competition"] = S.tournament.map(GROUP).fillna("Invitational tournaments")
S["year"] = S.date.dt.year
S["vs_south_asia"] = S.opponent.isin(SA).astype(int)
S["date"] = S.date.dt.date
fact_sa_matches = S[["date", "year", "team", "opponent", "vs_south_asia", "venue", "competition", "gf", "ga", "result"]].sort_values(["date", "team"])

# ---------------- Elo history and SAFF
Hh = H[H.date.dt.year >= 1973].copy()
Hh["year"] = Hh.date.dt.year
Hh["date"] = Hh.date.dt.date
fact_elo_history = Hh[["date", "year", "team", "elo"]]
fact_saff = SAFF[["year", "finish", "position"]]

tables = dict(dim_year=dim_year, dim_competition=dim_competition, dim_venue=dim_venue, dim_opponent=dim_opponent,
              dim_coach=dim_coach, dim_team_sa=dim_team_sa, fact_matches=fact_matches, fact_sa_matches=fact_sa_matches,
              fact_elo_history=fact_elo_history, fact_saff=fact_saff)
for n, df in tables.items():
    df.to_csv(f"{OUT}/{n}.csv", index=False)

# ---------------- checks
fk = lambda f, c, d, k: f[c].isin(d[k]).all()
bd_sa = fact_sa_matches[fact_sa_matches.team == "Bangladesh"]
CH = [
    ("lookup keys unique", all(d[k].is_unique for d, k in ((dim_year, "year"), (dim_competition, "competition"), (dim_venue, "venue"),
                                                           (dim_opponent, "opponent"), (dim_coach, "spell"), (dim_team_sa, "team")))),
    ("fact_matches keys all found", fk(fact_matches, "year", dim_year, "year") and fk(fact_matches, "competition", dim_competition, "competition")
     and fk(fact_matches, "venue", dim_venue, "venue") and fk(fact_matches, "opponent", dim_opponent, "opponent")
     and fk(fact_matches, "spell", dim_coach, "spell")),
    ("fact_sa_matches keys all found", fk(fact_sa_matches, "year", dim_year, "year") and fk(fact_sa_matches, "competition", dim_competition, "competition")
     and fk(fact_sa_matches, "venue", dim_venue, "venue") and fk(fact_sa_matches, "team", dim_team_sa, "team")),
    ("elo history and SAFF years all found", fk(fact_elo_history, "year", dim_year, "year") and fk(fact_saff, "year", dim_year, "year")),
    ("322 Bangladesh matches, 87-66-169", len(fact_matches) == 322 and fact_matches.result.value_counts().to_dict() == {"L": 169, "W": 87, "D": 66}),
    ("peer table: Bangladesh rows = match table", len(bd_sa) == 322 and bd_sa.gf.sum() == 290 and bd_sa.ga.sum() == 587),
    ("peer table: venue and competition agree with match table",
     (bd_sa.sort_values("date").venue.values == fact_matches.sort_values("date").venue.values).all()
     and (bd_sa.sort_values("date").competition.values == fact_matches.sort_values("date").competition.values).all()),
    ("South Asian derbies counted from both sides",
     len(fact_sa_matches[fact_sa_matches.vs_south_asia == 1]) % 2 == 0),
    ("coach spells: matches add up to 322", SP.matches.sum() == 322),
]
for n, ok in CH:
    print(("PASS " if ok else "FAIL ") + n)
print()
for n, df in tables.items():
    print(f"{n:18s} {len(df):>6,} rows  {df.shape[1]:>2} cols")
