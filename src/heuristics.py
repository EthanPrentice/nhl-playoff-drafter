from player import Player


def sum_team_odds_multiply_points(player: Player) -> float:
    team_odds = player.team.odds
    team_weight = team_odds.round1 + team_odds.round2 + team_odds.conference + team_odds.final

    return team_weight * player.seasonStats.points


def sum_team_odds_multiply_points_stretch_weighted(player: Player) -> float:
    team_odds = player.team.odds
    team_weight = team_odds.round1 + team_odds.round2 + team_odds.conference + team_odds.final

    return team_weight * (0.3 * player.seasonStats.points + 0.7 * player.stretchStats.points)
