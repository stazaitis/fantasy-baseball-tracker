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
    "x-fantasy-filter": json.dumps({
        "transactions": {
            "filterType": {
                "value": ["ADD", "DROP"]
            },
            "limit": 1000,
            "sortParam": "EXECUTION_DATE",
            "sortDir": "descending"
        }
    }),
    "Cookie": f"espn_s2={ESPN_S2}; SWID={SWID};"
}

def fetch_transaction_log():
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/seasons/2025/segments/0/leagues/{LEAGUE_ID}?view=mTransactions"
    res = requests.get(url, headers=HEADERS)

    try:
        data = res.json()
    except Exception as e:
        print("❌ Error parsing response JSON:", e)
        print("Response text:", res.text[:300])
        return []

    txns = data.get("transactions", [])
    if not txns:
        print("❌ No transactions found in mTransactions view.")
        return []

    return txns

def load_log():
    if os.path.exists("ownership_log.json"):
        with open("ownership_log.json", "r") as f:
            return json.load(f)
    return []

def save_log(log):
    with open("ownership_log.json", "w") as f:
        json.dump(log, f, indent=2)

def main():
    print("🔄 Fetching ESPN transactions...")
    txns = fetch_transaction_log()
    log = load_log()
    added = 0

    for txn in txns:
        if txn["type"] not in ["ADD", "DROP"]:
            continue

        for item in txn.get("items", []):
            player = item.get("player")
            if not player:
                continue

            team_id = item.get("toTeamId") if txn["type"] == "ADD" else item.get("fromTeamId")
            timestamp = txn.get("executionDate")
            dt = datetime.fromtimestamp(timestamp / 1000).isoformat()

            log_entry = {
                "player": player.get("fullName"),
                "teamId": team_id,
                "type": txn["type"],
                "timestamp": dt
            }

            if log_entry not in log:
                log.append(log_entry)
                added += 1
                print(f"✅ {txn['type']}: {log_entry['player']} at {dt}")

    save_log(log)
    print(f"✅ ownership_log.json updated with {added} new entries ({len(log)} total).")

if __name__ == "__main__":
    main()
