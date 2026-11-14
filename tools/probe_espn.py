"""Print the shape of ESPN's NBA odds data."""
import json, requests
H = {"User-Agent": "Mozilla/5.0"}
base = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
for d in ["20240115", "20260301"]:
    sb = requests.get(f"{base}/scoreboard", params={"dates": d}, headers=H, timeout=30).json()
    ev = sb["events"][0]
    print("\n====", d, ev["shortName"], "status:", json.dumps(ev["status"]["type"])[:300])
    print("competition odds on scoreboard:", json.dumps(ev["competitions"][0].get("odds"))[:1500])
    sm = requests.get(f"{base}/summary", params={"event": ev["id"]}, headers=H, timeout=30).json()
    print("pickcenter:", json.dumps(sm.get("pickcenter"))[:2500])
    print("header comp keys:", list(sm["header"]["competitions"][0]))
