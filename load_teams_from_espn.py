import json
from espn_api.baseball import League

# ESPN League Credentials
LEAGUE_ID = 121956
SEASON_YEAR = 2025
SWID = '{213A1465-139E-4467-BA14-65139EB467BF}'
ESPN_S2 = 'AEC5Kzs9YF3IT3q9VqL4Zwmtou69e3CTdfNHOuH1PZvo2z2FuAVbZLIJCzlJAEdkh4XEaumgT%2BFYtZzpHu8zIt%2FI1OpvNeNs4Gk6sHxnkp4w%2B%2BWDwp40O93MJaHlIezpNIr%2FX1Xkqv%2BgdTxfodJkV%2FsJ7dZIhii%2BOb2jOOPqWW%2FDRktzj1hXRaVIK%2B9nIMpr6oRBBagXnwI5CsWkWGKnHLc9%2BP%2FNytJ5j74HjOOpfh2JYTfuL7UKYMCWczCSwGY%2BmBR%2FFSealrl3TL6ATHyV%2FiOjoZrOB%2FXWulVsPTw8Ny7dfg%3D%3D'

def fetch_teams():
    league = League(league_id=LEAGUE_ID, year=SEASON_YEAR, espn_s2=ESPN_S2, swid=SWID)

    teams_output = []
    for team in league.teams:
        team_entry = {
            "owner": team.owners[0] if isinstance(team.owners, list) else team.owners,
            "team_name": team.team_name,
            "players": []
        }

        for player in team.roster:  # Includes starters, bench, IL
            team_entry["players"].append({
                "name": player.name,
                "position": player.position
            })

        teams_output.append(team_entry)

    with open("teams.json", "w") as f:
        json.dump(teams_output, f, indent=2)

    print("✅ Updated teams.json with full active rosters.")

if __name__ == "__main__":
    fetch_teams()
