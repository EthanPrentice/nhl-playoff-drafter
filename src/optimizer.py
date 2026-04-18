from dataclasses import dataclass
from typing import Iterable

from models import GoalieTeamProjection, SkaterProjection


@dataclass(frozen=True)
class LineupConstraints:
    forwards: int = 5
    defense: int = 3
    goalie_teams: int = 2
    max_skaters_per_team: int | None = None
    max_total_from_team_including_goalie_team: int | None = None


@dataclass(frozen=True)
class OptimizedLineup:
    forwards: list[SkaterProjection]
    defense: list[SkaterProjection]
    goalie_teams: list[GoalieTeamProjection]
    objective_value: float


def _stable_skater_key(skater: SkaterProjection) -> tuple[str, str, str]:
    return (skater.team, skater.position, skater.name)


def _stable_goalie_team_key(goalie_team: GoalieTeamProjection) -> tuple[str]:
    return (goalie_team.team,)


def _score_skater(skater: SkaterProjection, risk_lambda: float) -> float:
    return skater.expected_points - (risk_lambda * skater.expected_points_std)


def _score_goalie_team(goalie_team: GoalieTeamProjection, risk_lambda: float) -> float:
    return goalie_team.expected_points - (risk_lambda * goalie_team.expected_points_std)


def _objective(
    selected_forwards: Iterable[SkaterProjection],
    selected_defense: Iterable[SkaterProjection],
    selected_goalie_teams: Iterable[GoalieTeamProjection],
    risk_lambda: float,
) -> float:
    total = sum(_score_skater(x, risk_lambda) for x in selected_forwards)
    total += sum(_score_skater(x, risk_lambda) for x in selected_defense)
    total += sum(_score_goalie_team(x, risk_lambda) for x in selected_goalie_teams)
    return total


def _respects_optional_team_constraints(
    selected_forwards: tuple[SkaterProjection, ...],
    selected_defense: tuple[SkaterProjection, ...],
    selected_goalie_teams: tuple[GoalieTeamProjection, ...],
    constraints: LineupConstraints,
) -> bool:
    if constraints.max_skaters_per_team is not None:
        skaters_per_team: dict[str, int] = {}
        for skater in (*selected_forwards, *selected_defense):
            skaters_per_team[skater.team] = skaters_per_team.get(skater.team, 0) + 1
        if any(count > constraints.max_skaters_per_team for count in skaters_per_team.values()):
            return False

    if constraints.max_total_from_team_including_goalie_team is not None:
        total_per_team: dict[str, int] = {}
        for skater in (*selected_forwards, *selected_defense):
            total_per_team[skater.team] = total_per_team.get(skater.team, 0) + 1
        for goalie_team in selected_goalie_teams:
            total_per_team[goalie_team.team] = total_per_team.get(goalie_team.team, 0) + 1
        if any(count > constraints.max_total_from_team_including_goalie_team for count in total_per_team.values()):
            return False

    return True


def _validate_pool_sizes(
    forwards: list[SkaterProjection],
    defense: list[SkaterProjection],
    goalie_teams: list[GoalieTeamProjection],
    constraints: LineupConstraints,
) -> None:
    if len(forwards) < constraints.forwards:
        raise ValueError(f"Not enough forwards to satisfy roster constraint: need {constraints.forwards}, got {len(forwards)}")
    if len(defense) < constraints.defense:
        raise ValueError(f"Not enough defense to satisfy roster constraint: need {constraints.defense}, got {len(defense)}")
    if len(goalie_teams) < constraints.goalie_teams:
        raise ValueError(
            f"Not enough goalie teams to satisfy roster constraint: need {constraints.goalie_teams}, got {len(goalie_teams)}"
        )


def _optimize_without_cross_pool_constraints(
    forwards: list[SkaterProjection],
    defense: list[SkaterProjection],
    goalie_teams: list[GoalieTeamProjection],
    constraints: LineupConstraints,
    risk_lambda: float,
) -> OptimizedLineup:
    selected_forwards = sorted(forwards, key=lambda x: (-_score_skater(x, risk_lambda), _stable_skater_key(x)))[: constraints.forwards]
    selected_defense = sorted(defense, key=lambda x: (-_score_skater(x, risk_lambda), _stable_skater_key(x)))[: constraints.defense]
    selected_goalie_teams = sorted(
        goalie_teams, key=lambda x: (-_score_goalie_team(x, risk_lambda), _stable_goalie_team_key(x))
    )[: constraints.goalie_teams]

    return OptimizedLineup(
        forwards=selected_forwards,
        defense=selected_defense,
        goalie_teams=selected_goalie_teams,
        objective_value=_objective(selected_forwards, selected_defense, selected_goalie_teams, risk_lambda),
    )


