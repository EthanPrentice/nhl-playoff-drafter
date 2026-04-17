import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import (
    DEFAULT_SERIES_LENGTHS,
    EXPECTED_GAMES_METHOD,
    EXPECTED_GAMES_MONTE_CARLO_SIMULATIONS,
    EXPECTED_SERIES_LENGTH_R1,
    EXPECTED_SERIES_LENGTH_R2,
    EXPECTED_SERIES_LENGTH_R3,
    EXPECTED_SERIES_LENGTH_R4,
    MIN_STRETCH_GP_FOR_DIRECT_WEIGHT,
    RISK_LAMBDA,
    ROSTER,
    SCORING,
    STRETCH_SHRINKAGE_K,
    TUNING_BASELINE,
    TUNING_GRID,
)


class ConfigDefaultsTests(unittest.TestCase):
    def test_scoring_defaults(self):
        self.assertEqual(SCORING.skater_goal, 1)
        self.assertEqual(SCORING.skater_assist, 1)
        self.assertEqual(SCORING.skater_ot_goal_bonus, 1)
        self.assertEqual(SCORING.goalie_win, 1)
        self.assertEqual(SCORING.goalie_assist, 1)
        self.assertEqual(SCORING.goalie_shutout, 5)

    def test_roster_defaults(self):
        self.assertEqual(ROSTER.forwards, 5)
        self.assertEqual(ROSTER.defense, 3)
        self.assertEqual(ROSTER.goalie_teams, 2)

    def test_stretch_tunables_defaults(self):
        self.assertEqual(STRETCH_SHRINKAGE_K, 35)
        self.assertEqual(MIN_STRETCH_GP_FOR_DIRECT_WEIGHT, 10)
        self.assertEqual(RISK_LAMBDA, 0.2)

    def test_expected_games_defaults(self):
        self.assertEqual(EXPECTED_GAMES_METHOD, "monte_carlo")
        self.assertEqual(EXPECTED_GAMES_MONTE_CARLO_SIMULATIONS, 20_000)
        self.assertEqual(EXPECTED_SERIES_LENGTH_R1, 5.7)
        self.assertEqual(EXPECTED_SERIES_LENGTH_R2, 5.8)
        self.assertEqual(EXPECTED_SERIES_LENGTH_R3, 5.9)
        self.assertEqual(EXPECTED_SERIES_LENGTH_R4, 6.0)

    def test_tuning_manifest_defaults(self):
        self.assertEqual(TUNING_BASELINE.method, EXPECTED_GAMES_METHOD)
        self.assertEqual(TUNING_BASELINE.stretch_shrinkage_k, STRETCH_SHRINKAGE_K)
        self.assertEqual(TUNING_BASELINE.min_stretch_gp_for_direct_weight, MIN_STRETCH_GP_FOR_DIRECT_WEIGHT)
        self.assertEqual(TUNING_BASELINE.risk_lambda, RISK_LAMBDA)
        self.assertEqual(TUNING_BASELINE.series_lengths, DEFAULT_SERIES_LENGTHS)
        self.assertEqual(TUNING_BASELINE.stable_id(), "c2704b84ad8e")
        self.assertGreater(len(TUNING_GRID.methods), 0)
        self.assertGreater(len(TUNING_GRID.series_length_profiles), 0)


if __name__ == "__main__":
    unittest.main()
