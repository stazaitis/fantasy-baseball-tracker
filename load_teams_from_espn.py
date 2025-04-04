import requests
import json

# Replace these with your actual values
ESPN_LEAGUE_ID = 121956
SWID = "{213A1465-139E-4467-BA14-65139EB467BF}"
ESPN_S2 = "AECRHvmlDE0YOe8SH9g0YHWl570aqzPKAsa1KRQHXy2lEnwRrKlc%2BjBOTq8C4tZS97UL3dKK8Q8XgfqqrJ8o%2BgdohO5boY82RE8KQC2yHYRQ186r52nDmWlrEsMGL4RwJFHoNO4uP%2BMde8q7JOqRt0ttUtnEgdjisvvnLjmqgjsh0gxyIs5C%2B3LkWNi9v4Vcr1BtRsVGJGguKCSNlcGv8ZCmnr57Hs50OUbUMf900H84vpg7o8OiV2blW20X5Rn37zJn3JrllDKPLyFJqu5H%2FycJRCD%2FVYdOVcFs3wA72CW5CQ%3D%3D"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "x-fantasy-filter": "{}",
    "Cookie": f"espn_s2={ESPN_S2}; SWID={SWID}"
}

def fetch_teams():
    url = f"https://fantasy.espn.com/apis/v3/games/flb/seasons/2025/segments/0/leagues/{ESPN_LEAGUE_ID}?view=mMatchup&view=mRoster&view=mTeam"
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
            player_name = player["playerPoolEntry"]["player"]["fullName"]
            position = player["playerPoolEntry"]["player"]["defaultPositionId"]
            status = "starter" if player["lineupSlotId"] < 20 else "bench"

            team_info["players"].append({
                "name": player_name,
                "position": position,
                "status": status
            })

        teams.append(team_info)

    return teams

if __name__ == "__main__":
    teams = fetch_teams()
    with open("teams.json", "w") as f:
        json.dump(teams, f, indent=2)
    print("✅ teams.json updated from ESPN API")
