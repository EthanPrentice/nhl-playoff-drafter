from dataclasses import dataclass

from config import STRETCH_SHRINKAGE_K
from contracts import GoalieTeamProjectionInput, SkaterProjectionInput
from scoring import blend_rates, goalie_team_points_raw, rate_per_game, skater_points_from_summary


@dataclass(frozen=True)
class SkaterProjection:
    name: str
    team: str
    position: str
    expected_points: float


@dataclass(frozen=True)
class GoalieTeamProjection:
    team: str
    expected_points: float


def project_skaters(inputs: list[SkaterProjectionInput], expected_team_games: dict[str, float]) -> list[SkaterProjection]:
    projections: list[SkaterProjection] = []
    for item in inputs:
        season_rate = rate_per_game(skater_points_from_summary(item.season_p, item.season_otg), item.season_gp)
        stretch_rate = rate_per_game(skater_points_from_summary(item.stretch_p, item.stretch_otg), item.stretch_gp)
        blended_rate = blend_rates(season_rate, stretch_rate, item.stretch_gp, STRETCH_SHRINKAGE_K)
        projections.append(
            SkaterProjection(
                name=item.name,
                team=item.team,
                position=item.position,
                expected_points=blended_rate * expected_team_games.get(item.team, 0.0),
            )
        )
    return projections


def project_goalie_teams(inputs: list[GoalieTeamProjectionInput], expected_team_games: dict[str, float]) -> list[GoalieTeamProjection]:
    projections: list[GoalieTeamProjection] = []
    for item in inputs:
        per_game = rate_per_game(
            goalie_team_points_raw(item.season_wins, item.season_goaltender_assists, item.season_shutouts),
            82,
        )
        projections.append(
            GoalieTeamProjection(team=item.team, expected_points=per_game * expected_team_games.get(item.team, 0.0))
        )
    return projections
