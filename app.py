from flask import Flask, jsonify, render_template, redirect
import json
import requests
from datetime import datetime, date
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

SCORING = {
    "H": 0.5, "R": 1, "TB": 1, "RBI": 1, "BB": 1, "SO": -1, "SB": 1,
    "OUTS": 1, "H_ALLOWED": -1, "ER": -2, "BB_ISSUED": -1, "K": 1,
    "QS": 3, "CG": 3, "NH": 7, "PG": 10, "W": 5, "L": -5, "SV": 5, "HD": 3
}

MATCHUP_START = date(2025, 3, 31)
MATCHUP_END = date(2025, 4, 6)


def get_player_id(player_name):
    url = f"https://statsapi.mlb.com/api/v1/people/search?names={player_name}"
    try:
        res = requests.get(url).json()
        return res.get("people", [{}])[0].get("id")
    except:
        return None


def get_player_stats_for_range(player_name, add_date=None):
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
                if not (MATCHUP_START <= game_date <= min(MATCHUP_END, date.today())):
                    continue
                if add_date and game_date < add_date:
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
                        outs * SCORING["OUTS"] + stat.get("hits", 0) * SCORING["H_ALLOWED"] +
                        earned_runs * SCORING["ER"] + stat.get("baseOnBalls", 0) * SCORING["BB_ISSUED"] +
                        stat.get("strikeOuts", 0) * SCORING["K"] + stat.get("wins", 0) * SCORING["W"] +
                        stat.get("losses", 0) * SCORING["L"] + stat.get("saves", 0) * SCORING["SV"] +
                        stat.get("holds", 0) * SCORING["HD"] + stat.get("completeGames", 0) * SCORING["CG"] +
                        stat.get("noHitters", 0) * SCORING["NH"] + stat.get("perfectGames", 0) * SCORING["PG"]
                    )
                else:
                    total_points += (
                        stat.get("hits", 0) * SCORING["H"] + stat.get("runs", 0) * SCORING["R"] +
                        stat.get("totalBases", 0) * SCORING["TB"] + stat.get("rbi", 0) * SCORING["RBI"] +
                        stat.get("baseOnBalls", 0) * SCORING["BB"] + stat.get("strikeOuts", 0) * SCORING["SO"] +
                        stat.get("stolenBases", 0) * SCORING["SB"]
                    )
            except:
                continue

        return round(total_points, 1)
    except:
        return 0


@app.route("/")
def home():
    return redirect("/fantasy")


@app.route("/fantasy")
def fantasy_page():
    return render_template("fantasy.html")


@app.route("/api/live_points")
def live_points():
    with open("teams.json") as f:
        teams = json.load(f)

    results = []
    for team in teams:
        team_total = 0
        players_with_points = []
        added_today = date.today()

        for p in team["players"]:
            if p.get("status", "").lower() == "bench":
                continue

            add_date = date.fromisoformat(p["added"][:10]) if "added" in p else MATCHUP_START
            points = get_player_stats_for_range(p["name"], add_date=add_date)

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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
