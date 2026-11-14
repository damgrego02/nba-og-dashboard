"""Turn raw team game logs into one row per game with advanced stats.

Advanced stats used:
  possessions  = FGA - OREB + TOV + 0.44 * FTA   (averaged over both teams)
  offensive rating = points per 100 possessions
  Four Factors: eFG%, turnover %, offensive rebound %, free throw rate
  rest: days since each team's previous game (1 = back-to-back)
"""
from __future__ import annotations

import pandas as pd


def _possessions(df: pd.DataFrame) -> pd.Series:
    return df["FGA"] - df["OREB"] + df["TOV"] + 0.44 * df["FTA"]


def build_games(logs: pd.DataFrame, season: str) -> pd.DataFrame:
    """One row per game: home/away teams, scores, possessions, rest."""
    df = logs.copy()
    df["GAME_ID"] = df["GAME_ID"].astype(str)
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    df["is_home"] = df["MATCHUP"].str.contains(" vs. ", regex=False)
    df["poss"] = _possessions(df)

    # rest days per team (computed before splitting home/away)
    df = df.sort_values(["TEAM_ABBREVIATION", "GAME_DATE"])
    df["rest_days"] = df.groupby("TEAM_ABBREVIATION")["GAME_DATE"].diff().dt.days
    df["rest_days"] = df["rest_days"].fillna(7).clip(upper=7)

    keep = ["GAME_ID", "GAME_DATE", "TEAM_ABBREVIATION", "PTS", "FGM", "FGA", "FG3M",
            "FTM", "FTA", "OREB", "DREB", "TOV", "poss", "rest_days"]
    home = df[df["is_home"]][keep].add_prefix("h_")
    away = df[~df["is_home"]][keep].add_prefix("a_")
    g = home.merge(away, left_on="h_GAME_ID", right_on="a_GAME_ID", how="inner")

    games = pd.DataFrame({
        "game_id": g["h_GAME_ID"],
        "date": g["h_GAME_DATE"],
        "season": season,
        "home": g["h_TEAM_ABBREVIATION"],
        "away": g["a_TEAM_ABBREVIATION"],
        "home_pts": g["h_PTS"],
        "away_pts": g["a_PTS"],
        "poss": (g["h_poss"] + g["a_poss"]) / 2,
        "home_rest": g["h_rest_days"],
        "away_rest": g["a_rest_days"],
    })
    # keep the box score pieces for Four Factors
    for side, pre in (("home", "h_"), ("away", "a_")):
        for col in ["FGM", "FGA", "FG3M", "FTM", "FTA", "OREB", "DREB", "TOV"]:
            games[f"{side}_{col.lower()}"] = g[pre + col]
    games["margin"] = games["home_pts"] - games["away_pts"]
    games["home_win"] = (games["margin"] > 0).astype(int)
    return games.sort_values(["date", "game_id"]).reset_index(drop=True)


def four_factors(games: pd.DataFrame) -> pd.DataFrame:
    """Season-to-date Four Factors per team (offense and defense)."""
    rows = []
    for team in sorted(set(games["home"]) | set(games["away"])):
        for side, opp in (("home", "away"), ("away", "home")):
            sub = games[games[side] == team]
            if sub.empty:
                continue
            rows.append(pd.DataFrame({
                "team": team,
                "fgm": sub[f"{side}_fgm"], "fga": sub[f"{side}_fga"], "fg3m": sub[f"{side}_fg3m"],
                "fta": sub[f"{side}_fta"], "ftm": sub[f"{side}_ftm"], "oreb": sub[f"{side}_oreb"],
                "tov": sub[f"{side}_tov"], "opp_dreb": sub[f"{opp}_dreb"],
                "o_fgm": sub[f"{opp}_fgm"], "o_fga": sub[f"{opp}_fga"], "o_fg3m": sub[f"{opp}_fg3m"],
                "o_fta": sub[f"{opp}_fta"], "o_tov": sub[f"{opp}_tov"], "o_oreb": sub[f"{opp}_oreb"],
                "dreb": sub[f"{side}_dreb"], "poss": sub["poss"],
            }))
    t = pd.concat(rows).groupby("team").sum(numeric_only=True)
    out = pd.DataFrame(index=t.index)
    out["efg"] = (t.fgm + 0.5 * t.fg3m) / t.fga
    out["tov_pct"] = t.tov / t.poss
    out["oreb_pct"] = t.oreb / (t.oreb + t.opp_dreb)
    out["ft_rate"] = t.fta / t.fga
    out["opp_efg"] = (t.o_fgm + 0.5 * t.o_fg3m) / t.o_fga
    out["opp_tov_pct"] = t.o_tov / t.poss
    out["dreb_pct"] = t.dreb / (t.dreb + t.o_oreb)
    out["opp_ft_rate"] = t.o_fta / t.o_fga
    return out.round(4)
