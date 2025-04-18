import csv
import os

from player import Player, PlayerStats
from team import Team, TeamPlayoffOdds

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
RESOURCES_DIR = os.path.join(ROOT_DIR, "resources/2025")
OUTPUT_DIR = os.path.join(ROOT_DIR, "out/2025")

# I/O
def read_csv_to_dicts(filename) -> list[dict[str, str]]:
    def tryToNum(value):
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

    with open(os.path.join(RESOURCES_DIR, filename), mode="r", newline="", encoding="utf-8") as f:
        csv_reader = csv.DictReader(f, delimiter="\t",)
        data = []
        for row in csv_reader:
            # apply the tryToNum fn to each value in the dictionary
            converted_row = { key: tryToNum(value) for key, value in row.items() }
            data.append(converted_row)
    
    return data

def write_dicts_to_csv(data, filename):
    with open(os.path.join(OUTPUT_DIR, filename), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(data)

def get_players() -> list[Player]:
    teams = [Team(v) for v in read_csv_to_dicts("teams.tsv")]
    player_season_stats = read_csv_to_dicts("players_season.tsv")
    player_stretch_stats = read_csv_to_dicts("players_stretch.tsv")

    # TODO: optimize, but eh who cares. small data.
    results = []
    for season_stats in player_season_stats:
        for stretch_stats in player_stretch_stats:
            if season_stats["Name"] == stretch_stats["Name"] and season_stats["Team"] == stretch_stats["Team"]:
                for team in teams:
                    if team.name == season_stats["Team"]:
                        results.append(Player(team, season_stats, stretch_stats))
        
    return results

# HEURISTICS
def get_team_weights(players: list[Player]):
    result = {}
    for player in players:
        if "Team" in item:
            name = item.pop("Team")
            # sum of all numbers in the dict
            total_sum = sum(value for value in item.values() if isinstance(value, (int, float)))
            result[name] = total_sum
    return result

def append_heuristics(players, teams):
    team_weights = get_team_weights(teams)

    def append_heuristics_to_entry(v):
        team_weight = team_weights[v["Team"]]
        return { **v, "TeamWeight": f"{team_weight:.4f}", "EstimatedValue": round(v["P"] * team_weight) }

    return list(map(append_heuristics_to_entry, players))

# MAIN
if __name__ == "__main__":

    # filter players to include key values
    players = get_players()

    print(players)

    print("SUCCESS")
