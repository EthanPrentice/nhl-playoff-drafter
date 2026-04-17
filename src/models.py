from __future__ import annotations

import math
import random
from dataclasses import dataclass

from config import (
    EXPECTED_GAMES_METHOD,
    EXPECTED_GAMES_MONTE_CARLO_SIMULATIONS,
    EXPECTED_SERIES_LENGTH_R1,
    EXPECTED_SERIES_LENGTH_R2,
    EXPECTED_SERIES_LENGTH_R3,
    EXPECTED_SERIES_LENGTH_R4,
    MIN_STRETCH_GP_FOR_DIRECT_WEIGHT,
    STRETCH_SHRINKAGE_K,
)
from contracts import GoalieTeamProjectionInput, SkaterProjectionInput, TeamOddsInput
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


@dataclass(frozen=True)
class ExpectedGamesResult:
    mean: float
    std: float
    p10: float
    p90: float


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return max(0.0, min(1.0, numerator / denominator))


def _independent_round_probabilities(team_odds: TeamOddsInput) -> tuple[float, float, float, float]:
    p1 = max(0.0, min(1.0, team_odds.round1))
    p2 = _safe_ratio(team_odds.round2, team_odds.round1)
    p3 = _safe_ratio(team_odds.conference, team_odds.round2)
    p4 = _safe_ratio(team_odds.final, team_odds.conference)
    return p1, p2, p3, p4


def expected_games_analytic(team_odds: TeamOddsInput) -> ExpectedGamesResult:
    p1, p2, p3, _ = _independent_round_probabilities(team_odds)

    expected_games = (
        EXPECTED_SERIES_LENGTH_R1
        + (p1 * EXPECTED_SERIES_LENGTH_R2)
        + (p1 * p2 * EXPECTED_SERIES_LENGTH_R3)
        + (p1 * p2 * p3 * EXPECTED_SERIES_LENGTH_R4)
    )

    return ExpectedGamesResult(mean=expected_games, std=0.0, p10=expected_games, p90=expected_games)


def _sample_series_length(rand: random.Random) -> int:
    # Lightweight empirical prior for playoff series length.
    roll = rand.random()
    if roll < 0.20:
        return 4
    if roll < 0.45:
        return 5
    if roll < 0.75:
        return 6
    return 7


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0

    rank = percentile * (len(sorted_values) - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))

    if lower == upper:
        return sorted_values[lower]

    fraction = rank - lower
    return sorted_values[lower] + ((sorted_values[upper] - sorted_values[lower]) * fraction)


def expected_games_monte_carlo(
    team_odds: TeamOddsInput,
    simulations: int = EXPECTED_GAMES_MONTE_CARLO_SIMULATIONS,
    seed: int = 0,
) -> ExpectedGamesResult:
    if simulations <= 0:
        raise ValueError("simulations must be > 0")

    p1, p2, p3, _ = _independent_round_probabilities(team_odds)
    rand = random.Random(seed)
    totals: list[float] = []

    for _ in range(simulations):
        total_games = float(_sample_series_length(rand))

        if rand.random() < p1:
            total_games += _sample_series_length(rand)
            if rand.random() < p2:
                total_games += _sample_series_length(rand)
                if rand.random() < p3:
                    total_games += _sample_series_length(rand)

        totals.append(total_games)

    totals.sort()
    mean = sum(totals) / len(totals)
    variance = sum((value - mean) ** 2 for value in totals) / len(totals)

    return ExpectedGamesResult(
        mean=mean,
        std=math.sqrt(variance),
        p10=_percentile(totals, 0.10),
        p90=_percentile(totals, 0.90),
    )


def estimate_expected_games(
    team_odds_inputs: list[TeamOddsInput],
    method: str = EXPECTED_GAMES_METHOD,
) -> dict[str, ExpectedGamesResult]:
    results: dict[str, ExpectedGamesResult] = {}
    for item in team_odds_inputs:
        if method == "monte_carlo":
            try:
                result = expected_games_monte_carlo(item)
            except Exception:
                result = expected_games_analytic(item)
        else:
            result = expected_games_analytic(item)
        results[item.team] = result
    return results


def project_skaters(inputs: list[SkaterProjectionInput], expected_team_games: dict[str, float]) -> list[SkaterProjection]:
    projections: list[SkaterProjection] = []
    for item in inputs:
        season_rate = rate_per_game(skater_points_from_summary(item.season_p, item.season_otg), item.season_gp)
        stretch_rate = rate_per_game(skater_points_from_summary(item.stretch_p, item.stretch_otg), item.stretch_gp)
        if item.stretch_gp < MIN_STRETCH_GP_FOR_DIRECT_WEIGHT:
            blended_rate = season_rate
        else:
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