def _optimize_with_optional_constraints(
    forwards: list[SkaterProjection],
    defense: list[SkaterProjection],
    goalie_teams: list[GoalieTeamProjection],
    constraints: LineupConstraints,
    risk_lambda: float,
) -> OptimizedLineup:
    """
    Fast constrained selection path.

    NOTE: the previous exhaustive combinatorial search was exact but could be
    intractable for realistic pools (e.g. 135F/47D/13G). This greedy approach
    is deterministic and bounded, which keeps tuning runs from stalling when
    exposure-cap constraints are enabled.
    """
    sorted_forwards = sorted(forwards, key=lambda x: (-_score_skater(x, risk_lambda), _stable_skater_key(x)))
    sorted_defense = sorted(defense, key=lambda x: (-_score_skater(x, risk_lambda), _stable_skater_key(x)))
    sorted_goalie_teams = sorted(
        goalie_teams, key=lambda x: (-_score_goalie_team(x, risk_lambda), _stable_goalie_team_key(x))
    )

    skaters_per_team: dict[str, int] = {}
    total_per_team: dict[str, int] = {}

    def _can_add_skater(team: str) -> bool:
        if constraints.max_skaters_per_team is not None and skaters_per_team.get(team, 0) >= constraints.max_skaters_per_team:
            return False
        if (
            constraints.max_total_from_team_including_goalie_team is not None
            and total_per_team.get(team, 0) >= constraints.max_total_from_team_including_goalie_team
        ):
            return False
        return True

    def _can_add_goalie(team: str) -> bool:
        if (
            constraints.max_total_from_team_including_goalie_team is not None
            and total_per_team.get(team, 0) >= constraints.max_total_from_team_including_goalie_team
        ):
            return False
        return True

    selected_goalie_teams: list[GoalieTeamProjection] = []
    for goalie_team in sorted_goalie_teams:
        if not _can_add_goalie(goalie_team.team):
            continue
        selected_goalie_teams.append(goalie_team)
        total_per_team[goalie_team.team] = total_per_team.get(goalie_team.team, 0) + 1
        if len(selected_goalie_teams) == constraints.goalie_teams:
            break
    if len(selected_goalie_teams) < constraints.goalie_teams:
        raise ValueError("No feasible goalie-team selection satisfies the provided constraints")

    selected_forwards: list[SkaterProjection] = []
    for skater in sorted_forwards:
        if not _can_add_skater(skater.team):
            continue
        selected_forwards.append(skater)
        skaters_per_team[skater.team] = skaters_per_team.get(skater.team, 0) + 1
        total_per_team[skater.team] = total_per_team.get(skater.team, 0) + 1
        if len(selected_forwards) == constraints.forwards:
            break
    if len(selected_forwards) < constraints.forwards:
        raise ValueError("No feasible forward selection satisfies the provided constraints")

    selected_defense: list[SkaterProjection] = []
    for skater in sorted_defense:
        if not _can_add_skater(skater.team):
            continue
        selected_defense.append(skater)
        skaters_per_team[skater.team] = skaters_per_team.get(skater.team, 0) + 1
        total_per_team[skater.team] = total_per_team.get(skater.team, 0) + 1
        if len(selected_defense) == constraints.defense:
            break
    if len(selected_defense) < constraints.defense:
        raise ValueError("No feasible defense selection satisfies the provided constraints")

    if not _respects_optional_team_constraints(
        selected_forwards=tuple(selected_forwards),
        selected_defense=tuple(selected_defense),
        selected_goalie_teams=tuple(selected_goalie_teams),
        constraints=constraints,
    ):
        raise ValueError("No feasible lineup satisfies the provided constraints")

    return OptimizedLineup(
        forwards=selected_forwards,
        defense=selected_defense,
        goalie_teams=selected_goalie_teams,
        objective_value=_objective(selected_forwards, selected_defense, selected_goalie_teams, risk_lambda),
    )


def optimize_lineup(
    forwards: list[SkaterProjection],
    defense: list[SkaterProjection],
    goalie_teams: list[GoalieTeamProjection],
    constraints: LineupConstraints,
    risk_lambda: float = 0.0,
) -> OptimizedLineup:
    _validate_pool_sizes(forwards, defense, goalie_teams, constraints)

    has_optional_team_constraints = (
        constraints.max_skaters_per_team is not None or constraints.max_total_from_team_including_goalie_team is not None
    )
    if not has_optional_team_constraints:
        return _optimize_without_cross_pool_constraints(forwards, defense, goalie_teams, constraints, risk_lambda)

    return _optimize_with_optional_constraints(forwards, defense, goalie_teams, constraints, risk_lambda)
