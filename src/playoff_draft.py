import csv
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
RESOURCES_DIR = os.path.join(ROOT_DIR, "resources/2025")
OUTPUT_DIR = os.path.join(ROOT_DIR, "out/2025")

# I/O
def read_csv_to_dicts(filename):
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

# GENERAL
def filter_dict_keys(data, keys):
    return [{ k: d[k] for k in keys if k in d } for d in data]

# UTILS
def get_active_team_names(teams):
    return list(map(lambda v: v["Team"], teams))

def filter_active_players(teams, players):
    active_team_names = get_active_team_names(teams)
    filter_fn = lambda v: v["Team"] in active_team_names
    return list(filter(filter_fn, players))

# HEURISTICS
def get_team_weights(data):
    result = {}
    for item in data:
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
    # read teams and players
    teams = read_csv_to_dicts("teams.tsv")
    # filter players to include key values
    players = filter_dict_keys(
        data=read_csv_to_dicts("players_feb1.tsv"), 
        keys=["Name", "Team", "Pos", "G", "A", "P"]
    )
    # filter for players on playoff teams
    active_players = filter_active_players(teams, players)

    players_with_heuristics = sorted(append_heuristics(active_players, teams), key=lambda v: v["EstimatedValue"], reverse=True)

    # write results for all skaters
    write_dicts_to_csv(players_with_heuristics, "all.tsv")

    # write results for F/D to separate files
    forwards = list(filter(lambda v: v["Pos"] == "F", players_with_heuristics))
    defensemen = list(filter(lambda v: v["Pos"] == "D", players_with_heuristics))

    write_dicts_to_csv(forwards, "forward.tsv")
    write_dicts_to_csv(defensemen, "defense.tsv")

    print("SUCCESS")
