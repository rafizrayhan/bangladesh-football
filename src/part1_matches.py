"""Step 1: clean Bangladesh match table from the open international results dataset.

Source: github.com/martj42/international_results (results.csv, shootouts.csv)
Output: data/bd_matches.csv, one row per Bangladesh men's full international.

Notes
  The dataset lists only full internationals, so the South Asian Games (to 1999) and Asian Games
  (to 1990) appear only from the years they were played by senior teams.
  "Competitive" = every match that is not a friendly.
"""
import os

import pandas as pd

os.makedirs("data", exist_ok=True)
from results_loader import load_results
R = load_results()
SO = pd.read_csv("raw/shootouts.csv", parse_dates=["date"])
X = pd.read_csv("manual/excluded_matches.csv", parse_dates=["date"])   # B-team games listed as full internationals
R = R.merge(X[["date", "home_team", "away_team"]], on=["date", "home_team", "away_team"], how="left", indicator=True)
R = R[R._merge == "left_only"].drop(columns="_merge")

SOUTH_ASIA = ["Bangladesh", "India", "Nepal", "Maldives", "Sri Lanka", "Pakistan", "Bhutan", "Afghanistan"]
GROUP = {
    "FIFA World Cup qualification": "World Cup qualifiers",
    "AFC Asian Cup qualification": "Asian Cup qualifiers",
    "AFC Asian Cup": "Asian Cup finals",
    "SAFF Cup": "SAFF Cup",
    "South Asian Games": "South Asian Games",
    "Asian Games": "Asian Games",
    "AFC Challenge Cup": "AFC Challenge Cup",
    "AFC Challenge Cup qualification": "AFC Challenge Cup",
    "FIFA ASEAN Cup": "FIFA ASEAN Cup",
    "Friendly": "Friendlies",
}

B = R[(R.home_team == "Bangladesh") | (R.away_team == "Bangladesh")].copy()
home = B.home_team == "Bangladesh"
B["opponent"] = B.away_team.where(home, B.home_team)
B["gf"] = B.home_score.where(home, B.away_score).astype(int)
B["ga"] = B.away_score.where(home, B.home_score).astype(int)
B["venue"] = "Away"
B.loc[home, "venue"] = "Home"
B.loc[B.neutral, "venue"] = "Neutral"
B["result"] = "D"
B.loc[B.gf > B.ga, "result"] = "W"
B.loc[B.gf < B.ga, "result"] = "L"
B["points"] = B.result.map({"W": 3, "D": 1, "L": 0})
B["competition"] = B.tournament.map(GROUP).fillna("Invitational tournaments")
B["competitive"] = (B.competition != "Friendlies").astype(int)
B["opponent_south_asia"] = B.opponent.isin(SOUTH_ASIA).astype(int)
B["year"] = B.date.dt.year
B["decade"] = (B.year // 10 * 10).astype(str) + "s"

so = SO.merge(B[["date", "home_team", "away_team"]], on=["date", "home_team", "away_team"])
B = B.merge(so[["date", "home_team", "away_team", "winner"]], on=["date", "home_team", "away_team"], how="left")
B["shootout"] = B.winner.map(lambda w: "" if pd.isna(w) else ("Won" if w == "Bangladesh" else "Lost"))
B = B.drop(columns="winner").sort_values("date").reset_index(drop=True)
B.insert(0, "match_id", range(1, len(B) + 1))
B["label"] = B.date.dt.strftime("%d %b %Y") + " · " + B.opponent + " " + B.gf.astype(str) + "-" + B.ga.astype(str)

cols = ["match_id", "date", "year", "decade", "opponent", "opponent_south_asia", "venue", "city", "country",
        "tournament", "competition", "competitive", "gf", "ga", "result", "points", "shootout", "label"]
B[cols].to_csv("data/bd_matches.csv", index=False)

# ---------------- checks
C = [
    ("322 matches (315 in the dataset minus 2 B-team games plus 9 added from two sources)", len(B) == 322),
    ("added Bangladesh matches all present (9)", len(B.merge(pd.read_csv("manual/added_matches.csv", parse_dates=["date"]).query("home_team == 'Bangladesh' or away_team == 'Bangladesh'")[["date", "home_team", "away_team"]], on=["date", "home_team", "away_team"])) == 9),
    ("Nepal 1995 SAFF Cup moved to 27 March", ((B.date == "1995-03-27") & (B.opponent == "Nepal")).any() and not ((B.date == "1995-03-25") & (B.opponent == "Nepal")).any()),
    ("no missing scores", B[["gf", "ga"]].notna().all().all()),
    ("no duplicate date + opponent", not B.duplicated(["date", "opponent"]).any()),
    ("W + D + L = matches", B.result.value_counts().sum() == len(B)),
    ("goals for = 290, against = 587 (281/580 plus the added matches 9/7)", B.gf.sum() == 290 and B.ga.sum() == 587),
    ("every tournament has a competition group", B.competition.notna().all()),
    ("shootouts only after draws", (B[B.shootout != ""].result == "D").all()),
    ("verified: Bangladesh 1-0 India, 18 Nov 2025",
     ((B.date == "2025-11-18") & (B.opponent == "India") & (B.gf == 1) & (B.ga == 0)).any()),
    ("verified: San Marino 1-2 Bangladesh, 5 Jun 2026",
     ((B.date == "2026-06-05") & (B.opponent == "San Marino") & (B.gf == 2) & (B.ga == 1)).any()),
    ("verified: Indonesia 9-2 Bangladesh, 1 Oct 2026",
     ((B.date == "2026-10-01") & (B.opponent == "Indonesia") & (B.gf == 2) & (B.ga == 9)).any()),
    ("added: Singapore 1-0 Bangladesh, 31 Mar 2026", ((B.date == "2026-03-31") & (B.opponent == "Singapore") & (B.gf == 0) & (B.ga == 1)).any()),
    ("added: Bangladesh 4-0 Sri Lanka, 11 Nov 2026 (SAFF)", ((B.date == "2026-11-11") & (B.opponent == "Sri Lanka") & (B.gf == 4) & (B.ga == 0) & (B.venue == "Home")).any()),
    ("added: Bangladesh 0-1 Pakistan, 14 Nov 2026 (SAFF semi-final)", ((B.date == "2026-11-14") & (B.opponent == "Pakistan") & (B.gf == 0) & (B.ga == 1) & (B.venue == "Home")).any()),
    ("added: Bangladesh 1-0 Bhutan, 5 Nov 2026 (SAFF)", ((B.date == "2026-11-05") & (B.opponent == "Bhutan") & (B.gf == 1) & (B.ga == 0) & (B.venue == "Home")).any()),
]
for n, ok in C:
    print(("PASS " if ok else "FAIL ") + n)
print()
print(B.result.value_counts().to_dict(), "| competitive", B.competitive.sum(), "| vs South Asia", B.opponent_south_asia.sum())
print(B.competition.value_counts().to_string())
print("shootouts:", B[B.shootout != ""][["date", "opponent", "tournament", "shootout"]].to_string(index=False))
print("\nSAFF Cup by edition (year: W-D-L):")
s = B[B.competition == "SAFF Cup"].groupby("year").result.value_counts().unstack(fill_value=0)
print(s.to_string())
