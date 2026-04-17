from player import Player, PlayerStats
from team import Team

# TEAM
def get_team_odds_2024(team: Team, players: list[Player]):
    return sum([
        team.odds.round1,
        team.odds.round2,
        team.odds.conference
    ])

def get_player_odds_2024(player: Player):
    return player.seasonStats.points * player.team.estimatedValue


def get_team_odds_direct_sum(team: Team, players: list[Player]):
    return sum([
        team.odds.round1,
        team.odds.round2 / team.odds.round1,
        team.odds.conference / team.odds.round2
    ])


def get_team_odds_real_sum(team: Team, players: list[Player]):
    return sum([
        team.odds.round1,
        team.odds.round2 / team.odds.round1,
        team.odds.conference / team.odds.round2
    ])


def get_team_weight_diff(team: Team, players: list[Player]):
    weights = [3, 1, 1]
    odds = [team.odds.round1, team.odds.round2, team.odds.conference]

    result = 0
    for i in range(len(odds)):
        if i > 0:
            result += odds[i] / odds[i - 1] / 0.5 * weights[i]
        else:
             result += odds[i] / 0.5 * weights[i]
    
    return result / sum(weights)


def get_team_weight_diff_penalty(team: Team, players: list[Player]):
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


# TOTAL SEASON TEAM HEURISTICS
def get_team_weight_all_players(team: Team, players: list[Player]) -> float:
    team_players = filter(lambda x: x.team.name == team.name, players)
    # take top 12 players since it is a smaller league
    team_players_ev = sorted(map(lambda x: x.estimatedValue, team_players), reverse=True)[:12]
    return sum(team_players_ev)


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


def yahoo_default_single(playerStats: PlayerStats) -> float:
    value_sum = 0.0
    value_sum += 3 * playerStats.goals
    value_sum += 2 * playerStats.assists
    value_sum += 0.5 * playerStats.plus_minus
    value_sum += 2 * (playerStats.points - playerStats.even_strength_points)
    value_sum += 0.5 * playerStats.shots
    value_sum += 0.5 * playerStats.blocks
    value_sum += 0.5 * playerStats.hits
    return value_sum


def yahoo_default(player: Player) -> float:
    if player.position == "F" or player.position == "D":
        return yahoo_default_single(player.seasonStats)
    else:       # player.position == "G"
        pass    # fill in if we get goalie stats


def yahoo_default_with_past(player: Player) -> float:
    value_sum = 0.0
    if player.position == "F" or player.position == "D":
        value_sum += 0.7 * yahoo_default_single(player.seasonStats)
        value_sum += 0.3 * yahoo_default_single(player.prevSeasonStats)
    else:       # player.position == "G"
        pass    # fill in if we get goalie stats
    return value_sum
