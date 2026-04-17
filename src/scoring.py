
def skater_points_raw(goals: int, assists: int, ot_goals: int) -> float:
    return float(goals + assists + ot_goals)


def skater_points_from_summary(points: int, ot_goals: int) -> float:
    return float(points + ot_goals)


def goalie_team_points_raw(wins: int, assists: int, shutouts: int) -> float:
    return float(wins + assists + (5 * shutouts))


def rate_per_game(total_points: float, games_played: int) -> float:
    if games_played <= 0:
        return 0.0
    return float(total_points) / games_played


def blend_rates(season_rate: float, stretch_rate: float, stretch_gp: int, k: int) -> float:
    if stretch_gp <= 0:
        return season_rate

    weight = stretch_gp / (stretch_gp + k)
    return (weight * stretch_rate) + ((1 - weight) * season_rate)
