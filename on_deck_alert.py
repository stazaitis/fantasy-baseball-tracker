import os
import json
import requests
from datetime import datetime
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
            position = str(player.get("position", ""))
            if (
                player.get("status") == "starter"
                and not position.startswith("SP")
                and not position.startswith("RP")
            ):
                hitters.add(player["name"])
    return list(hitters)

def get_live_game_ids():
    games = statsapi.schedule(date=datetime.today().strftime('%Y-%m-%d'))
    return [g["game_id"] for g in games if g.get("status") == "In Progress"]

def get_on_deck_players_with_context():
    players = []

    for game_id in get_live_game_ids():
        try:
            url = f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live"
            res = requests.get(url)
            data = res.json()

            offense = data.get("liveData", {}).get("linescore", {}).get("offense", {})
            current_batter = offense.get("batter", {}).get("fullName")
            team_id = offense.get("team", {}).get("id")
            inning = data["liveData"]["linescore"]["currentInning"]
            half = data["liveData"]["linescore"]["inningHalf"][0]  # "Top" or "Bottom" → T or B
            outs = data["liveData"]["outs"]

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
                context_id = f"{game_id}-{half}{inning}-O{outs}"
                players.append((on_deck_name, context_id))

        except Exception as e:
            print(f"⚠️ Error processing game {game_id}: {e}")
            continue

    return players

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

    log = load_log()
    now_on_deck = get_on_deck_players_with_context()

    new_alerts = []
    for name, context in now_on_deck:
        if name in all_hitters:
            if log.get(name) != context:
                new_alerts.append(name)
                log[name] = context  # Update log with new game state
