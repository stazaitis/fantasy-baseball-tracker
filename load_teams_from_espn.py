import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load secrets
load_dotenv()
LEAGUE_ID = 121956
SWID = os.getenv("SWID")
ESPN_S2 = os.getenv("ESPN_S2")

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
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/seasons/2025/segments/0/leagues/{LEAGUE_ID}?view=mMatchup&view=mRoster&view=mTeam&view=mRosterSettings"
    res = requests.get(url, headers=HEADERS)

    try:
        data = res.json()
    except Exception as e:
        print("❌ Failed to parse ESPN API response")
        print("Status code:", res.status_code)
        print("Response text snippet:", res.text[:500])
        raise e

    teams = {}
    for team in data.get("teams", []):
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
            try:
                player_data = player.get("playerPoolEntry", {}).get("player", {})
                if not player_data:
                    continue

                player_id = player_data.get("id")
                player_name = player_data.get("fullName", "Unknown")
                position_id = player_data.get("defaultPositionId", 0)
                position = POSITION_MAP.get(position_id, str(position_id))
                lineup_slot = player.get("lineupSlotId", 99)
                # ESPN slot IDs for starters — adjust to match your exact league setup if needed
                STARTER_SLOTS = list(range(0, 22))  # Slots 0–21 are all starters in your league
                status = "starter" if lineup_slot in STARTER_SLOTS else "bench"



                acquired_timestamp = player.get("acquisitionDate")
                acquired_datetime = datetime.fromtimestamp(acquired_timestamp / 1000).isoformat() if acquired_timestamp else None
                acquired_date = acquired_datetime.split("T")[0] if acquired_datetime else None

                dropped_timestamp = player.get("droppingDate")
                dropped_datetime = datetime.fromtimestamp(dropped_timestamp / 1000).isoformat() if dropped_timestamp else None
                dropped_date = dropped_datetime.split("T")[0] if dropped_datetime else None

                team_info["players"].append({
                    "espn_id": player_id,
                    "name": player_name,
                    "position": position,
                    "status": status,
                    "acquiredDate": acquired_date,
                    "acquiredDateTime": acquired_datetime,
                    "droppedDate": dropped_date,
                    "droppedDateTime": dropped_datetime
                })
            except Exception as e:
                print(f"⚠️ Error processing player for {team_name}: {e}")

        print(f"✅ {abbrev} ({team_name}): {len(team_info['players'])} players loaded")
        teams[abbrev] = team_info

    return teams

def save_teams_json(data):
    try:
        json_str = json.dumps(data, indent=2)
        with open("teams.json", "w") as f:
            f.write(json_str)
        print("✅ teams.json saved successfully")
    except Exception as e:
        print(f"❌ Failed to save teams.json: {e}")

if __name__ == "__main__":
    teams = fetch_teams()
    save_teams_json(teams)

    import sys
    if '--save-snapshot' in sys.argv:
        today_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"teams_{today_str}.json"
        try:
            with open(filename, "w") as f:
                json.dump(teams, f, indent=2)
            print(f"📸 Snapshot saved as {filename}")
        except Exception as e:
            print(f"❌ Failed to save snapshot {filename}: {e}")
