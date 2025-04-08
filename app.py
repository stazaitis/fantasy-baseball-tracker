import os
import json
import requests
from datetime import datetime, date
from flask import Flask, jsonify, render_template, redirect
from waitress import serve
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

app = Flask(__name__)

# Matchup 3 (April 7 – April 13)
MATCHUP_START = date(2025, 4, 7)
MATCHUP_END = date(2025, 4, 13)

# Fantasy scoring rules
SCORING = {
    "H": 0.5, "R": 1, "TB": 1, "RBI": 1, "BB": 1, "SO": -1, "SB": 1,
    "OUTS": 1, "H_ALLOWED": -1, "ER": -2, "BB_ISSUED": -1, "K": 1,
    "QS": 3, "CG": 3, "NH": 7, "PG": 10, "W": 5, "L": -5, "SV": 5, "HD": 3
}

def get_first_game_start_datetime(game_date):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={game_date.isoformat()}"
    res = requests.get(url)
    try:
        games = res.json().get("dates", [])[0].get("games", [])
        if not games:
            return None
        start_times = [datetime.fromisoformat(game["gameDate"].replace("Z", "+00:00")) for game in games]
        return min(start_times) if start_times else None
    except:
        return None

def get_player_id(player_name):
    url = f"https://statsapi.mlb.com/api/v1/people/search?names={player_name}"
    try:
        res = requests.get(url).json()
        return res.get("people", [{}])[0].get("id")
    except:
        print(f"❌ Could not get ID for {player_name}")
        return None

def get_player_stats_for_range(player_name, acquired_datetime=None, dropped_datetime=None):
    player_id = get_player_id(player_name)
    if not player_id:
        return 0

    current_year = datetime.now().year
    group = "hitting" if "ohtani" in player_name.lower() else "all"
    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=gameLog&group={group}&season={current_year}"

    try:
        res = requests.get(url).json()
        game_logs = res.get("stats", [{}])[0].get("splits", [])
        total_points = 0

        for game in game_logs:
            try:
                game_date = datetime.strptime(game["date"], "%Y-%m-%d").date()
                if not (MATCHUP_START <= game_date <= MATCHUP_END):
                    continue

                first_game_start = get_first_game_start_datetime(game_date)
                if not first_game_start:
                    continue

                # Handle acquisition logic
                if acquired_datetime:
                    acquired_dt = datetime.fromisoformat(acquired_datetime).replace(tzinfo=first_game_start.tzinfo)
                    if acquired_dt >= first_game_start:
                        continue

                if dropped_datetime:
                    dropped_dt = datetime.fromisoformat(dropped_datetime).replace(tzinfo=first_game_start.tzinfo)
                    if dropped_dt <= first_game_start:
                        continue

                stat = game["stat"]
                pitching = "inningsPitched" in stat

                if pitching:
                    ip = stat.get("inningsPitched", "0.0")
                    outs = int(ip.split(".")[0]) * 3 + int(ip.split(".")[1]) if "." in ip else int(ip) * 3
                    earned_runs = stat.get("earnedRuns", 0)
                    if outs >= 18 and earned_runs <= 3:
                        total_points += SCORING["QS"]

                    total_points += (
                        outs * SCORING["OUTS"] +
                        stat.get("hits", 0) * SCORING["H_ALLOWED"] +
                        earned_runs * SCORING["ER"] +
                        stat.get("baseOnBalls", 0) * SCORING["BB_ISSUED"] +
                        stat.get("strikeOuts", 0) * SCORING["K"] +
                        stat.get("wins", 0) * SCORING["W"] +
                        stat.get("losses", 0) * SCORING["L"] +
                        stat.get("saves", 0) * SCORING["SV"] +
                        stat.get("holds", 0) * SCORING["HD"] +
                        stat.get("completeGames", 0) * SCORING["CG"] +
                        stat.get("noHitters", 0) * SCORING["NH"] +
                        stat.get("perfectGames", 0) * SCORING["PG"]
                    )
                else:
                    total_points += (
                        stat.get("hits", 0) * SCORING["H"] +
                        stat.get("runs", 0) * SCORING["R"] +
                        stat.get("totalBases", 0) * SCORING["TB"] +
                        stat.get("rbi", 0) * SCORING["RBI"] +
                        stat.get("baseOnBalls", 0) * SCORING["BB"] +
                        stat.get("strikeOuts", 0) * SCORING["SO"] +
                        stat.get("stolenBases", 0) * SCORING["SB"]
                    )
            except Exception as e:
                print(f"⚠️ Error processing {player_name}: {e}")

        return round(total_points, 1)
    except Exception as e:
        print(f"❌ Failed to fetch stats for {player_name}: {e}")
        return 0

@app.route("/")
def home():
    return redirect("/fantasy")

@app.route("/fantasy")
def fantasy_page():
    return render_template("fantasy.html")

@app.route("/api/live_points")
def live_points():
    try:
        with open("teams.json", "r") as f:
            teams_data = json.load(f)
    except Exception as e:
        return {"error": f"Failed to load teams.json: {str(e)}"}, 500

    results = []

    for team_id, team in teams_data.items():
        team_name = team.get("team_name", team_id)
        team_points = 0
        player_results = []

        for player in team.get("players", []):
            name = player.get("name")
            acquired = player.get("acquiredDateTime")
            dropped = player.get("droppedDateTime")
            points = get_player_stats_for_range(name, acquired, dropped)

            player_results.append({
                "name": name,
                "points": points
            })
            team_points += points

        results.append({
            "team": team_name,
            "total_points": round(team_points, 1),
            "players": player_results
        })

    return {"live_points": results}, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    serve(app, host="0.0.0.0", port=port)
