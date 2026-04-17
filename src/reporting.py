import csv
from pathlib import Path
from typing import Iterable

from player import Player
from team import Team

PLAYER_HEADERS = ["EV", "Name", "Team", "TEV", "Pos", "GP", "SGP", "G", "A", "P", "ESP", "PM", "S", "Bl", "H"]
TEAM_HEADERS = ["EV", "Name"]


def write_players_to_tsv(players: Iterable[Player], output_path: Path) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle, delimiter="\t")
        writer.writerow(PLAYER_HEADERS)
        for player in players:
            writer.writerow([
                f"{player.estimatedValue:.3f}",
                player.name,
                player.team.name,
                f"{player.team.estimatedValue:.3f}",
                player.position,
                player.seasonStats.games_played,
                player.stretchStats.games_played,
                player.seasonStats.goals,
                player.seasonStats.assists,
                player.seasonStats.points,
                player.seasonStats.even_strength_points,
                player.seasonStats.plus_minus,
                player.seasonStats.shots,
                player.seasonStats.blocks,
                player.seasonStats.hits,
            ])


def write_teams_to_tsv(teams: list[Team], output_path: Path) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle, delimiter="\t")
        writer.writerow(TEAM_HEADERS)
        for team in teams:
            writer.writerow([f"{team.estimatedValue:.3f}", team.name])


def write_ranked_results(teams: list[Team], players: list[Player], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_teams_to_tsv(teams, output_dir / "teams.tsv")
    write_players_to_tsv(players, output_dir / "all.tsv")
    write_players_to_tsv((player for player in players if player.position == "F"), output_dir / "forwards.tsv")
    write_players_to_tsv((player for player in players if player.position == "D"), output_dir / "defense.tsv")
