import requests
import json

ESPN_LEAGUE_ID = 121956
SWID = "{213A1465-139E-4467-BA14-65139EB467BF}"
ESPN_S2 = "AEC5Kzs9YF3IT3q9VqL4Zwmtou69e3CTdfNHOuH1PZvo2z2FuAVbZLIJCzlJAEdkh4XEaumgT%2BFYtZzpHu8zIt%2FI1OpvNeNs4Gk6sHxnkp4w%2B%2BWDwp40O93MJaHlIezpNIr%2FX1Xkqv%2BgdTxfodJkV%2FsJ7dZIhii%2BOb2jOOPqWW%2FDRktzj1hXRaVIK%2B9nIMpr6oRBBagXnwI5CsWkWGKnHLc9%2BP%2FNytJ5j74HjOOpfh2JYTfuL7UKYMCWczCSwGY%2BmBR%2FFSealrl3TL6ATHyV%2FiOjoZrOB%2FXWulVsPTw8Ny7dfg%3D%3D"

HEADERS = {
    "x-fantasy-filter": "{}",
    "User-Agent": "Mozilla/5.0",
    "Cookie": f"espn_s2={ESPN_S2}; SWID={SWID};"
}

def fetch_teams():
    url = f"https://fantasy.espn.com/apis/v3/games/flb/seasons/2025/segments/0/leagues/{ESPN_LEAGUE_ID}?view=mMatchup&view=mRoster&view=mTeam"
    res = requests.get(url, headers=HEADERS)
    data = res.json()

    teams = []
    for team in data["teams"]:
        team_info = {
            "team_name": team["location"] + " " + team["nickname"],
            "owner": team["owners"] and team["owners"][0],
            "players": []
        }

        for player in team.get("roster", {}).get("entries", []):
            player_name = player["playerPoolEntry"]["player"]["fullName"]
            position = player["playerPoolEntry"]["player"]["defaultPositionId"]
            status = "starter" if player["lineupSlotId"] < 20 else "bench"

            team_info["players"].append({
                "name": player_name,
                "position": position,
                "status": status
            })

        teams.append(team_info)

    return teams

if __name__ == "__main__":
    teams = fetch_teams()
    with open("teams.json", "w") as f:
        json.dump(teams, f, indent=2)
    print("✅ teams.json updated from ESPN API")