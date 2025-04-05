import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import statsapi

load_dotenv()
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
TEAMS_FILE = "teams.json"
LOG_FILE = "on_deck_log.json"

def load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_log(log):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

def get_all_fantasy_hitters():
    with open(TEAMS_FILE, "r") as f:
        teams = json.load(f)

    hitters = set()
    for team in teams:
        for player in team["players"]:
            position = str(player.get("position", ""))  # Safely convert to string
            if (
                player.get("status") == "starter"
                and not position.startswith("SP")
                and not position.startswith("RP")
            ):
                hitters.add(player["name"])
    return list(hitters)

def get_live_game_ids():
    games = statsapi.schedule(date=datetime.today().strftime('%Y-%m-%d'))

    print("📅 Games pulled from schedule():")
    for g in games:
        away = g["away_name"]
        home = g["home_name"]
        status = g["status"]
        print(f"  → {away} @ {home} – Status: {status}")

    live_game_ids = [g["game_id"] for g in games if g.get("status") == "In Progress"]
    print(f"🎯 Live game IDs: {live_game_ids}")
    return live_game_ids

def get_on_deck_players():
    on_deck = []

    for game_id in get_live_game_ids():
        try:
            url = f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live"
            res = requests.get(url)
            data = res.json()

            offense = data.get("liveData", {}).get("linescore", {}).get("offense", {})
            current_batter = offense.get("batter", {}).get("fullName")
            team_id = offense.get("team", {}).get("id")

            if not current_batter or not team_id:
                continue

            box = data.get("liveData", {}).get("boxscore", {})
            on_deck_name = None

            for side in box.get("teams", {}).values():
                if side["team"]["id"] == team_id:
                    batters = []
                    for pid, pinfo in side["players"].items():
                        if "battingOrder" in pinfo:
                            batters.append({
                                "order": int(pinfo["battingOrder"]),
                                "name": pinfo["person"]["fullName"]
                            })

                    batters = sorted(batters, key=lambda x: x["order"])
                    current_idx = next((i for i, b in enumerate(batters) if b["name"] == current_batter), None)

                    if current_idx is not None:
                        next_idx = (current_idx + 1) % len(batters)
                        on_deck_name = batters[next_idx]["name"]

            if on_deck_name:
                on_deck.append(on_deck_name)

        except Exception as e:
            print(f"⚠️ Error in game {game_id}: {e}")
            continue

    return on_deck

def send_discord_alert(players):
    if not players:
        return
    names = "\n".join(f"• **{name}** is on deck!" for name in players)
    timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    message = f"🧢 **Fantasy On-Deck Alert** – {timestamp}\n{names}"
    requests.post(DISCORD_WEBHOOK_URL, json={"content": message})

def main():
    all_hitters = get_all_fantasy_hitters()
    print(f"🧢 Loaded {len(all_hitters)} fantasy hitters")

    on_deck_players = get_on_deck_players()
    print(f"⚾ On-deck players: {on_deck_players}")

    log = load_log()
    now = datetime.utcnow()
    cooldown = timedelta(minutes=2)  # ALERT AGAIN after 2 minutes

    new_alerts = []

    for name in on_deck_players:
        if name in all_hitters:
            last_alert_time = log.get(name)
            if not last_alert_time:
                new_alerts.append(name)
            else:
                last_dt = datetime.fromisoformat(last_alert_time)
                if now - last_dt > cooldown:
                    new_alerts.append(name)

    print(f"🚨 New alerts to send: {new_alerts}")

    if new_alerts:
        send_discord_alert(new_alerts)
        for name in new_alerts:
            log[name] = now.isoformat()
        save_log(log)

if __name__ == "__main__":
    main()
