"""Raw international results with this project's manual corrections applied.

manual/added_matches.csv  full internationals missing from the open dataset (Bangladesh's, plus the other South Asian
                          teams' 2026 SAFF Championship games), each confirmed by two independent sources
manual/date_fixes.csv     date corrections confirmed by two independent sources
(B-team exclusions stay in each script, via manual/excluded_matches.csv)
"""
import pandas as pd


def load_results():
    R = pd.read_csv("raw/results.csv", parse_dates=["date"])
    F = pd.read_csv("manual/date_fixes.csv", parse_dates=["old_date", "new_date"])
    for f in F.itertuples():
        hit = (R.date == f.old_date) & (R.home_team == f.home_team) & (R.away_team == f.away_team)
        assert hit.sum() == 1, f"date fix target not found exactly once: {f}"
        R.loc[hit, "date"] = f.new_date
    A = pd.read_csv("manual/added_matches.csv", parse_dates=["date"]).drop(columns="sources")
    for a in A.itertuples():
        dup = (R.date == a.date) & (R.home_team == a.home_team) & (R.away_team == a.away_team)
        assert not dup.any(), f"added match already present: {a}"
    R = pd.concat([R, A], ignore_index=True).sort_values("date", kind="stable").reset_index(drop=True)
    return R
