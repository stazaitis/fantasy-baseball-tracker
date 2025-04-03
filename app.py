from flask import Flask, jsonify, render_template, redirect
import json
import requests
from datetime import datetime, date

app = Flask(__name__)

# Custom fantasy scoring system
SCORING = {
    "H": 0.5,
    "R": 1,
    "TB": 1,
    "RBI": 1,
    "BB": 1,
    "SO": -1,
    "SB": 1,
    "OUTS": 1,
    "H_ALLOWED": -1,
    "ER": -2,
    "BB_ISSUED": -1,
    "K": 1,
    "QS": 3,
    "CG": 3,
    "NH": 7,
    "PG": 10,
    "W": 5,
    "L": -5,
    "SV": 5,
    "HD": 3,
}

# Matchup 2 (March 31 – April 6)
MATCHUP_START = date(2025, 3, 31)
MATCHUP_END = date(2025, 4, 6)

def get_player_id(player_name):
    try:
        url = f"https://statsapi.mlb.com/api/v1/people/search?names={player_name}"
        res = requests.get(url).json()
        people = res.get("people", [])
        return people[0]["id"] if people else None
    except Exception as e:
        print(f"[ERROR] Failed to get player ID for {player_name}: {e}")
        return None

def get_player_stats_for_range(player_name):
    player_id = get_player_id(player_name)
    if not player_id:
        print(f"⚠️ No ID found for {player_name}")
        return 0

    current_year = datetime.now().year
    group = "hitting" if "ohtani" in player_name.lower() else "all"

    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=gameLog&group={group}&season={current_year}"
        res = requests.get(url).json()

        stats_data = res.get("stats", [])
        if not stats_data or not isinstance(stats_data, list) or len(stats_data) == 0:
            print(f"⚠️ No game log data for {player_name}")
            return 0

        first_stat_block = stats_data[0]
        if not first_stat_block or "splits" not in first_stat_block:
            print(f"⚠️ No splits in stats for {player_name}")
            return 0

        game_logs = first_stat_block["splits"]

        total_points = 0

        for game in game_logs:
            game_date = datetime.strptime(game["date"], "%Y-%m-%d").date()
            if not (MATCHUP_START <= game_date <= MATCHUP_END):
                continue

            stat = game["stat"]
            pitching = "inningsPitched" in stat

            if pitching:
                ip = stat.get("inningsPitched", "0.0")
                if "." in ip:
                    parts = ip.split(".")
                    outs = int(parts[0]) * 3 + int(parts[1])
                else:
                    outs = int(ip) * 3

                total_points += (
                    outs * SCORING["OUTS"] +
                    stat.get("hits", 0) * SCORING["H_ALLOWED"] +
                    stat.get("earnedRuns", 0) * SCORING["ER"] +
                    stat.get("baseOnBalls", 0) * SCORING["BB_ISSUED"] +
                    stat.get("strikeOuts", 0) * SCORING["K"] +
                    stat.get("wins", 0) * SCORING["W"] +
                    stat.get("losses", 0) * SCORING["L"] +
                    stat.get("saves", 0) * SCORING["SV"] +
                    stat.get("holds", 0) * SCORING["HD"] +
                    stat.get("qualityStarts", 0) * SCORING["QS"] +
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

        return round(total_points, 1)

    except Exception as e:
        print(f"[ERROR] Failed to get stats for {player_name}: {e}")
        return 0

@app.route("/")
def index():
    return redirect("/fantasy")

@app.route("/fantasy")
def fantasy_page():
    return render_template("fantasy.html")

@app.route("/search")
def search_page():
    return render_template("search.html")

@app.route("/api/live_points")
def live_points():
    try:
        with open("teams.json") as f:
            teams = json.load(f)
    except Exception as e:
        return jsonify({"error": f"Failed to load teams.json: {e}"}), 500

    results = []
    for team in teams:
        team_total = 0
        players_with_points = []

        for p in team["players"]:
            if p.get("status", "").lower() == "bench":
                continue  # ✅ Skip bench players

            points = get_player_stats_for_range(p["name"])
            players_with_points.append({
                "name": p["name"],
                "position": p["position"],
                "points": points
            })
            team_total += points

        results.append({
            "team_name": team["team_name"],
            "owner": team["owner"]["displayName"] if isinstance(team["owner"], dict) else team["owner"],
            "total": round(team_total, 1),
            "players": players_with_points
        })

    return jsonify(results)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
