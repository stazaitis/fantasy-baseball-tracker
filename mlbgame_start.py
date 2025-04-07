import requests
from datetime import datetime, timedelta
import pytz
import subprocess

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
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    with open(WORKFLOW_PATH, "w", encoding="utf-8") as f:
        for line in lines:
            if line.strip().startswith("- cron:"):
                f.write(f"    - cron: \"{cron_expr}\"\n")
            else:
                f.write(line)

def git_commit_and_push():
    try:
        subprocess.run(["git", "config", "--global", "user.name", "cron-updater-bot"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "cron@fantasybot.com"], check=True)
        subprocess.run(["git", "add", WORKFLOW_PATH], check=True)
        subprocess.run(["git", "commit", "-m", "🔁 Update cron to match MLB schedule"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Cron update committed and pushed to GitHub.")
    except subprocess.CalledProcessError as e:
        print("❌ Git command failed:", e)

# === MAIN RUN ===
if __name__ == "__main__":
    game_time = get_first_game_time_utc()
    if game_time:
        cron_string = datetime_to_cron(game_time)
        print(f"✅ First MLB game (UTC): {game_time}")
        print(f"🔄 Updating workflow to run at: {cron_string}")
        update_cron_schedule(cron_string)
        git_commit_and_push()
    else:
        print("❌ No game time found. Workflow not updated.")

if __name__ == "__main__":
    game_time = get_first_game_time_utc()
    if game_time:
        cron_string = datetime_to_cron(game_time)
        print(f"✅ First MLB game (UTC): {game_time}")
        print(f"🔄 Updating workflow to run at: {cron_string}")
        update_cron_schedule(cron_string)
    else:
        print("❌ No game time found. Workflow not updated.")
