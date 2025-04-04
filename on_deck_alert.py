import os
import requests
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Retrieve Discord webhook URL from the environment variable
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1357496918728773765/daACAYwsiKOIxdY8EGuYV8-zz93nwZmPedMSXzNJQXCJPMz6qD06pCN2-irjTgo_gpIE")

# List of Fantasy Hitters
FANTASY_HITTERS = [
    # Team 1 (Roster 1)
    "N Maton", "L Robert Jr.", "A Benintendi", "M Vargas", "M Thaiss", 
    "R Baldwin", "T Jankowski", "M Taylor", "J Amaya",
    
    # Team 2 (Roster 2)
    "Z McKinstry", "R Greene", "S Torkelson", "K Carpenter", "C Keith", 
    "J Malloy", "T Sweeney", "J Rogers", "R Kreidler"
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
