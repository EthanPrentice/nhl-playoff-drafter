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


def set_estimated_values(players: list[Player], heuristic: Callable[[Player], float]):
    for player in players:
        player.estimatedValue = heuristic(player)

    players.sort(key=lambda x: x.estimatedValue, reverse=True)


# MAIN
def main():
    # filter players to include key values
    players = get_players()

    set_estimated_values(players, heuristics.sum_team_odds_multiply_points_stretch_weighted)

    for p in players:
        print(p)

    print("SUCCESS")


if __name__ == "__main__":
    main()
