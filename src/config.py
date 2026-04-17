from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScoringConfig:
    skater_goal: int = 1
    skater_assist: int = 1
    skater_ot_goal_bonus: int = 1
    goalie_win: int = 1
    goalie_assist: int = 1
    goalie_shutout: int = 5


@dataclass(frozen=True)
class RosterConfig:
    forwards: int = 5
    defense: int = 3
    goalie_teams: int = 2


ROOT_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = ROOT_DIR / "resources" / "2026"
OUTPUT_DIR = ROOT_DIR / "out" / "season_2026"

PLAYER_SEASON_FILE = "players_season.tsv"
PLAYER_STRETCH_FILE = "players_stretch.tsv"
PLAYER_PREV_SEASON_FILE = "players_prev_season.tsv"
TEAM_FILE = "teams.tsv"

SCORING = ScoringConfig()
ROSTER = RosterConfig()

STRETCH_SHRINKAGE_K = 20
DEFAULT_EXPECTED_TEAM_GAMES = 6.0
