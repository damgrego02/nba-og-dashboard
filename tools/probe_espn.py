"""Print the shape of ESPN's NBA data so the loader can be built against the real format."""
import json, requests
H = {"User-Agent": "Mozilla/5.0"}
base = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"

r = requests.get(f"{base}/scoreboard", params={"dates": "20260301"}, headers=H, timeout=30)
print("scoreboard status", r.status_code)
sb = r.json()
print("top keys", list(sb))
ev = sb["events"][0]
print("event keys", list(ev))
print("event id/date/season", ev.get("id"), ev.get("date"), ev.get("season"))
comp = ev["competitions"][0]
print("competition keys", list(comp))
c = comp["competitors"][0]
print("competitor keys", list(c))
print("team keys", list(c["team"]))
print("homeAway/score/winner/abbr", c.get("homeAway"), c.get("score"), c.get("winner"), c["team"].get("abbreviation"))
print("scoreboard stats:", [(s.get("name"), s.get("abbreviation"), s.get("displayValue")) for s in c.get("statistics", [])])

r = requests.get(f"{base}/scoreboard", params={"dates": "20260301-20260307", "limit": 500}, headers=H, timeout=30)
print("\nrange query status", r.status_code, "events:", len(r.json().get("events", [])))

r = requests.get(f"{base}/summary", params={"event": ev["id"]}, headers=H, timeout=30)
print("\nsummary status", r.status_code)
sm = r.json()
print("summary keys", list(sm))
bt = sm["boxscore"]["teams"][0]
print("boxscore team keys", list(bt))
print("boxscore stats:", json.dumps([(s.get("name"), s.get("label"), s.get("displayValue")) for s in bt["statistics"]]))

for d in ["20231024", "20241022", "20251021"]:
    r = requests.get(f"{base}/scoreboard", params={"dates": d}, headers=H, timeout=30)
    evs = r.json().get("events", [])
    print("opening night", d, r.status_code, len(evs), [e.get("shortName") for e in evs][:3])
