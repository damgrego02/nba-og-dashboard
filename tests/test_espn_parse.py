"""Checks the ESPN parser against JSON shaped like the real responses (captured Nov 2026)."""
from nba.espn import parse_home_spread, parse_scoreboard, parse_summary

SB = {"events": [{
    "id": "401810723", "date": "2026-03-01T18:00Z", "season": {"year": 2026, "type": 2},
    "status": {"type": {"completed": True}},
    "competitions": [{"neutralSite": False, "status": {"type": {"completed": True}}, "competitors": [
        {"homeAway": "home", "team": {"abbreviation": "NY"}, "score": "114"},
        {"homeAway": "away", "team": {"abbreviation": "SA"}, "score": "109"}]}]}]}

def stat(**kv):
    return [{"name": k.replace("__", "-"), "displayValue": v} for k, v in kv.items()]

SM = {
    "boxscore": {"teams": [
        {"homeAway": "home", "statistics": stat(**{"fieldGoalsMade__fieldGoalsAttempted": "43-97",
            "threePointFieldGoalsMade__threePointFieldGoalsAttempted": "17-48",
            "freeThrowsMade__freeThrowsAttempted": "11-19", "offensiveRebounds": "14",
            "defensiveRebounds": "40", "totalTurnovers": "12"})},
        {"homeAway": "away", "statistics": stat(**{"fieldGoalsMade__fieldGoalsAttempted": "40-88",
            "threePointFieldGoalsMade__threePointFieldGoalsAttempted": "12-35",
            "freeThrowsMade__freeThrowsAttempted": "17-22", "offensiveRebounds": "9",
            "defensiveRebounds": "38", "totalTurnovers": "15"})}]},
    "header": {"competitions": [{"competitors": [
        {"homeAway": "home", "score": "114"}, {"homeAway": "away", "score": "109"}]}]},
    "pickcenter": [{"provider": {"name": "DraftKings"}, "details": "SA -1.5", "overUnder": 227.5,
                    "spread": 1.5, "awayTeamOdds": {"moneyLine": -118}, "homeTeamOdds": {"moneyLine": -102}}],
}

def main():
    games = parse_scoreboard(SB, "2026-03-01")
    assert games == [{"event_id": "401810723", "date": "2026-03-01", "home": "NYK", "away": "SAS"}], games
    rows, line = parse_summary(SM, games[0])
    assert rows[0]["MATCHUP"] == "NYK vs. SAS" and rows[1]["MATCHUP"] == "SAS @ NYK"
    assert rows[0]["PTS"] == 114 and rows[0]["FGA"] == 97 and rows[0]["TOV"] == 12 and rows[1]["OREB"] == 9
    assert rows[0]["WL"] == "W" and rows[1]["WL"] == "L"
    assert line["home_spread"] == 1.5 and line["home_ml"] == -102 and line["book"] == "DraftKings"
    assert parse_home_spread("NY -6.5", games[0]) == -6.5
    assert parse_home_spread("EVEN", games[0]) == 0.0
    print("ESPN parser checks passed.")

if __name__ == "__main__":
    main()
