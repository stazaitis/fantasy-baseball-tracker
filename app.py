import os
import json
import requests
import threading
from datetime import datetime, date, timedelta
from flask import Flask, jsonify, render_template, redirect
from waitress import serve
from dotenv import load_dotenv

# Initialize Flask app
app = Flask(__name__)
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Matchup 3 (April 7 – April 13)
MATCHUP_START = date(2025, 4, 7)
MATCHUP_END = date(2025, 4, 13)

# Fantasy scoring rules
SCORING = {
    "H": 0.5, "R": 1, "TB": 1, "RBI": 1, "BB": 1, "SO": -1, "SB": 1,
    "OUTS": 1, "H_ALLOWED": -1, "ER": -2, "BB_ISSUED": -1, "K": 1,
    "QS": 3, "CG": 3, "NH": 7, "PG": 10, "W": 5, "L": -5, "SV": 5, "HD": 3
}

# Cache for player stats
stats_cache = {
    "last_updated": None,
    "is_updating": False,
    "data": []
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
                    try:
                        acquired_dt = datetime.fromisoformat(acquired_datetime).replace(tzinfo=first_game_start.tzinfo)
                        if acquired_dt >= first_game_start:
                            continue
                    except:
                        print(f"⚠️ Error parsing acquired date for {player_name}")

                if dropped_datetime:
                    try:
                        dropped_dt = datetime.fromisoformat(dropped_datetime).replace(tzinfo=first_game_start.tzinfo)
                        if dropped_dt <= first_game_start:
                            continue
                    except:
                        print(f"⚠️ Error parsing dropped date for {player_name}")

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

def update_stats_background():
    """Run the stats update in a background thread"""
    global stats_cache
    
    if stats_cache["is_updating"]:
        return "Already updating"
    
    stats_cache["is_updating"] = True
    
    def background_task():
        try:
            with open("teams.json", "r") as f:
                teams = json.load(f)
            
            result = []
            
            for team in teams:
                team_name = team.get("team_name", "Unknown")
                team_points = 0
                player_results = []
                
                players = team.get("players", [])
                if not players:
                    print(f"⚠️ No players found for team: {team_name}")
                    continue
                
                for player in players:
                    name = player.get("name")
                    acquired = player.get("acquiredDateTime")
                    dropped = player.get("droppedDateTime")
                    
                    # Process player stats
                    try:
                        points = get_player_stats_for_range(name, acquired, dropped)
                        print(f"📊 {name}: {points} pts")
                    except Exception as e:
                        print(f"❌ Error processing {name}: {e}")
                        points = 0
                    
                    player_results.append({
                        "name": name,
                        "points": points
                    })
                    team_points += points
                
                result.append({
                    "team": team_name,
                    "total_points": round(team_points, 1),
                    "players": player_results
                })
            
            # Update the cache with new data
            stats_cache["data"] = result
            stats_cache["last_updated"] = datetime.now().isoformat()
            
            # Send Discord notification if webhook is configured
            if DISCORD_WEBHOOK_URL:
                try:
                    teams_sorted = sorted(result, key=lambda x: x["total_points"], reverse=True)
                    message = "📊 **Fantasy Baseball Live Points Update**\n\n"
                    for i, team in enumerate(teams_sorted):
                        message += f"**{i+1}. {team['team']}**: {team['total_points']} pts\n"
                    
                    requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
                except Exception as e:
                    print(f"❌ Discord notification failed: {e}")
                    
        except Exception as e:
            print(f"❌ Background stats update failed: {e}")
        finally:
            stats_cache["is_updating"] = False
    
    # Start the background thread
    thread = threading.Thread(target=background_task)
    thread.daemon = True
    thread.start()
    
    return "Started stats update"

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
    """Return cached stats or trigger an update if needed"""
    global stats_cache
    
    # If no data exists or it's been more than 2 hours since last update
    if (not stats_cache["data"] or 
        (stats_cache["last_updated"] is None) or
        (datetime.now() - datetime.fromisoformat(stats_cache["last_updated"])).total_seconds() > 7200):
        if not stats_cache["is_updating"]:
            update_stats_background()
    
    # Return status and data
    return {
        "live_points": stats_cache["data"],
        "last_updated": stats_cache["last_updated"],
        "updating": stats_cache["is_updating"]
    }, 200

@app.route("/api/update_stats", methods=["GET"])
def trigger_update():
    """Manually trigger a stats update"""
    result = update_stats_background()
    return {"status": result}, 200

@app.route("/api/teams")
def teams_api():
    """Just return the teams without calculating points"""
    try:
        with open("teams.json", "r") as f:
            teams = json.load(f)
        return {"teams": teams}, 200
    except Exception as e:
        return {"error": f"Failed to load teams.json: {str(e)}"}, 500

@app.route("/api/player_stats/<player_name>")
def player_stats_api(player_name):
    """Test endpoint to get stats for a single player"""
    try:
        points = get_player_stats_for_range(player_name)
        return {
            "player": player_name, 
            "points": points
        }, 200
    except Exception as e:
        return {"error": f"Failed to get stats for {player_name}: {str(e)}"}, 500

# Run the app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    
    # Start initial stats calculation in background
    update_stats_background()
    
    # Run the server
    serve(app, host="0.0.0.0", port=port)