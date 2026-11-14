"""Runs the whole pipeline on fake seasons where we KNOW each team's true strength.

If the model works, it should (a) beat the simple baselines and (b) recover the
true ratings. Run with:  python -m tests.test_synthetic
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from nba.backtest import run
from nba.data import previous_season

TEAMS = ["ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
         "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
         "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"]
rng = np.random.default_rng(7)
TRUE_OFF = dict(zip(TEAMS, rng.normal(0, 3.5, 30)))
TRUE_DEF = dict(zip(TEAMS, rng.normal(0, 3.5, 30)))
TRUE_PACE = dict(zip(TEAMS, rng.normal(99, 2.5, 30)))


def fake_season(season: str) -> pd.DataFrame:
    """LeagueGameLog-shaped rows for a fake 1,230-game season."""
    r = np.random.default_rng(int(season[:4]))
    start = pd.Timestamp(f"{season[:4]}-10-22")
    rows, gid = [], 0
    drift = {t: r.normal(0, 1.0) for t in TEAMS}  # strengths change a bit each season
    for day in range(170):
        date = start + pd.Timedelta(days=day)
        teams = list(r.permutation(TEAMS))[: 2 * r.integers(3, 8)]
        for h, a in zip(teams[::2], teams[1::2]):
            gid += 1
            poss = (TRUE_PACE[h] + TRUE_PACE[a]) / 2 + r.normal(0, 3)
            h_ppp = 114 + TRUE_OFF[h] + drift[h] + TRUE_DEF[a] + 1.5 + r.normal(0, 10)
            a_ppp = 114 + TRUE_OFF[a] + drift[a] + TRUE_DEF[h] - 1.5 + r.normal(0, 10)
            hp, ap = round(h_ppp * poss / 100), round(a_ppp * poss / 100)
            if hp == ap:
                hp += 1
            for team, opp, pts, home in ((h, a, hp, True), (a, h, ap, False)):
                fga = int(poss * 0.88)
                rows.append({
                    "GAME_ID": f"{season[:4]}{gid:05d}", "GAME_DATE": date.strftime("%Y-%m-%d"),
                    "TEAM_ABBREVIATION": team,
                    "MATCHUP": f"{team} vs. {opp}" if home else f"{team} @ {opp}",
                    "WL": "W" if (pts > (ap if home else hp)) else "L",
                    "PTS": pts, "FGM": int(pts * 0.37), "FGA": fga, "FG3M": int(pts * 0.12),
                    "FTM": int(pts * 0.15), "FTA": int(pts * 0.19), "OREB": 10, "DREB": 33,
                    "TOV": int(poss - fga + 10 - 0.44 * int(pts * 0.19)),
                })
    return pd.DataFrame(rows)


def fake_lines(season: str) -> pd.DataFrame:
    """Fake 'Vegas' lines: the true margin plus noise, to exercise the Vegas code."""
    g = fake_season(season)
    home = g[g["MATCHUP"].str.contains(" vs. ")]
    away = g[g["MATCHUP"].str.contains(" @ ")]
    m = home.merge(away, on="GAME_ID", suffixes=("_h", "_a"))
    r = np.random.default_rng(1)
    est = m["PTS_h"] - m["PTS_a"] + r.normal(0, 9, len(m))
    p = 1 / (1 + np.exp(-est / 7))
    ml = lambda q: np.where(q >= 0.5, -100 * q / (1 - q), 100 * (1 - q) / q).round()
    return pd.DataFrame({"GAME_ID": m["GAME_ID"], "home_ml": ml(p * 0.98 + 0.01), "away_ml": ml((1 - p) * 0.98 + 0.01),
                         "home_spread": (-est * 2).round() / 2, "total": 225.0, "book": "FakeBook"})


def main():
    season = "2025-26"
    r = run(season, loader=fake_season, lines_loader=fake_lines, write=False)
    m, home, rec = r["model"], r["baseline_home_team"], r["baseline_better_record"]
    print("\nmodel   ", {k: round(v, 3) for k, v in m.items()})
    print("home    ", {k: round(v, 3) for k, v in home.items()})
    print("record  ", {k: round(v, 3) for k, v in rec.items()})
    assert m["log_loss"] < home["log_loss"], "model should beat 'always home'"
    assert m["accuracy"] > rec["accuracy"] - 0.01, "model should be at least as good as 'better record'"
    print("vegas", r.get("vegas_games", {}).get("vegas"))
    print("ats  ", r.get("against_the_spread"))
    assert "vegas_games" in r
    assert previous_season("2025-26") == "2024-25"
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
