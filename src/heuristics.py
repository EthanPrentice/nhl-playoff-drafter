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

# PLAYER

def sum_team_odds_multiply_points(player: Player) -> float:
    return player.team.estimatedValue * player.seasonStats.points


def sum_team_odds_multiply_points_stretch_weighted(player: Player) -> float:
    return player.team.estimatedValue * (0.3 * player.seasonStats.points + 0.7 * player.stretchStats.points)
