import csv
from pathlib import Path
from typing import Iterable

from data_loader import LoadDiagnostics
from models import GoalieTeamProjection, SkaterProjection
from optimizer import OptimizedLineup
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


def _write_projection_rankings(
    projections: Iterable[SkaterProjection],
    output_path: Path,
) -> None:
    rows = sorted(projections, key=lambda item: (-item.expected_points, item.team, item.name))
    with open(output_path, "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle, delimiter="\t")
        writer.writerow(
            [
                "rank",
                "name",
                "team",
                "position",
                "ev",
                "floor",
                "ceiling",
                "season_rate",
                "stretch_rate",
                "blended_rate",
                "team_games_factor",
                "stretch_weight",
                "confidence_band",
            ]
        )
        for idx, item in enumerate(rows, start=1):
            writer.writerow(
                [
                    idx,
                    item.name,
                    item.team,
                    item.position,
                    f"{item.expected_points:.3f}",
                    f"{item.floor_points:.3f}",
                    f"{item.ceiling_points:.3f}",
                    f"{item.season_rate:.3f}",
                    f"{item.stretch_rate:.3f}",
                    f"{item.blended_rate:.3f}",
                    f"{item.team_games_factor:.3f}",
                    f"{item.stretch_weight:.3f}",
                    f"{item.floor_points:.3f}..{item.ceiling_points:.3f}",
                ]
            )


def _write_goalie_team_rankings(goalie_teams: Iterable[GoalieTeamProjection], output_path: Path) -> None:
    rows = sorted(goalie_teams, key=lambda item: (-item.expected_points, item.team))
    with open(output_path, "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle, delimiter="\t")
        writer.writerow(
            [
                "rank",
                "team",
                "ev",
                "floor",
                "ceiling",
                "w_component",
                "a_component",
                "so_component",
                "team_games_factor",
                "confidence_band",
            ]
        )
        for idx, item in enumerate(rows, start=1):
            writer.writerow(
                [
                    idx,
                    item.team,
                    f"{item.expected_points:.3f}",
                    f"{item.floor_points:.3f}",
                    f"{item.ceiling_points:.3f}",
                    f"{item.wins_component:.3f}",
                    f"{item.assists_component:.3f}",
                    f"{item.shutouts_component:.3f}",
                    f"{item.team_games_factor:.3f}",
                    f"{item.floor_points:.3f}..{item.ceiling_points:.3f}",
                ]
            )


def _iter_lineup_rows(label: str, lineup: OptimizedLineup) -> Iterable[list[str]]:
    for player in lineup.forwards:
        yield [label, "F", player.name, player.team, f"{player.expected_points:.3f}", f"{player.floor_points:.3f}", f"{player.ceiling_points:.3f}"]
    for player in lineup.defense:
        yield [label, "D", player.name, player.team, f"{player.expected_points:.3f}", f"{player.floor_points:.3f}", f"{player.ceiling_points:.3f}"]
    for team in lineup.goalie_teams:
        yield [label, "GT", team.team, team.team, f"{team.expected_points:.3f}", f"{team.floor_points:.3f}", f"{team.ceiling_points:.3f}"]


def write_draft_outputs(
    output_dir: Path,
    skater_projections: list[SkaterProjection],
    goalie_team_projections: list[GoalieTeamProjection],
    optimal_lineup: OptimizedLineup,
    alternative_lineups: dict[str, OptimizedLineup],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_projection_rankings((item for item in skater_projections if item.position == "F"), output_dir / "forwards.tsv")
    _write_projection_rankings((item for item in skater_projections if item.position == "D"), output_dir / "defense.tsv")
    _write_goalie_team_rankings(goalie_team_projections, output_dir / "goalie_teams.tsv")

    with open(output_dir / "optimal_lineup.tsv", "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle, delimiter="\t")
        writer.writerow(["lineup", "slot", "name", "team", "ev", "floor", "ceiling"])
        for row in _iter_lineup_rows("optimal", optimal_lineup):
            writer.writerow(row)

    with open(output_dir / "alternative_lineups.tsv", "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle, delimiter="\t")
        writer.writerow(["lineup", "slot", "name", "team", "ev", "floor", "ceiling"])
        for label, lineup in sorted(alternative_lineups.items()):
            for row in _iter_lineup_rows(label, lineup):
                writer.writerow(row)

    exposures: dict[str, int] = {}
    lineup_count = 1 + len(alternative_lineups)
    for row in _iter_lineup_rows("optimal", optimal_lineup):
        exposures[row[3]] = exposures.get(row[3], 0) + 1
    for label, lineup in sorted(alternative_lineups.items()):
        for row in _iter_lineup_rows(label, lineup):
            exposures[row[3]] = exposures.get(row[3], 0) + 1

    with open(output_dir / "team_exposure.tsv", "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle, delimiter="\t")
        writer.writerow(["team", "selections", "share"])
        for team_name, selections in sorted(exposures.items(), key=lambda item: (-item[1], item[0])):
            writer.writerow([team_name, selections, f"{selections / lineup_count:.3f}"])


def write_diagnostics(diagnostics: LoadDiagnostics, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "diagnostics.tsv"
    with open(output_path, "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle, delimiter="\t")
        writer.writerow(["metric", "value"])
        writer.writerow(["season_rows", diagnostics.season_rows])
        writer.writerow(["stretch_rows", diagnostics.stretch_rows])
        writer.writerow(["prev_rows", diagnostics.prev_rows])
        writer.writerow(["team_rows", diagnostics.team_rows])
        writer.writerow(["teams_loaded", diagnostics.teams_loaded])
        writer.writerow(["players_loaded", diagnostics.players_loaded])
        writer.writerow(["skipped_missing_stretch", diagnostics.skipped_missing_stretch])
        writer.writerow(["skipped_missing_team", diagnostics.skipped_missing_team])
        writer.writerow(["dropped_invalid_numeric", diagnostics.dropped_invalid_numeric])

        for reason, count in sorted(diagnostics.dropped_by_reason.items()):
            writer.writerow([f"dropped_reason:{reason}", count])

        for field_key, count in sorted(diagnostics.critical_missing_counts.items()):
            writer.writerow([f"missing_critical:{field_key}", count])
