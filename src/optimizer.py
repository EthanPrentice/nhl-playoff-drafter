from dataclasses import dataclass

from models import GoalieTeamProjection, SkaterProjection


@dataclass(frozen=True)
class LineupConstraints:
    forwards: int = 5
    defense: int = 3
    goalie_teams: int = 2


@dataclass(frozen=True)
class OptimizedLineup:
    forwards: list[SkaterProjection]
    defense: list[SkaterProjection]
    goalie_teams: list[GoalieTeamProjection]


def optimize_lineup(
    skaters: list[SkaterProjection],
    goalie_teams: list[GoalieTeamProjection],
    constraints: LineupConstraints,
) -> OptimizedLineup:
    forwards = sorted((x for x in skaters if x.position == "F"), key=lambda x: x.expected_points, reverse=True)[: constraints.forwards]
    defense = sorted((x for x in skaters if x.position == "D"), key=lambda x: x.expected_points, reverse=True)[: constraints.defense]
    selected_goalie_teams = sorted(goalie_teams, key=lambda x: x.expected_points, reverse=True)[: constraints.goalie_teams]
    return OptimizedLineup(forwards=forwards, defense=defense, goalie_teams=selected_goalie_teams)
