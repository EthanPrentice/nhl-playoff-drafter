from dataclasses import dataclass
from hashlib import sha1
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


@dataclass(frozen=True)
class SeriesLengthConfig:
    round1: float = 5.9
    round2: float = 5.9
    round3: float = 5.9
    round4: float = 5.9


@dataclass(frozen=True)
class TuningConfig:
    method: str
    stretch_shrinkage_k: int
    min_stretch_gp_for_direct_weight: int
    risk_lambda: float
    max_skaters_per_team: int | None
    max_total_from_team_including_goalie_team: int | None
    series_lengths: SeriesLengthConfig
    monte_carlo_simulations: int

    def stable_id(self) -> str:
        payload = (
            f"m={self.method}|k={self.stretch_shrinkage_k}|min_gp={self.min_stretch_gp_for_direct_weight}|"
            f"risk={self.risk_lambda:.4f}|max_skaters={self.max_skaters_per_team}|"
            f"max_total={self.max_total_from_team_including_goalie_team}|"
            f"series={self.series_lengths.round1:.2f},{self.series_lengths.round2:.2f},"
            f"{self.series_lengths.round3:.2f},{self.series_lengths.round4:.2f}|"
            f"mc={self.monte_carlo_simulations}"
        )
        return sha1(payload.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class TuningGrid:
    methods: tuple[str, ...]
    shrinkage_k_values: tuple[int, ...]
    min_stretch_gp_values: tuple[int, ...]
    risk_lambda_values: tuple[float, ...]
    max_skaters_per_team_values: tuple[int | None, ...]
    max_total_from_team_values: tuple[int | None, ...]
    series_length_profiles: tuple[SeriesLengthConfig, ...]
    coarse_monte_carlo_simulations: int
    refine_monte_carlo_simulations: int
    coarse_top_k: int
    refinement_top_k: int


ROOT_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = ROOT_DIR / "resources" / "2026"
OUTPUT_DIR = ROOT_DIR / "out" / "season_2026"

PLAYER_SEASON_FILE = "players_season.tsv"
PLAYER_STRETCH_FILE = "players_stretch.tsv"
PLAYER_PREV_SEASON_FILE = "players_prev_season.tsv"
TEAM_FILE = "teams.tsv"

SCORING = ScoringConfig()
ROSTER = RosterConfig()

STRETCH_SHRINKAGE_K = 35
MIN_STRETCH_GP_FOR_DIRECT_WEIGHT = 10
RISK_LAMBDA = 0.2

EXPECTED_GAMES_METHOD = "monte_carlo"
EXPECTED_GAMES_MONTE_CARLO_SIMULATIONS = 20_000
EXPECTED_SERIES_LENGTH_R1 = 5.7
EXPECTED_SERIES_LENGTH_R2 = 5.8
EXPECTED_SERIES_LENGTH_R3 = 5.9
EXPECTED_SERIES_LENGTH_R4 = 6.0

DEFAULT_SERIES_LENGTHS = SeriesLengthConfig(
    round1=EXPECTED_SERIES_LENGTH_R1,
    round2=EXPECTED_SERIES_LENGTH_R2,
    round3=EXPECTED_SERIES_LENGTH_R3,
    round4=EXPECTED_SERIES_LENGTH_R4,
)

TUNING_BASELINE = TuningConfig(
    method=EXPECTED_GAMES_METHOD,
    stretch_shrinkage_k=STRETCH_SHRINKAGE_K,
    min_stretch_gp_for_direct_weight=MIN_STRETCH_GP_FOR_DIRECT_WEIGHT,
    risk_lambda=RISK_LAMBDA,
    max_skaters_per_team=None,
    max_total_from_team_including_goalie_team=None,
    series_lengths=DEFAULT_SERIES_LENGTHS,
    monte_carlo_simulations=EXPECTED_GAMES_MONTE_CARLO_SIMULATIONS,
)

TUNING_GRID = TuningGrid(
    methods=("analytic", "monte_carlo"),
    shrinkage_k_values=(10, 20, 30, 40),
    min_stretch_gp_values=(6, 10, 14),
    risk_lambda_values=(0.0, 0.1, 0.2),
    max_skaters_per_team_values=(None, 3),
    max_total_from_team_values=(None, 3, 4),
    series_length_profiles=(
        DEFAULT_SERIES_LENGTHS,
        SeriesLengthConfig(round1=5.7, round2=5.8, round3=5.9, round4=6.0),
        SeriesLengthConfig(round1=6.0, round2=6.0, round3=6.1, round4=6.1),
    ),
    coarse_monte_carlo_simulations=3000,
    refine_monte_carlo_simulations=20000,
    coarse_top_k=8,
    refinement_top_k=3,
)
