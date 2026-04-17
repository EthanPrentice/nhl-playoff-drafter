import csv
import os
from typing import Callable

from player import Player
from team import Team
import heuristics

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
RESOURCES_DIR = os.path.join(ROOT_DIR, "resources", "2026")
OUTPUT_DIR = os.path.join(ROOT_DIR, "out", "season_2026")


# I/O
def read_csv_to_dicts(filename) -> list[dict[str, str]]:
    with open(os.path.join(RESOURCES_DIR, filename), mode="r", newline="", encoding="utf-8") as f:
        csv_reader = csv.DictReader(f, delimiter="\t")
        return list(csv_reader)


def write_players_to_csv(players: list[Player], filename):
    with open(os.path.join(OUTPUT_DIR, filename), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["EV", "Name", "Team", "TEV", "Pos", "GP", "SGP", "G", "A", "P", "ESP", "PM", "S", "Bl", "H"])
        for p in players:
            writer.writerow([f"{p.estimatedValue:.3f}", p.name, p.team.name, f"{p.team.estimatedValue:.3f}", p.position,
                             p.seasonStats.games_played, p.stretchStats.games_played, p.seasonStats.goals, 
                             p.seasonStats.assists, p.seasonStats.points, p.seasonStats.even_strength_points,
                             p.seasonStats.plus_minus, p.seasonStats.shots, p.seasonStats.blocks, p.seasonStats.hits])

def write_teams_to_csv(teams: list[Team], filename):
    with open(os.path.join(OUTPUT_DIR, filename), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["EV", "Name"])
        for team in teams:
            writer.writerow([f"{team.estimatedValue:.3f}", team.name])

def get_teams():
    # playoff_teams = [Team(v) for v in read_csv_to_dicts("teams.tsv")]
    return [Team.from_name(v) for v in [
        "ANA", "BOS", "BUF", "CAR", "CBJ", "CGY", "CHI", "COL", "DAL", "DET", "EDM", "FLA", "LAK", "MIN",
        "MTL", "NJD", "NSH", "NYI", "NYR", "OTT", "PHI", "PIT", "SEA", "SJS", "STL", "TBL", "TOR", "UTA",
        "VAN", "VGK", "WPG", "WSH"
    ]]


def get_players(teams: list[Team]) -> list[Player]:
    player_season_stats = read_csv_to_dicts("players_season.tsv")
    player_stretch_stats = read_csv_to_dicts("players_stretch.tsv")
    player_prev_season_stats = read_csv_to_dicts("players_prev_season.tsv")

    # TODO: optimize, but eh who cares. small data.
    results = []
    for season_stats in player_season_stats:
        for stretch_stats in player_stretch_stats:
            matching1 = season_stats["Name"] == stretch_stats["Name"] and season_stats["Team"] == stretch_stats["Team"]
            for prev_season_stats in player_prev_season_stats:
                matching2 = season_stats["Name"] == prev_season_stats["Name"] and season_stats["Team"] == prev_season_stats["Team"]
                if matching1 and matching2:
                    for team in teams:
                        if team.name == season_stats["Team"]:
                            results.append(Player(team, season_stats, stretch_stats, prev_season_stats))
                            break
                    break
            else:
                if matching1:
                    for team in teams:
                        if team.name == season_stats["Team"]:
                            results.append(Player(team, season_stats, stretch_stats))
                    break

    return results


def write_results(teams: list[Team], players: list[Player], output_dir: str):
    write_teams_to_csv(teams, os.path.join(output_dir, "teams.tsv"))

    write_players_to_csv(players, os.path.join(output_dir, "all.tsv"))

    forwards = filter(lambda x: x.position == "F", players)
    write_players_to_csv(forwards, os.path.join(output_dir, "forwards.tsv"))

    defense = filter(lambda x: x.position == "D", players)
    write_players_to_csv(defense, os.path.join(output_dir, "defense.tsv"))


# HEURISTICS
def normalize_team_values(teams, new_min=0.8, new_max=1.2):
    if not teams:
        return
    values = [t.estimatedValue for t in teams]
    min_val = min(values)
    max_val = max(values)
    if min_val == max_val:
        mid = (new_min + new_max) / 2
        for t in teams:
            t.estimatedValue = mid
        return
    scale = (new_max - new_min) / (max_val - min_val)
    for t in teams:
        t.estimatedValue = new_min + (t.estimatedValue - min_val) * scale


def set_team_estimated_values(teams: list[Team], players: list[Player], heuristic: Callable[[Team, list[Player]], float]):
    for team in teams:
        team.estimatedValue = heuristic(team, players)

    normalize_team_values(teams)
    teams.sort(key=lambda x: x.estimatedValue, reverse=True)


def set_player_estimated_values(players: list[Player], heuristic: Callable[[Player], float]):
    for player in players:
        player.estimatedValue = heuristic(player)

    players.sort(key=lambda x: x.estimatedValue, reverse=True)


# MAIN
def main():
    teams = get_teams()
    players = get_players(teams)

    set_player_estimated_values(players, heuristics.yahoo_default_with_past)
    set_team_estimated_values(teams, players, heuristics.get_team_weight_all_players)

    write_results(teams, players, OUTPUT_DIR)

    print("SUCCESS")


if __name__ == "__main__":
    main()
