import os
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, redirect
import json
from datetime import datetime, date

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Position ID to name mapping
POSITION_MAP = {
    1: "P", 2: "C", 3: "1B", 4: "2B", 5: "3B", 6: "SS", 7: "LF",
    8: "CF", 9: "RF", 10: "DH", 11: "RP", 12: "SP"
}

# Custom fantasy scoring system
SCORING = {
    "H": 0.5, "R": 1, "TB": 1, "RBI": 1, "BB": 1, "SO": -1, "SB": 1,
    "OUTS": 1, "H_ALLOWED": -1, "ER": -2, "BB_ISSUED": -1, "K": 1,
    "QS": 3, "CG": 3, "NH": 7, "PG": 10, "W": 5, "L": -5, "SV": 5, "HD": 3
}

# Matchup 2 (March 31 – April 6)
MATCHUP_START = date(2025, 3, 31)
MATCHUP_END = date(2025, 4, 6)

def get_first_game_start_datetime(game_date):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={game_date.isoformat()}"
    res = requests.get(url)
    try:
        games = res.json().get("dates", [])[0].get("games", [])
        if not games:
            return None
        # Get the earliest game start time
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
        print(f"❌ Error getting ID for {player_name}")
        return None

def get_player_stats_for_range(player_name, acquired_datetime=None, dropped_datetime=None):
    player_id = get_player_id(player_name)
    if not player_id:
        print(f"⚠️ No ID found for {player_name}")
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

                if acquired_datetime and acquired_datetime.replace(tzinfo=first_game_start.tzinfo) >= first_game_start:
                    continue
                if dropped_datetime and dropped_datetime.replace(tzinfo=first_game_start.tzinfo) <= first_game_start:
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
                print(f"⚠️ Error processing game for {player_name}: {e}")

        return round(total_points, 1)

    except Exception as e:
        print(f"❌ Error fetching stats for {player_name}: {e}")
        return 0

@app.route("/")
def home():
    return redirect("/fantasy")

@app.route("/fantasy")
def fantasy_page():
    return render_template("fantasy.html")

@app.route("/search")
def search_page():
    return render_template("search.html")

@app.route("/api/live_points")
def live_points():
    with open("teams.json") as f:
        teams = json.load(f)

    results = []
    for team in teams:
        team_total = 0
        players_with_points = []

        for p in team["players"]:
            if p.get("status", "").lower() == "bench":
                continue

            acquired_str = p.get("acquiredDateTime")
            dropped_str = p.get("droppedDateTime")

            acquired_dt = None
            dropped_dt = None

            if acquired_str:
                try:
                    acquired_dt = datetime.fromisoformat(acquired_str.replace("Z", "+00:00"))
                except:
                    pass

            if dropped_str:
                try:
                    dropped_dt = datetime.fromisoformat(dropped_str.replace("Z", "+00:00"))
                except:
                    pass

            points = get_player_stats_for_range(p["name"], acquired_dt, dropped_dt)
            players_with_points.append({
                "name": p["name"],
                "position": POSITION_MAP.get(p["position"], p["position"]),
                "points": round(points, 1)
            })
            team_total += points

        results.append({
            "team_name": team["team_name"],
            "owner": team["owner"].get("displayName") if isinstance(team["owner"], dict) else team["owner"],
            "total": round(team_total, 1),
            "players": players_with_points
        })

    return jsonify(results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
