from datetime import datetime
import requests
import json

# ESPN credentials
ESPN_LEAGUE_ID = 121956
SWID = "{213A1465-139E-4467-BA14-65139EB467BF}"
ESPN_S2 = "AECRHvmlDE0YOe8SH9g0YHWl570aqzPKAsa1KRQHXy2lEnwRrKlc%2BjBOTq8C4tZS97UL3dKK8Q8XgfqqrJ8o%2BgdohO5boY82RE8KQC2yHYRQ186r52nDmWlrEsMGL4RwJFHoNO4uP%2BMde8q7JOqRt0ttUtnEgdjisvvnLjmqgjsh0gxyIs5C%2B3LkWNi9v4Vcr1BtRsVGJGguKCSNlcGv8ZCmnr57Hs50OUbUMf900H84vpg7o8OiV2blW20X5Rn37zJn3JrllDKPLyFJqu5H%2FycJRCD%2FVYdOVcFs3wA72CW5CQ%3D%3D"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "x-fantasy-filter": "{}",
    "Cookie": f"espn_s2={ESPN_S2}; SWID={SWID};"
}

def fetch_teams():
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/seasons/2025/segments/0/leagues/{ESPN_LEAGUE_ID}?view=mMatchup&view=mRoster&view=mTeam&view=mRosterSettings"
    res = requests.get(url, headers=HEADERS)

    try:
        data = res.json()
    except Exception as e:
        print("❌ Failed to parse ESPN API response")
        print("Status code:", res.status_code)
        print("Response text snippet:", res.text[:500])
        raise e

    teams = []
    for team in data["teams"]:
        location = team.get("location", "")
        nickname = team.get("nickname", "")
        abbrev = team.get("abbrev", "Unknown")
        team_name = f"{location} {nickname}".strip() or abbrev

        team_info = {
            "team_name": team_name,
            "owner": team["owners"] and team["owners"][0],
            "players": []
        }

        for player in team.get("roster", {}).get("entries", []):
            player_data = player["playerPoolEntry"]["player"]
            player_name = player_data["fullName"]
            position = player_data["defaultPositionId"]
            status = "starter" if player["lineupSlotId"] < 20 else "bench"

            acquired_timestamp = player.get("acquisitionDate")
            if acquired_timestamp:
                try:
                    acquired_date = datetime.fromtimestamp(acquired_timestamp / 1000).strftime("%Y-%m-%d")
                except:
                    acquired_date = None
            else:
                acquired_date = None

            team_info["players"].append({
                "name": player_name,
                "position": position,
                "status": status,
                "acquiredDate": acquired_date
            })

        teams.append(team_info)

    return teams

if __name__ == "__main__":
    teams = fetch_teams()
    with open("teams.json", "w") as f:
        json.dump(teams, f, indent=2)
    print("✅ teams.json updated from ESPN API")
