import os
import json
import requests
import threading
import traceback
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
    try:
        res = requests.get(url)
        data = res.json()
        dates = data.get("dates", [])
        if not dates:
            print(f"No games found for date: {game_date}")
            return None
            
        games = dates[0].get("games", [])
        if not games:
            print(f"No games found in dates for: {game_date}")
            return None
            
        start_times = []
        for game in games:
            if "gameDate" in game:
                start_times.append(datetime.fromisoformat(game["gameDate"].replace("Z", "+00:00")))
            
        if not start_times:
            print(f"No start times found for games on: {game_date}")
            return None
            
        return min(start_times)
    except Exception as e:
        print(f"Error getting game start time for {game_date}: {str(e)}")
        return None

def get_player_id(player_name):
    print(f"Looking up player ID for: {player_name}")
    url = f"https://statsapi.mlb.com/api/v1/people/search?names={player_name}"
    try:
        res = requests.get(url)
        data = res.json()
        people = data.get("people", [])
        
        if not people:
            print(f"❌ No player found with name: {player_name}")
            return None
            
        player_id = people[0].get("id")
        print(f"✅ Found player ID {player_id} for {player_name}")
        return player_id
    except Exception as e:
        print(f"❌ Error getting ID for {player_name}: {str(e)}")
        return None

