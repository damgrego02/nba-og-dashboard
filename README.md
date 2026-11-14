# NBA Dashboard

A pregame NBA prediction system built like a valuation model:

1. **Base model (the fundamentals):** opponent-adjusted offensive and defensive ratings, pace, rest, and home court, weighted toward recent games.
2. **Your takes (the assumptions):** plain-language eye-test analysis that adjusts the model. *(coming next)*
3. **Vegas (the market):** the price to beat. *(coming next)*

A scorecard tracks whether the takes add an edge.

## What's here now

| Path | What it does |
|---|---|
| `nba/espn.py` | Downloads box scores and DraftKings lines from ESPN and caches them in `data/raw/` |
| `nba/data.py` | Backup source: NBA.com (blocks cloud servers, but works from a home connection) |
| `nba/features.py` | Builds one row per game with possessions, rest days, and the Four Factors |
| `nba/model.py` | The team ratings model |
| `nba/backtest.py` | Replays a past season day by day and grades the model |
| `tests/test_synthetic.py` | Checks the whole pipeline on fake seasons where the right answer is known |
| `tests/test_espn_parse.py` | Checks the ESPN reader against the real response format |

## Running the backtest

On GitHub: **Actions** tab → **Backtest** → **Run workflow**. Results are saved to `reports/backtest_<season>.md` and also shown on the run's summary page.

On your own computer (Python 3.10+):

```
pip install -r requirements.txt
python -m nba.backtest --season 2025-26
```
