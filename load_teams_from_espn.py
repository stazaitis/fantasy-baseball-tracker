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

POSITION_MAP = {
    1: "C", 2: "1B", 3: "2B", 4: "3B", 5: "SS", 6: "MI", 7: "CI", 8: "OF",
    9: "RF", 10: "CF", 11: "LF", 12: "UTIL", 13: "SP", 14: "RP", 15: "P",
    16: "BE", 17: "IL", 18: "NA"
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
            "owner": team["owners"][0] if team.get("owners") else None,
            "players": []
        }

        roster_entries = team.get("roster", {}).get("entries", [])
        for player in roster_entries:
            player_data = player.get("playerPoolEntry", {}).get("player", {})
            if not player_data:
                continue  # skip if no player data

            player_id = player_data.get("id")
            player_name = player_data.get("fullName", "Unknown")
            position_id = player_data.get("defaultPositionId", 0)
            position = POSITION_MAP.get(position_id, str(position_id))
            lineup_slot = player.get("lineupSlotId", 99)
            status = "starter" if lineup_slot < 20 else "bench"

            acquired_timestamp = player.get("acquisitionDate")
            acquired_date = (
                datetime.fromtimestamp(acquired_timestamp / 1000).strftime("%Y-%m-%d")
                if acquired_timestamp else None
            )
            acquired_datetime = (
                datetime.fromtimestamp(acquired_timestamp / 1000).isoformat()
                if acquired_timestamp else None
            )

            player_entry = {
                "espn_id": player_id,
                "name": player_name,
                "position": position,
                "status": status
            }

            if acquired_date:
                player_entry["acquiredDate"] = acquired_date
            if acquired_datetime:
                player_entry["acquiredDateTime"] = acquired_datetime

            team_info["players"].append(player_entry)

        print(f"✅ {team_name}: {len(team_info['players'])} players loaded")
        teams.append(team_info)

    return teams

if __name__ == "__main__":
    teams = fetch_teams()
    with open("teams.json", "w") as f:
        json.dump(teams, f, indent=2)
    print("✅ teams.json successfully updated from ESPN")