def get_player_stats_for_range(player_name, acquired_datetime=None, dropped_datetime=None):
    print(f"Getting stats for player: {player_name}")
    player_id = get_player_id(player_name)
    if not player_id:
        print(f"⚠️ No ID found for {player_name}")
        return 0

    current_year = datetime.now().year
    group = "hitting" if "ohtani" in player_name.lower() else "all"
    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=gameLog&group={group}&season={current_year}"

    try:
        res = requests.get(url)
        data = res.json()
        stats = data.get("stats", [])
        
        if not stats:
            print(f"⚠️ No stats found for {player_name}")
            return 0
            
        game_logs = stats[0].get("splits", [])
        print(f"📊 Found {len(game_logs)} game logs for {player_name}")
        
        total_points = 0
        counted_games = 0

        for game in game_logs:
            try:
                game_date = datetime.strptime(game["date"], "%Y-%m-%d").date()
                
                # Check if game is in matchup range
                if not (MATCHUP_START <= game_date <= MATCHUP_END):
                    print(f"📅 Game on {game_date} for {player_name} is outside matchup range")
                    continue

                print(f"📅 Processing game on {game_date} for {player_name}")
                first_game_start = get_first_game_start_datetime(game_date)
                if not first_game_start:
                    print(f"⚠️ Could not determine first game start time for {game_date}")
                    continue

                # Handle acquisition logic
                if acquired_datetime:
                    try:
                        acquired_dt = datetime.fromisoformat(acquired_datetime).replace(tzinfo=first_game_start.tzinfo)
                        if acquired_dt >= first_game_start:
                            print(f"⏱️ Player {player_name} was acquired after game start on {game_date}")
                            continue
                    except Exception as e:
                        print(f"⚠️ Error parsing acquired date for {player_name}: {str(e)}")

                if dropped_datetime:
                    try:
                        dropped_dt = datetime.fromisoformat(dropped_datetime).replace(tzinfo=first_game_start.tzinfo)
                        if dropped_dt <= first_game_start:
                            print(f"⏱️ Player {player_name} was dropped before game start on {game_date}")
                            continue
                    except Exception as e:
                        print(f"⚠️ Error parsing dropped date for {player_name}: {str(e)}")

                stat = game["stat"]
                game_points = 0
                pitching = "inningsPitched" in stat

                if pitching:
                    ip = stat.get("inningsPitched", "0.0")
                    outs = int(ip.split(".")[0]) * 3 + int(ip.split(".")[1]) if "." in ip else int(ip) * 3
                    earned_runs = stat.get("earnedRuns", 0)
                    if outs >= 18 and earned_runs <= 3:
                        game_points += SCORING["QS"]

                    game_points += (
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
                    game_points += (
                        stat.get("hits", 0) * SCORING["H"] +
                        stat.get("runs", 0) * SCORING["R"] +
                        stat.get("totalBases", 0) * SCORING["TB"] +
                        stat.get("rbi", 0) * SCORING["RBI"] +
                        stat.get("baseOnBalls", 0) * SCORING["BB"] +
                        stat.get("strikeOuts", 0) * SCORING["SO"] +
                        stat.get("stolenBases", 0) * SCORING["SB"]
                    )
                
                total_points += game_points
                counted_games += 1
                print(f"⚾ {player_name} scored {game_points} points on {game_date}")
                
            except Exception as e:
                print(f"⚠️ Error processing game for {player_name}: {str(e)}")

        print(f"📊 Total: {player_name} scored {total_points} points in {counted_games} games")
        return round(total_points, 1)

    except Exception as e:
        print(f"❌ Failed to fetch stats for {player_name}: {str(e)}")
        print(f"❌ Error details: {traceback.format_exc()}")
        return 0

def update_stats_background():
    """Run the stats update in a background thread"""
    global stats_cache

    if stats_cache["is_updating"]:
        return "Already updating"

    stats_cache["is_updating"] = True
    print("🚀 Starting background stats calculation process...")

    def background_task():
        try:
            print("📊 Starting background stats calculation...")

            with open("teams.json", "r") as f:
                teams_data = json.load(f)

            print(f"📊 Loaded teams.json with type: {type(teams_data)}")

            # ✅ Normalize into list once — no need to do it twice
            if isinstance(teams_data, dict):
                print(f"📊 teams.json is a dictionary with {len(teams_data)} keys")
                teams = list(teams_data.values())
            else:
                print(f"📊 teams.json is a list with {len(teams_data)} items")
                teams = teams_data

            result = []

            for team in teams:
                team_name = team.get("team_name", "Unknown")
                print(f"📊 Processing team: {team_name}")
                team_points = 0
                starters = []
                bench = []

                players = team.get("players", [])
                if not players:
                    print(f"⚠️ No players found for team: {team_name}")
                    continue

                print(f"📊 Found {len(players)} players for team: {team_name}")

                for idx, player in enumerate(players):
                    name = player.get("name")
                    if not name:
                        print(f"⚠️ Player without name found in team {team_name}")
                        continue

                    acquired = player.get("acquiredDateTime")
                    dropped = player.get("droppedDateTime")
                    is_bench = player.get("status") == "bench"

                    print(f"📊 Processing player {idx+1}/{len(players)}: {name}")
                    try:
                        points = get_player_stats_for_range(name, acquired, dropped)
                        print(f"📊 {name}: {points} pts")
                    except Exception as e:
                        print(f"❌ Error processing {name}: {str(e)}")
                        print(f"❌ Error details: {traceback.format_exc()}")
                        points = 0

                    player_info = {
                        "name": name,
                        "points": points
                    }

                    if is_bench:
                        bench.append(player_info)
                    else:
                        starters.append(player_info)
                        team_points += points

                result.append({
                    "team": team_name,
                    "total_points": round(team_points, 1),
                    "starters": starters,
                    "bench": bench
                })

            stats_cache["data"] = result
            stats_cache["last_updated"] = datetime.now().isoformat()
            print("📊 Stats calculation completed successfully!")

            if DISCORD_WEBHOOK_URL:
                try:
                    teams_sorted = sorted(result, key=lambda x: x["total_points"], reverse=True)
                    message = "📊 **Fantasy Baseball Live Points Update**\n\n"
                    for i, team in enumerate(teams_sorted):
                        message += f"**{i+1}. {team['team']}**: {team['total_points']} pts\n"

                    requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
                    print("📊 Discord notification sent!")
                except Exception as e:
                    print(f"❌ Discord notification failed: {str(e)}")

        except Exception as e:
            print(f"❌ Background stats update failed: {str(e)}")
            print(f"❌ Error details: {traceback.format_exc()}")
        finally:
            stats_cache["is_updating"] = False
            print("📊 Background process complete, updating status set to false")

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

@app.route("/api/update_stats")
def trigger_update():
    """Manually trigger a stats update"""
    result = update_stats_background()
    return {"status": result}, 200

@app.route("/api/teams")
def teams_api():
    """Just return the teams without calculating points"""
    try:
        print(f"🔍 DEBUG: Attempting to load teams.json from current directory")
        import os
        print(f"🔍 DEBUG: Current directory: {os.getcwd()}")
        print(f"🔍 DEBUG: Directory contents: {os.listdir()}")
        
        with open("teams.json", "r") as f:
            content = f.read()
            print(f"🔍 DEBUG: File content length: {len(content)}")
            teams = json.loads(content)
            print(f"🔍 DEBUG: Loaded teams count: {len(teams)}")
        
        return teams, 200
    except Exception as e:
        print(f"❌ DEBUG: Error loading teams.json: {str(e)}")
        print(f"❌ DEBUG: Error details: {traceback.format_exc()}")
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

@app.route("/api/test_player/<player_name>")
def test_player_api(player_name):
    """Test endpoint to get detailed stats for a single player"""
    try:
        print(f"🔍 TEST: Starting detailed test for player: {player_name}")
        
        # Get the raw stats for this player
        player_id = get_player_id(player_name)
        if not player_id:
            return {"error": f"Could not find ID for {player_name}"}, 404
            
        current_year = datetime.now().year
        group = "hitting" if "ohtani" in player_name.lower() else "all"
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=gameLog&group={group}&season={current_year}"
        
        print(f"🔍 TEST: Requesting stats from URL: {url}")
        res = requests.get(url)
        data = res.json()
        
        # Log the raw data structure for diagnosis
        print(f"🔍 TEST: Raw API response structure: {json.dumps(data)[:200]}...")
        
        points = get_player_stats_for_range(player_name)
        
        return {
            "player": player_name,
            "player_id": player_id, 
            "points": points,
            "matchup_range": f"{MATCHUP_START} to {MATCHUP_END}"
        }, 200
    except Exception as e:
        print(f"❌ TEST ERROR: {str(e)}")
        print(traceback.format_exc())
        return {"error": f"Test failed: {str(e)}"}, 500

@app.route("/api/debug")
def debug_info():
    """Return debugging information"""
    try:
        with open("teams.json", "r") as f:
            teams_data = json.load(f)
        
        # Get the structure and first few items
        data_type = type(teams_data).__name__
        
        if isinstance(teams_data, dict):
            sample = list(teams_data.keys())[:3]
            size = len(teams_data)
            first_team = next(iter(teams_data.values()))
        elif isinstance(teams_data, list):
            sample = [t.get("team_name", "Unknown") for t in teams_data[:3]]
            size = len(teams_data)
            first_team = teams_data[0] if teams_data else {}
        else:
            sample = str(teams_data)[:100]
            size = len(str(teams_data))
            first_team = {}
        
        # Get a sample player
        sample_player = None
        if first_team and "players" in first_team and first_team["players"]:
            sample_player = first_team["players"][0]
        
        return {
            "teams_data_type": data_type,
            "teams_count": size,
            "sample": sample,
            "sample_player": sample_player,
            "matchup_dates": {
                "start": str(MATCHUP_START),
                "end": str(MATCHUP_END),
                "current": str(date.today())
            }
        }, 200
    except Exception as e:
        return {"error": f"Debug failed: {str(e)}"}, 500

# Run the app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting server on port {port}")
    
    # Run the server
    serve(app, host="0.0.0.0", port=port)