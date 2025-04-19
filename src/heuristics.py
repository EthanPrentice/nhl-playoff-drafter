from player import Player
from team import Team

# TEAM
def get_team_odds_direct_sum(team: Team):
    return sum([
        team.odds.round1,
        team.odds.round2 / team.odds.round1,
        team.odds.conference / team.odds.round2
    ])


def get_team_odds_real_sum(team: Team):
    return sum([
        team.odds.round1,
        team.odds.round2 / team.odds.round1,
        team.odds.conference / team.odds.round2
    ])


def get_team_weight_diff(team: Team):
    weights = [3, 1, 1]
    odds = [team.odds.round1, team.odds.round2, team.odds.conference]

    result = 0
    for i in range(len(odds)):
        if i > 0:
            result += odds[i] / odds[i - 1] / 0.5 * weights[i]
        else:
             result += odds[i] / 0.5 * weights[i]
    
    return result / sum(weights)


def get_team_weight_diff_penalty(team: Team):
    weights = [2, 1, 1]
    odds = [team.odds.round1, team.odds.round2, team.odds.conference]

    result = 0
    for i in range(len(odds)):
        independent_odds = odds[i] / odds[i - 1] if i > 0 else odds[i]

        mid_dist = abs(independent_odds - 0.5)
        if mid_dist < 0.05:
            independent_odds -= 0.1 * (1 - mid_dist / 0.05)  # penalty for being risky
        
        result += independent_odds / 0.5 * weights[i]
    
    return result / sum(weights)

# PLAYER
def sum_team_odds_multiply_points(player: Player) -> float:
    return player.team.estimatedValue * player.seasonStats.points * 82 / player.seasonStats.games_played


def sum_team_odds_multiply_points_stretch_weighted(player: Player) -> float:
    return player.team.estimatedValue * (0.3 * player.seasonStats.points + 0.7 * player.stretchStats.points)


def sum_team_odds_multiply_points_stretch_weighted_per_game(player: Player) -> float:
    seasonEV = player.seasonStats.points * 82 / player.seasonStats.games_played
    stretchEV = (player.stretchStats.points * 30.5 / player.stretchStats.games_played) * 82 / 30.5

    if player.stretchStats.games_played <= 10:
        return player.team.estimatedValue * seasonEV
    else:
        return player.team.estimatedValue * (0.3 * seasonEV + 0.7 * stretchEV)


def sum_team_odds_multiply_points_esp_stretch_weighted_per_game(player: Player) -> float:
    seasonEV = (player.seasonStats.points * 0.85 + player.seasonStats.even_strength_points * 0.15) * 82 / player.seasonStats.games_played

    stretchEV = player.stretchStats.points * 0.85 + player.stretchStats.even_strength_points * 0.15
    stretchEV = (stretchEV * 30.5 / player.stretchStats.games_played) * 82 / 30.5

    if player.stretchStats.games_played <= 10:
        return player.team.estimatedValue * seasonEV
    else:
        return player.team.estimatedValue * (0.3 * seasonEV + 0.7 * stretchEV)