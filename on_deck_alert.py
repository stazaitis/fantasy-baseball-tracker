import requests
import datetime
import json

# Discord Webhook URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1357496918728773765/daACAYwsiKOIxdY8EGuYV8-zz93nwZmPedMSXzNJQXCJPMz6qD06pCN2-irjTgo_gpIE"

# Load fantasy team
with open("teams.json") as f:
    teams = json.load(f)

# Flatten all players
fantasy_hitters = set()
for team in teams:
    for p in team["players"]:
        if p["position"] not in ["C", "SP", "RP", "P"]:
            fantasy_hitters.add(p["name"].lower())

# Get current MLB on-deck batters
def get_on_deck():
    res = requests.get("https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date=" + str(datetime.date.today()))
    games = res.json().get("dates", [])[0].get("games", [])

    on_deck_players = []

    for game in games:
        game_id = game["gamePk"]
        live_data = requests.get(f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live").json()
        try:
            on_deck = live_data["liveData"]["plays"]["currentPlay"]["matchup"]["onDeck"]["fullName"]
            if on_deck.lower() in fantasy_hitters:
                on_deck_players.append(on_deck)
        except KeyError:
            continue

    return on_deck_players

# Send Discord alert
def send_discord_alert(players):
    if not players:
        return

    message = f"🔔 **Fantasy On-Deck Alert!**\n\nThe following fantasy hitters are on deck:\n"
    for p in players:
        message += f"- {p}\n"

    payload = {"content": message}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

if __name__ == "__main__":
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"📢 On-Deck Alerts – {now}")
    hitters_on_deck = get_on_deck()
    if hitters_on_deck:
        print("✅ Sending Discord alert...")
        send_discord_alert(hitters_on_deck)
    else:
        print("No fantasy hitters currently on deck.")
