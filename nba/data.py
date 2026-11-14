"""Download and cache NBA team game logs from NBA.com (via the nba_api package).

One request per season returns every team's box score line for every game,
which is everything the team model needs. Results are cached in data/raw/ so
each season is only downloaded once (pass refresh=True for the current season).
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# NBA.com rejects requests that don't look like they come from a browser.
HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}


def fetch_team_logs(season: str, season_type: str = "Regular Season",
                    retries: int = 4, timeout: int = 60) -> pd.DataFrame:
    """Fetch every team-game row for one season, e.g. season='2025-26'."""
    from nba_api.stats.endpoints import leaguegamelog  # imported lazily

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = leaguegamelog.LeagueGameLog(
                season=season,
                season_type_all_star=season_type,
                player_or_team_abbreviation="T",
                headers=HEADERS,
                timeout=timeout,
            )
            df = resp.get_data_frames()[0]
            if df.empty:
                raise RuntimeError(f"NBA.com returned no games for {season}")
            return df
        except Exception as err:  # network hiccups are common; back off and retry
            last_err = err
            wait = 15 * (attempt + 1)
            print(f"  attempt {attempt + 1} failed for {season}: {err!r}; retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Could not download {season} after {retries} attempts") from last_err


def load_team_logs(season: str, refresh: bool = False) -> pd.DataFrame:
    """Return team game logs for a season, using the local cache when present."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"team_games_{season}.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path, dtype={"GAME_ID": str})
    print(f"Downloading {season} team game logs from NBA.com ...")
    df = fetch_team_logs(season)
    df.to_csv(path, index=False)
    print(f"  saved {len(df)} rows to {path.name}")
    return df


def previous_season(season: str) -> str:
    """'2025-26' -> '2024-25'"""
    start = int(season[:4]) - 1
    return f"{start}-{str(start + 1)[-2:]}"
