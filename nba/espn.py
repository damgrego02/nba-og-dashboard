"""Download NBA box scores and betting lines from ESPN's public site API.

NBA.com blocks cloud servers (including GitHub's), so this is the main source.
  - scoreboard?dates=YYYYMMDD : every game that day with final scores
  - summary?event=<id>        : full team box score + DraftKings lines (pickcenter)

Output matches the NBA.com team game log columns, so the rest of the code
doesn't care which source the data came from. Lines are saved separately.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests

from .features import NBA_TEAMS

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# ESPN abbreviation -> NBA.com abbreviation
ABBR = {"GS": "GSW", "NY": "NYK", "SA": "SAS", "NO": "NOP", "UTAH": "UTA", "WSH": "WAS"}


def nba_abbr(espn: str) -> str:
    return ABBR.get(espn, espn)


def _get(path: str, params: dict, retries: int = 4) -> dict:
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(f"{BASE}/{path}", params=params, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.json()
            last = RuntimeError(f"HTTP {r.status_code}")
        except requests.RequestException as err:
            last = err
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"ESPN {path} {params} failed") from last


# ----------------------------------------------------------------- parsing
def parse_scoreboard(sb: dict, date: str) -> list[dict]:
    """Completed, non-neutral regular-season games on one date."""
    games = []
    for ev in sb.get("events", []):
        if ev.get("season", {}).get("type") != 2:          # 2 = regular season
            continue
        comp = ev["competitions"][0]
        if not comp.get("status", ev.get("status", {})).get("type", {}).get("completed"):
            continue
        if comp.get("neutralSite"):                          # no true home team
            continue
        teams = {c["homeAway"]: nba_abbr(c["team"]["abbreviation"]) for c in comp["competitors"]}
        if not set(teams.values()) <= NBA_TEAMS:              # All-Star / exhibitions
            continue
        games.append({"event_id": ev["id"], "date": date, "home": teams["home"], "away": teams["away"]})
    return games


def _made_att(value: str) -> tuple[int, int]:
    made, att = value.split("-")
    return int(made), int(att)


def parse_summary(sm: dict, game: dict) -> tuple[list[dict], dict]:
    """Two team rows in NBA.com game-log format, plus the betting line."""
    stats = {}
    for t in sm["boxscore"]["teams"]:
        s = {x["name"]: x["displayValue"] for x in t["statistics"]}
        stats[t["homeAway"]] = s
    points = {c["homeAway"]: int(c["score"]) for c in sm["header"]["competitions"][0]["competitors"]}

    rows = []
    for side, opp in (("home", "away"), ("away", "home")):
        s = stats[side]
        fgm, fga = _made_att(s["fieldGoalsMade-fieldGoalsAttempted"])
        fg3m, _ = _made_att(s["threePointFieldGoalsMade-threePointFieldGoalsAttempted"])
        ftm, fta = _made_att(s["freeThrowsMade-freeThrowsAttempted"])
        tov = s.get("totalTurnovers", s.get("turnovers", "0"))
        team, other = game[side], game[opp]
        rows.append({
            "GAME_ID": game["event_id"],
            "GAME_DATE": game["date"],
            "TEAM_ABBREVIATION": team,
            "MATCHUP": f"{team} vs. {other}" if side == "home" else f"{team} @ {other}",
            "WL": "W" if points[side] > points[opp] else "L",
            "PTS": points[side], "FGM": fgm, "FGA": fga, "FG3M": fg3m, "FTM": ftm, "FTA": fta,
            "OREB": int(s["offensiveRebounds"]), "DREB": int(s["defensiveRebounds"]), "TOV": int(tov),
        })

    line = {"GAME_ID": game["event_id"], "home_ml": None, "away_ml": None,
            "home_spread": None, "total": None, "book": None}
    for pc in sm.get("pickcenter") or []:
        line["book"] = pc.get("provider", {}).get("name")
        line["home_ml"] = (pc.get("homeTeamOdds") or {}).get("moneyLine")
        line["away_ml"] = (pc.get("awayTeamOdds") or {}).get("moneyLine")
        line["total"] = pc.get("overUnder")
        line["home_spread"] = parse_home_spread(pc.get("details"), game)
        break   # first (highest-priority) book only
    return rows, line


def parse_home_spread(details: str | None, game: dict) -> float | None:
    """'SA -1.5' with SA away -> home spread +1.5.  'EVEN' -> 0."""
    if not details:
        return None
    if details.strip().upper() in ("EVEN", "PK", "PICK"):
        return 0.0
    try:
        abbr, num = details.rsplit(" ", 1)
        num = float(num)
    except ValueError:
        return None
    fav = nba_abbr(abbr.strip())
    if fav == game["home"]:
        return num
    if fav == game["away"]:
        return -num
    return None


# ---------------------------------------------------------------- download
def season_dates(season: str) -> list[str]:
    start = int(season[:4])
    days = pd.date_range(f"{start}-10-01", f"{start + 1}-04-20", freq="D")
    today = pd.Timestamp.now(tz="US/Eastern").tz_localize(None).normalize()
    return [d.strftime("%Y%m%d") for d in days if d < today]


def fetch_season(season: str, workers: int = 8) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = season_dates(season)
    print(f"  scanning {len(dates)} days of {season} scoreboards ...")
    with ThreadPoolExecutor(workers) as pool:
        boards = list(pool.map(lambda d: (d, _get("scoreboard", {"dates": d})), dates))
    games = [g for d, sb in boards for g in parse_scoreboard(sb, f"{d[:4]}-{d[4:6]}-{d[6:]}")]
    print(f"  found {len(games)} games; downloading box scores ...")

    def one(game):
        try:
            return parse_summary(_get("summary", {"event": game["event_id"]}), game)
        except Exception as err:       # skip a broken game rather than the season
            print(f"    skipped {game['away']} @ {game['home']} {game['date']}: {err}")
            return [], None

    with ThreadPoolExecutor(workers) as pool:
        results = list(pool.map(one, games))
    rows = [r for rs, _ in results for r in rs]
    lines = [ln for _, ln in results if ln]
    return pd.DataFrame(rows), pd.DataFrame(lines)


def load_season(season: str, refresh: bool = False) -> pd.DataFrame:
    """Team game logs for a season (cached in data/raw)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    logs_path = RAW_DIR / f"espn_team_games_{season}.csv"
    lines_path = RAW_DIR / f"espn_lines_{season}.csv"
    if logs_path.exists() and not refresh:
        return pd.read_csv(logs_path, dtype={"GAME_ID": str})
    print(f"Downloading {season} from ESPN ...")
    logs, lines = fetch_season(season)
    if logs.empty:
        raise RuntimeError(f"ESPN returned no games for {season}")
    logs.to_csv(logs_path, index=False)
    lines.to_csv(lines_path, index=False)
    print(f"  saved {len(logs) // 2} games and {lines['home_ml'].notna().sum() if len(lines) else 0} betting lines")
    return logs


def load_lines(season: str) -> pd.DataFrame:
    path = RAW_DIR / f"espn_lines_{season}.csv"
    if not path.exists():
        return pd.DataFrame(columns=["GAME_ID", "home_ml", "away_ml", "home_spread", "total", "book"])
    return pd.read_csv(path, dtype={"GAME_ID": str})
