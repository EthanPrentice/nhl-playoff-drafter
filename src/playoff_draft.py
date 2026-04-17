from typing import Callable

import heuristics
from config import (
    EXPECTED_GAMES_METHOD,
    OUTPUT_DIR,
    PLAYER_PREV_SEASON_FILE,
    PLAYER_SEASON_FILE,
    PLAYER_STRETCH_FILE,
    RESOURCES_DIR,
    ROSTER,
    TEAM_FILE,
)
from data_loader import DataLoader, ResourceFiles
from models import estimate_expected_games, project_goalie_teams, project_skaters
from optimizer import LineupConstraints, optimize_lineup
from player import Player
from reporting import write_ranked_results
from team import Team


# HEURISTICS

def normalize_team_values(teams: list[Team], new_min=0.8, new_max=1.2):
    if not teams:
        return

    values = [team.estimatedValue for team in teams]
    min_val = min(values)
    max_val = max(values)

    if min_val == max_val:
        mid = (new_min + new_max) / 2
        for team in teams:
            team.estimatedValue = mid
        return

    scale = (new_max - new_min) / (max_val - min_val)
    for team in teams:
        team.estimatedValue = new_min + (team.estimatedValue - min_val) * scale


def set_team_estimated_values(teams: list[Team], players: list[Player], heuristic: Callable[[Team, list[Player]], float]):
    for team in teams:
        team.estimatedValue = heuristic(team, players)

    normalize_team_values(teams)
    teams.sort(key=lambda item: item.estimatedValue, reverse=True)


def set_player_estimated_values(players: list[Player], heuristic: Callable[[Player], float]):
    for player in players:
        player.estimatedValue = heuristic(player)

    players.sort(key=lambda item: item.estimatedValue, reverse=True)


def main():
    loader = DataLoader(
        resources_dir=RESOURCES_DIR,
        resource_files=ResourceFiles(
            teams_file=TEAM_FILE,
            player_season_file=PLAYER_SEASON_FILE,
            player_stretch_file=PLAYER_STRETCH_FILE,
            player_prev_season_file=PLAYER_PREV_SEASON_FILE,
        ),
        strict=False,
    )

    teams = loader.load_teams()
    players = loader.load_players(teams)

    set_team_estimated_values(teams, players, heuristics.get_team_weight_diff_penalty)
    set_player_estimated_values(players, heuristics.sum_team_odds_multiply_points_stretch_weighted_per_game)

    expected_games_stats = estimate_expected_games(loader.to_team_odds_inputs(teams), method=EXPECTED_GAMES_METHOD)
    expected_team_games = {team: stats.mean for team, stats in expected_games_stats.items()}
    skater_inputs = loader.to_skater_projection_inputs(players)
    goalie_team_inputs = loader.to_goalie_team_projection_inputs(teams)
    skater_projections = project_skaters(skater_inputs, expected_team_games)
    goalie_team_projections = project_goalie_teams(goalie_team_inputs, expected_team_games)

    lineup = optimize_lineup(
        forwards=[x for x in skater_projections if x.position == "F"],
        defense=[x for x in skater_projections if x.position == "D"],
        goalie_teams=goalie_team_projections,
        constraints=LineupConstraints(
            forwards=ROSTER.forwards,
            defense=ROSTER.defense,
            goalie_teams=ROSTER.goalie_teams,
        ),
    )

    write_ranked_results(teams, players, OUTPUT_DIR)

    print(loader.diagnostics_summary())
    print(
        f"optimized lineup sizes: F={len(lineup.forwards)}, D={len(lineup.defense)}, GT={len(lineup.goalie_teams)}"
    )
    print("SUCCESS")


if __name__ == "__main__":
    main()
