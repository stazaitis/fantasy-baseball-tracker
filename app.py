from flask import Flask, jsonify, render_template
import json
import statsapi
from datetime import datetime, date

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

def get_player_stats_for_range(player_name):
    try:
        search = statsapi.lookup_player(player_name)
        if not search:
            return 0
        player_id = search[0]['id']
        games = statsapi.player_stat_game_log(player_id, group='hitting', type='byDate')
        points = 0
        for game in games:
            game_date = datetime.strptime(game['game_date'], '%Y-%m-%d').date()
            if MATCHUP_START <= game_date <= MATCHUP_END:
                points += calculate_points(game['stat'])
        return points
    except Exception as e:
        print(f"⚠️ Error for {player_name}: {e}")
        return 0

@app.route("/fantasy")
def fantasy():
    return render_template("fantasy.html")

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

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


