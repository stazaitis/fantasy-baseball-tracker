import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1357496918728773765/daACAYwsiKOIxdY8EGuYV8-zz93nwZmPedMSXzNJQXCJPMz6qD06pCN2-irjTgo_gpIE")
FANTASY_HITTERS = [
    # Add your fantasy hitters here (update with full league if needed)
    "Aaron Judge", "Shohei Ohtani", "Mike Trout", "Juan Soto",
    "Rafael Devers", "Jose Altuve", "Luis Robert Jr.", "Corey Seager"
]

def get_on_deck_hitters():
    url = "https://statsapi.mlb.com/api/v1.1/game/feeds/ondeck"
    try:
        res = requests.get(url)
        if res.status_code != 200:
            return []
        data = res.json()
        return [entry.get("batter", {}).get("fullName", "") for entry in data if entry.get("batter")]
    except Exception:
        return []

def send_discord_alert(players):
    if not players:
        return  # Don't send anything if no hitters are on-deck

    names = "\n".join(f"• **{name}** is on deck!" for name in players)
    timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    message = f"🧢 **Fantasy On-Deck Alert** – {timestamp}\n{names}"

    requests.post(DISCORD_WEBHOOK_URL, json={"content": message})

def main():
    on_deck_hitters = get_on_deck_hitters()
    fantasy_on_deck = [name for name in on_deck_hitters if name in FANTASY_HITTERS]

    send_discord_alert(fantasy_on_deck)

if __name__ == "__main__":
    main()
