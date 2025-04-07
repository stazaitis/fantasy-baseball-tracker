import requests
from datetime import datetime, timedelta
import pytz

# Path to your GitHub Action workflow file
WORKFLOW_PATH = ".github/workflows/daily-roster-sync.yml"

def get_first_game_time_utc():
    today = datetime.utcnow().date()
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today.isoformat()}"
    res = requests.get(url).json()

    try:
        games = res["dates"][0]["games"]
        start_times = [
            datetime.fromisoformat(g["gameDate"].replace("Z", "+00:00"))
            for g in games
        ]
        first_game = min(start_times)
        return first_game - timedelta(minutes=1)
    except (KeyError, IndexError, ValueError):
        print("⚠️ No games found today or invalid data.")
        return None

def datetime_to_cron(dt):
    return f"{dt.minute} {dt.hour} * * *"

def update_cron_schedule(cron_expr):
    with open(WORKFLOW_PATH, "r") as f:
        lines = f.readlines()

    with open(WORKFLOW_PATH, "w") as f:
        for line in lines:
            if line.strip().startswith("- cron:"):
                f.write(f"    - cron: \"{cron_expr}\"\n")
            else:
                f.write(line)

if __name__ == "__main__":
    game_time = get_first_game_time_utc()
    if game_time:
        cron_string = datetime_to_cron(game_time)
        print(f"✅ First MLB game (UTC): {game_time}")
        print(f"🔄 Updating workflow to run at: {cron_string}")
        update_cron_schedule(cron_string)
    else:
        print("❌ No game time found. Workflow not updated.")
