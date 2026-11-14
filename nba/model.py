"""Team ratings model: opponent-adjusted offense and defense, weighted toward recent games.

For every game we get two "scoring rows", one per offense:

    points per 100 possessions = league avg + offense(team) + defense(opponent)
                                 +/- half of home court
                                 + back-to-back effects

Solving all rows at once (weighted ridge regression) adjusts every team for the
quality of the opponents it has faced. Recent games count more (half-life in days),
and last season's games count a little at the start of a new season.

Predicted margin = (home expected pts per 100 - away expected pts per 100)
                   * expected possessions / 100
Win probability  = Normal CDF(predicted margin / sigma)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ModelParams:
    half_life_days: float = 30.0   # a game this many days old counts half as much
    ridge: float = 5.0             # pulls ratings toward average when data is thin
    prior_season_weight: float = 0.4
    sigma: float = 13.0            # spread of real margins around the prediction


def normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


class RatingsModel:
    def __init__(self, params: ModelParams | None = None):
        self.p = params or ModelParams()
        self.teams: list[str] = []
        self.off: dict[str, float] = {}
        self.dfn: dict[str, float] = {}
        self.pace: dict[str, float] = {}
        self.league_avg = 112.0
        self.hca = 0.0
        self.b2b_off = 0.0
        self.b2b_def = 0.0

    # ------------------------------------------------------------------ fit
    def fit(self, games: pd.DataFrame, as_of: pd.Timestamp, season_start: pd.Timestamp) -> "RatingsModel":
        """Fit using only games played before `as_of` (no peeking at the future)."""
        past = games[games["date"] < as_of]
        if past.empty:
            raise ValueError("no games before as_of")

        # age in days; the off-season is skipped so last season's final games
        # are treated as "just before" this season's opener
        cur = past["date"] >= season_start
        prior_end = past.loc[~cur, "date"].max() if (~cur).any() else season_start
        age = np.where(
            cur,
            (as_of - past["date"]).dt.days,
            (as_of - season_start).days + (prior_end - past["date"]).dt.days + 1,
        ).astype(float)
        w = 0.5 ** (age / self.p.half_life_days)
        w = np.where(cur, w, w * self.p.prior_season_weight)

        teams = sorted(set(past["home"]) | set(past["away"]))
        idx = {t: i for i, t in enumerate(teams)}
        n = len(teams)
        # columns: [intercept, off_0..off_n-1, def_0..def_n-1, hca, b2b_off, b2b_def]
        k = 1 + 2 * n + 3
        m = len(past)
        X = np.zeros((2 * m, k))
        y = np.zeros(2 * m)
        W = np.concatenate([w, w])

        hi = past["home"].map(idx).to_numpy()
        ai = past["away"].map(idx).to_numpy()
        poss = past["poss"].to_numpy()
        h_b2b = (past["home_rest"].to_numpy() <= 1).astype(float)
        a_b2b = (past["away_rest"].to_numpy() <= 1).astype(float)
        r = np.arange(m)

        # home offense rows
        X[r, 0] = 1
        X[r, 1 + hi] = 1
        X[r, 1 + n + ai] = 1
        X[r, 1 + 2 * n] = 0.5
        X[r, 2 + 2 * n] = h_b2b
        X[r, 3 + 2 * n] = a_b2b
        y[r] = past["home_pts"].to_numpy() / poss * 100
        # away offense rows
        r2 = r + m
        X[r2, 0] = 1
        X[r2, 1 + ai] = 1
        X[r2, 1 + n + hi] = 1
        X[r2, 1 + 2 * n] = -0.5
        X[r2, 2 + 2 * n] = a_b2b
        X[r2, 3 + 2 * n] = h_b2b
        y[r2] = past["away_pts"].to_numpy() / poss * 100

        penalty = np.zeros(k)
        penalty[1:1 + 2 * n] = self.p.ridge          # shrink team ratings only
        XtW = X.T * W
        beta = np.linalg.solve(XtW @ X + np.diag(penalty), XtW @ y)

        self.teams = teams
        self.league_avg = beta[0]
        self.off = {t: beta[1 + i] for t, i in idx.items()}
        self.dfn = {t: beta[1 + n + i] for t, i in idx.items()}
        self.hca = beta[1 + 2 * n]
        self.b2b_off = beta[2 + 2 * n]
        self.b2b_def = beta[3 + 2 * n]

        # recency-weighted pace per team
        pace_rows = pd.DataFrame({
            "team": np.concatenate([past["home"], past["away"]]),
            "poss": np.concatenate([poss, poss]),
            "w": W,
        })
        pace_rows["wp"] = pace_rows["poss"] * pace_rows["w"]
        agg = pace_rows.groupby("team")[["wp", "w"]].sum()
        self.pace = (agg["wp"] / agg["w"]).to_dict()
        return self

    # -------------------------------------------------------------- predict
    def predict(self, home: str, away: str, home_rest: float = 2, away_rest: float = 2) -> dict:
        avg_off = float(np.mean(list(self.off.values()))) if self.off else 0.0
        o = lambda t: self.off.get(t, avg_off)
        d = lambda t: self.dfn.get(t, 0.0)
        h_b2b, a_b2b = float(home_rest <= 1), float(away_rest <= 1)

        home_ppp = self.league_avg + o(home) + d(away) + self.hca / 2 + self.b2b_off * h_b2b + self.b2b_def * a_b2b
        away_ppp = self.league_avg + o(away) + d(home) - self.hca / 2 + self.b2b_off * a_b2b + self.b2b_def * h_b2b
        lg_pace = float(np.mean(list(self.pace.values()))) if self.pace else 100.0
        poss = (self.pace.get(home, lg_pace) + self.pace.get(away, lg_pace)) / 2
        margin = (home_ppp - away_ppp) * poss / 100
        return {
            "home": home,
            "away": away,
            "pred_margin": round(margin, 2),
            "pred_home_pts": round(home_ppp * poss / 100, 1),
            "pred_away_pts": round(away_ppp * poss / 100, 1),
            "pred_poss": round(poss, 1),
            "home_win_prob": round(normal_cdf(margin / self.p.sigma), 4),
        }

    def ratings_table(self) -> pd.DataFrame:
        """Adjusted offensive / defensive / net rating per team (points per 100)."""
        t = pd.DataFrame({
            "team": self.teams,
            "ortg": [self.league_avg + self.off[x] for x in self.teams],
            "drtg": [self.league_avg + self.dfn[x] for x in self.teams],
            "pace": [self.pace.get(x, np.nan) for x in self.teams],
        })
        t["net"] = t["ortg"] - t["drtg"]
        return t.sort_values("net", ascending=False).round(2).reset_index(drop=True)
