# ownership_tracker.py

import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

LEAGUE_ID = 121956
SEASON = 2025
SWID = os.getenv("SWID")
ESPN_S2 = os.getenv("ESPN_S2")

HEADERS = {
    "x-fantasy-filter": "{}",
    "User-Agent": "Mozilla/5.0",
    "Cookie": f"swid={SWID}; espn_s2={ESPN_S2};"
}

def fetch_recent_activity():
    scoring_period_id = 11  # Change to current week manually if needed
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/seasons/{SEASON}/segments/0/leagues/{LEAGUE_ID}?view=mTransactions&scoringPeriodId={scoring_period_id}"

    res = requests.get(url, headers=HEADERS)

    try:
        data = res.json()
    except Exception:
        print("❌ Failed to parse JSON. Response:")
        print(res.text[:1000])
        return []

    if "transactions" not in data:
        print("❌ 'transactions' key not found. Response:")
        print(json.dumps(data, indent=2)[:1000])
        return []

    return data["transactions"]

def parse_transactions(transactions):
    log = {}

    for tx in transactions:
        date = datetime.fromtimestamp(tx["executionDate"] / 1000.0).strftime("%a %b %d\n%I:%M %p")
        for item in tx["items"]:
            player = item["player"]["fullName"]
            team_id = item["toTeamId"] if tx["type"] == "ADD" else item["fromTeamId"]
            team_name = f"{team_id_to_abbrev(team_id)} Roster"
            action = tx["type"].lower()

            key = f"{player}, {team_name}"
            log.setdefault(key, []).append({
                "action": action,
                "team": team_name,
                "date": date
            })

    return log

def team_id_to_abbrev(team_id):
    # Map team ID to abbrev manually or use actual team data if available
    team_map = {
        1: "ALTL", 2: "GRIF", 3: "CONR", 4: "WATf", 5: "McK", 6: "Ben",
        7: "Kuch", 8: "KBM", 9: "STAZ", 10: "MBT", 11: "NNT", 12: "HELP"
    }
    return team_map.get(team_id, f"Team{team_id}")

def main():
    print("🔄 Fetching recent ESPN activity...")
    tx = fetch_recent_activity()
    log = parse_transactions(tx)

    with open("ownership_log.json", "w") as f:
        json.dump(log, f, indent=2)

    print(f"✅ ownership_log.json updated with {len(log)} entries.")

if __name__ == "__main__":
    main()
