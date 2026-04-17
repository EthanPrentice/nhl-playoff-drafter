from dataclasses import dataclass


@dataclass(frozen=True)
class TeamOddsInput:
    team: str
    round1: float
    round2: float
    conference: float
    final: float


@dataclass(frozen=True)
class SkaterProjectionInput:
    name: str
    team: str
    position: str
    season_gp: int
    season_p: int
    season_otg: int
    stretch_gp: int
    stretch_p: int
    stretch_otg: int
    prior_gp: int = 0
    prior_p: int = 0
    prior_otg: int = 0


@dataclass(frozen=True)
class GoalieTeamProjectionInput:
    team: str
    season_wins: int
    season_goaltender_assists: int
    season_shutouts: int
    team_odds: TeamOddsInput
