from flask import Flask, jsonify, render_template
import json
import requests
from datetime import datetime, date
import os

app = Flask(__name__)

# Matchup 2: Mar 31 – Apr 6
MATCHUP_START = date(2025, 3, 31)
MATCHUP_END = date(2025, 4, 6)

SCORING = {
    "H": 0.5,
    "R": 1,
    "TB": 1,
    "RBI": 1,
    "BB": 1,
    "SO": -1,
    "SB": 1
}

def calculate_points(stats):
    if not stats:
        return 0
    return (
        stats.get("hits", 0) * SCORING["H"] +
        stats.get("runs", 0) * SCORING["R"] +
        stats.get("totalBases", 0) * SCORING["TB"] +
        stats.get("rbi", 0) * SCORING["RBI"] +
        stats.get("baseOnBalls", 0) * SCORING["BB"] +
        stats.get("strikeOuts", 0) * SCORING["SO"] +
        stats.get("stolenBases", 0) * SCORING["SB"]
    )

def get_player_id(player_name):
    url = f"https://statsapi.mlb.com/api/v1/people/search?names={player_name}"
    res = requests.get(url).json()
    people = res.get("people", [])
    return people[0]["id"] if people else None

def get_player_stats_for_range(player_name):
    player_id = get_player_id(player_name)
    if not player_id:
        print(f"❌ Player not found: {player_name}")
        return 0

    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=gameLog&season=2025"
    res = requests.get(url).json()
    stats_list = res.get("stats", [])[0].get("splits", [])

    points = 0
    for entry in stats_list:
        game_date = entry.get("date")
        if not game_date:
            continue
        parsed_date = datetime.strptime(game_date, "%Y-%m-%d").date()
        if MATCHUP_START <= parsed_date <= MATCHUP_END:
            stat = entry["stat"]
            points += calculate_points(stat)

    return round(points, 1)

@app.route("/fantasy")
def fantasy():
    return render_template("fantasy.html")

@app.route("/search")
def search():
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
            points = get_player_stats_for_range(p["name"])
            players_with_points.append({
                "name": p["name"],
                "position": p["position"],
                "points": round(points, 1)
            })
            team_total += points

        results.append({
            "team_name": team["team_name"],
            "owner": team["owner"],
            "total": round(team_total, 1),
            "players": players_with_points
        })

    return jsonify(results)

@app.route("/api/test")
def test():
    return "ok"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
