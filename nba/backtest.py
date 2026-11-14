"""Walk-forward backtest: replay a past season one day at a time.

For each game day, the model is fit only on games played before that day, then
predicts that day's games. That mimics using it live, with no peeking.

Settings (how fast old games fade, how hard ratings are pulled toward average)
are chosen on the season BEFORE the test season, then frozen. The test season
is never used to pick settings, so its score is an honest out-of-sample result.

Usage:
    python -m nba.backtest --season 2025-26
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from .data import previous_season
from .espn import load_lines, load_season
from .features import build_games
from .metrics import calibration, score
from .model import ModelParams, RatingsModel

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
PROCESSED = ROOT / "data" / "processed"


def season_games(season: str, loader=load_season) -> pd.DataFrame:
    return build_games(loader(season), season)


def walk_forward(all_games: pd.DataFrame, season: str, params: ModelParams) -> pd.DataFrame:
    target = all_games[all_games["season"] == season]
    season_start = target["date"].min()
    preds = []
    for day, todays in target.groupby("date"):
        model = RatingsModel(params).fit(all_games, as_of=day, season_start=season_start)
        for g in todays.itertuples():
            p = model.predict(g.home, g.away, g.home_rest, g.away_rest)
            preds.append({"game_id": g.game_id, "date": day, **p})
    out = target.merge(pd.DataFrame(preds).drop(columns=["home", "away"]), on=["game_id", "date"])
    return out


def add_baselines(preds: pd.DataFrame) -> pd.DataFrame:
    """Simple rules the model has to beat."""
    df = preds.copy()
    df["base_home_prob"] = 0.6   # "always pick the home team"
    # "pick the team with the better record so far" (home team on ties)
    # records only use games before each date
    wins, games_played = {}, {}
    rec = []
    for day, todays in df.sort_values("date").groupby("date"):
        for g in todays.itertuples():
            ph = wins.get(g.home, 0) / games_played[g.home] if games_played.get(g.home) else 0.5
            pa = wins.get(g.away, 0) / games_played[g.away] if games_played.get(g.away) else 0.5
            rec.append((g.game_id, 0.65 if ph >= pa else 0.35))
        for g in todays.itertuples():
            for t, won in ((g.home, g.home_win), (g.away, 1 - g.home_win)):
                wins[t] = wins.get(t, 0) + won
                games_played[t] = games_played.get(t, 0) + 1
    df = df.merge(pd.DataFrame(rec, columns=["game_id", "record_home_prob"]), on="game_id")
    return df


def _implied(ml):
    if ml is None or pd.isna(ml):
        return np.nan
    return 100 / (ml + 100) if ml > 0 else -ml / (-ml + 100)


def add_vegas(preds: pd.DataFrame, lines: pd.DataFrame) -> pd.DataFrame:
    """Attach the betting line; convert moneylines to a no-vig home win chance."""
    df = preds.copy()
    if lines is None or lines.empty:
        df["vegas_home_prob"] = np.nan
        df["home_spread"] = np.nan
        df["book"] = None
        return df
    ln = lines.rename(columns={"GAME_ID": "game_id"})[["game_id", "home_ml", "away_ml", "home_spread", "total", "book"]]
    ln["game_id"] = ln["game_id"].astype(str)
    df["game_id"] = df["game_id"].astype(str)
    df = df.merge(ln, on="game_id", how="left")
    ph = df["home_ml"].map(_implied)
    pa = df["away_ml"].map(_implied)
    df["vegas_home_prob"] = ph / (ph + pa)
    return df


def ats(df: pd.DataFrame) -> dict:
    """Against the spread: when the model disagrees with Vegas, who's right?

    A bettor needs about 52.4% to break even at standard -110 pricing.
    """
    d = df[df["home_spread"].notna()].copy()
    d["model_edge"] = d["pred_margin"] + d["home_spread"]      # >0: model likes home vs the line
    d["home_cover"] = d["margin"] + d["home_spread"]
    d = d[d["home_cover"] != 0]                                  # drop pushes
    out = {}
    for label, cut in (("all_games", 0.0), ("edge_2_plus", 2.0), ("edge_4_plus", 4.0)):
        sub = d[d["model_edge"].abs() >= cut] if cut else d
        if len(sub):
            hit = ((sub["model_edge"] > 0) == (sub["home_cover"] > 0)).mean()
            out[label] = {"games": int(len(sub)), "hit_rate": float(hit)}
    return out


def tune(all_games: pd.DataFrame, season: str) -> tuple[ModelParams, pd.DataFrame]:
    """Pick settings with the best log loss on `season`; also measure sigma there."""
    grid = itertools.product([14, 30, 60, 120], [2.0, 5.0, 15.0], [0.25, 0.5])
    rows, best, best_ll = [], None, float("inf")
    for hl, ridge, prior_w in grid:
        params = ModelParams(half_life_days=hl, ridge=ridge, prior_season_weight=prior_w)
        preds = walk_forward(all_games, season, params)
        s = score(preds)
        rows.append({"half_life_days": hl, "ridge": ridge, "prior_season_weight": prior_w, **s})
        print(f"  half-life {hl:>3}d  ridge {ridge:>4}  prior {prior_w}:  "
              f"acc {s['accuracy']:.3f}  log loss {s['log_loss']:.4f}")
        if s["log_loss"] < best_ll:
            best_ll, best = s["log_loss"], (params, preds)
    params, preds = best
    params.sigma = float(np.sqrt(np.mean((preds["margin"] - preds["pred_margin"]) ** 2)))
    return params, pd.DataFrame(rows)


def run(season: str, loader=load_season, lines_loader=load_lines, write: bool = True) -> dict:
    tune_season = previous_season(season)
    seasons = [previous_season(tune_season), tune_season, season]
    all_games = pd.concat([season_games(s, loader) for s in seasons], ignore_index=True)

    print(f"\nStep 1: choosing settings on {tune_season} ...")
    # the tuning pass has to re-run once sigma is known, so tune first, then re-score
    params, grid = tune(all_games[all_games["season"].isin(seasons[:2])], tune_season)
    print(f"  chosen: half-life {params.half_life_days}d, ridge {params.ridge}, "
          f"prior-season weight {params.prior_season_weight}, sigma {params.sigma:.2f}")

    print(f"\nStep 2: testing on {season} (never seen during tuning) ...")
    preds = add_baselines(walk_forward(all_games[all_games["season"].isin(seasons[1:])], season, params))
    season_start = preds["date"].min()
    after_2wk = preds[preds["date"] >= season_start + pd.Timedelta(days=14)]

    results = {
        "season": season,
        "tuned_on": tune_season,
        "params": vars(params),
        "model": score(preds),
        "model_after_first_2_weeks": score(after_2wk),
        "baseline_home_team": score(preds, "base_home_prob"),
        "baseline_better_record": score(preds, "record_home_prob"),
    }
    preds = add_vegas(preds, lines_loader(season))
    with_line = preds[preds["vegas_home_prob"].notna()]
    if len(with_line) >= 50:
        results["vegas_games"] = {
            "model": score(with_line),
            "vegas": score(with_line, "vegas_home_prob"),
            "book": str(with_line["book"].dropna().iloc[0]) if with_line["book"].notna().any() else "",
        }
        results["against_the_spread"] = ats(preds)
    pacers = preds[(preds["home"] == "IND") | (preds["away"] == "IND")]
    if len(pacers):
        results["pacers_games"] = score(pacers)

    final_model = RatingsModel(params).fit(
        all_games[all_games["season"].isin(seasons[1:])],
        as_of=preds["date"].max() + pd.Timedelta(days=1), season_start=season_start)
    ratings = final_model.ratings_table()
    calib = calibration(preds)

    if write:
        REPORTS.mkdir(exist_ok=True)
        PROCESSED.mkdir(parents=True, exist_ok=True)
        preds.to_csv(PROCESSED / f"backtest_predictions_{season}.csv", index=False)
        ratings.to_csv(PROCESSED / f"end_of_season_ratings_{season}.csv", index=False)
        grid.to_csv(PROCESSED / f"tuning_grid_{tune_season}.csv", index=False)
        (REPORTS / f"backtest_{season}.json").write_text(json.dumps(results, indent=2, default=str))
        md = report_markdown(results, calib, ratings)
        (REPORTS / f"backtest_{season}.md").write_text(md)
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with open(summary_path, "a") as fh:
                fh.write(md)
        print(f"\nReport written to reports/backtest_{season}.md")
    return results


def _row(name: str, s: dict) -> str:
    mae = f"{s['margin_mae']:.1f}" if "margin_mae" in s else "—"
    return f"| {name} | {s['games']} | {s['accuracy']:.1%} | {s['brier']:.3f} | {s['log_loss']:.3f} | {mae} |"


def report_markdown(r: dict, calib: pd.DataFrame, ratings: pd.DataFrame) -> str:
    p = r["params"]
    lines = [
        f"# Backtest: {r['season']} regular season",
        "",
        f"Settings were chosen on {r['tuned_on']} and then frozen, so these are honest "
        "out-of-sample results. Each day the model only knew games played before that day.",
        "",
        "| Predictor | Games | Picked winner | Brier (lower is better) | Log loss (lower is better) | Avg miss on margin (pts) |",
        "|---|---|---|---|---|---|",
        _row("**Model**", r["model"]),
        _row("Model, after the first 2 weeks", r["model_after_first_2_weeks"]),
        _row("Always pick the home team", r["baseline_home_team"]),
        _row("Pick the better record", r["baseline_better_record"]),
    ]
    if "pacers_games" in r:
        lines.append(_row("Model, Pacers games only", r["pacers_games"]))
    if "vegas_games" in r:
        v = r["vegas_games"]
        lines += [
            "",
            f"## Model vs Vegas ({v['book']} lines, games where a line was available)",
            "",
            "| Predictor | Games | Picked winner | Brier | Log loss | Avg miss on margin (pts) |",
            "|---|---|---|---|---|---|",
            _row("**Model**", v["model"]),
            _row("Vegas (moneyline, vig removed)", v["vegas"]),
        ]
    if "against_the_spread" in r:
        names = {"all_games": "Every game", "edge_2_plus": "Model disagrees by 2+ pts",
                 "edge_4_plus": "Model disagrees by 4+ pts"}
        lines += [
            "",
            "## Against the spread",
            "",
            "If you had taken the model's side against the Vegas spread. "
            "Break-even at standard pricing is about 52.4%.",
            "",
            "| Games picked | Games | Model's side covered |",
            "|---|---|---|",
        ]
        for k, a in r["against_the_spread"].items():
            lines.append(f"| {names[k]} | {a['games']} | {a['hit_rate']:.1%} |")
    lines += [
        "",
        "## Calibration: are the percentages honest?",
        "",
        "| Favorite's predicted chance | Games | Predicted | Actually won |",
        "|---|---|---|---|",
    ]
    for c in calib.itertuples():
        if c.games:
            lines.append(f"| {c.bucket} | {c.games} | {c.predicted:.1%} | {c.actual:.1%} |")
    lines += [
        "",
        "## Settings chosen",
        "",
        f"- Recency half-life: {p['half_life_days']} days",
        f"- Shrink toward average (ridge): {p['ridge']}",
        f"- Weight on last season's games: {p['prior_season_weight']}",
        f"- Typical miss on a game's margin (sigma): {p['sigma']:.1f} pts",
        "",
        "## End-of-season adjusted ratings (points per 100 possessions)",
        "",
        "| Rank | Team | Off rating | Def rating | Net | Pace |",
        "|---|---|---|---|---|---|",
    ]
    for i, t in enumerate(ratings.itertuples(), 1):
        lines.append(f"| {i} | {t.team} | {t.ortg:.1f} | {t.drtg:.1f} | {t.net:+.1f} | {t.pace:.1f} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", default="2025-26")
    args = ap.parse_args()
    r = run(args.season)
    m, b = r["model"], r["baseline_better_record"]
    print(f"\nModel picked {m['accuracy']:.1%} of winners vs {b['accuracy']:.1%} for 'better record'.")


if __name__ == "__main__":
    main()
