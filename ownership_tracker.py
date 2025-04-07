import json
import os
from datetime import date

def compare_snapshots(yesterday_file, today_file, log_file='ownership_log.json'):
    with open(yesterday_file) as f:
        teams_yesterday = json.load(f)
    with open(today_file) as f:
        teams_today = json.load(f)

    today_str = str(date.today())
    ownership_log = {}

    # Load existing log
    if os.path.exists(log_file):
        with open(log_file) as f:
            ownership_log = json.load(f)

    if today_str not in ownership_log:
        ownership_log[today_str] = {}

    new_changes = 0

    for team_name, today_data in teams_today.items():
        yesterday_data = teams_yesterday.get(team_name, {})
        today_players = {p['name'] for p in today_data.get("starters", []) + today_data.get("bench", [])}
        yesterday_players = {p['name'] for p in yesterday_data.get("starters", []) + yesterday_data.get("bench", [])}

        added = sorted(list(today_players - yesterday_players))
        dropped = sorted(list(yesterday_players - today_players))

        if added or dropped:
            ownership_log[today_str][team_name] = {
                "added": added,
                "dropped": dropped
            }
            new_changes += 1
            print(f"🔁 {team_name}: +{len(added)} added, -{len(dropped)} dropped")

    with open(log_file, "w") as f:
        json.dump(ownership_log, f, indent=2)

    print(f"\n✅ ownership_log.json updated for {today_str} with {new_changes} teams having changes.")

if __name__ == "__main__":
    compare_snapshots("teams_2025-04-06.json", "teams_2025-04-07.json")
