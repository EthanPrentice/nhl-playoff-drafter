import csv
import os
from typing import Callable

from player import Player
from team import Team
import heuristics

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
RESOURCES_DIR = os.path.join(ROOT_DIR, "resources/2025")
OUTPUT_DIR = os.path.join(ROOT_DIR, "out/2025")


# I/O
def read_csv_to_dicts(filename) -> list[dict[str, str]]:
    with open(os.path.join(RESOURCES_DIR, filename), mode="r", newline="", encoding="utf-8") as f:
        csv_reader = csv.DictReader(f, delimiter="\t")
        return list(csv_reader)


def write_players_to_csv(players: list[Player], filename):
    with open(os.path.join(OUTPUT_DIR, filename), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["EV", "Name", "Team", "TEV", "Pos", "GP", "SGP", "G", "A", "P", "ESP"])
        for p in players:
            writer.writerow([f"{p.estimatedValue:.3f}", p.name, p.team.name, f"{p.team.estimatedValue:.3f}", p.position,
                             p.seasonStats.games_played, p.stretchStats.games_played, p.seasonStats.goals, 
                             p.seasonStats.assists, p.seasonStats.points, p.seasonStats.even_strength_points])

def write_teams_to_csv(teams: list[Team], filename):
    with open(os.path.join(OUTPUT_DIR, filename), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["EV", "Name"])
        for team in teams:
            writer.writerow([f"{team.estimatedValue:.3f}", team.name])

def get_teams():
    return [Team(v) for v in read_csv_to_dicts("teams.tsv")]

def get_players(teams: list[Team]) -> list[Player]:
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


def write_results(teams: list[Team], players: list[Player], output_dir: str):
    write_teams_to_csv(teams, os.path.join(output_dir, "teams.tsv"))

    write_players_to_csv(players, os.path.join(output_dir, "all.tsv"))

    forwards = filter(lambda x: x.position == "F", players)
    write_players_to_csv(forwards, os.path.join(output_dir, "forwards.tsv"))

    defense = filter(lambda x: x.position == "D", players)
    write_players_to_csv(defense, os.path.join(output_dir, "defense.tsv"))


def set_team_estimated_values(teams: list[Team], heuristic: Callable[[Team], float]):
    for team in teams:
        team.estimatedValue = heuristic(team)

    teams.sort(key=lambda x: x.estimatedValue, reverse=True)


def set_player_estimated_values(players: list[Player], heuristic: Callable[[Player], float]):
    for player in players:
        player.estimatedValue = heuristic(player)

    players.sort(key=lambda x: x.estimatedValue, reverse=True)


# MAIN
def main():
    teams = get_teams()
    players = get_players(teams)

    set_team_estimated_values(teams, heuristics.get_team_weight_diff_penalty)
    set_player_estimated_values(players, heuristics.sum_team_odds_multiply_points_esp_stretch_weighted_per_game)

    write_results(teams, players, OUTPUT_DIR)

    print("SUCCESS")


if __name__ == "__main__":
    main()
