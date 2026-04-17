import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import DEFAULT_SERIES_LENGTHS, TuningConfig
from tuning import passes_primary_metric_gate, weighted_validation_score


class TuningHelpersTests(unittest.TestCase):
    def test_weighted_validation_score(self):
        score = weighted_validation_score(lineup_delta=4.0, spearman=0.5, rmse=2.0)
        self.assertAlmostEqual(score, 2.475)

    def test_primary_metric_gate(self):
        self.assertTrue(passes_primary_metric_gate([0.1, 0.2], [0.0, 0.4]))
        self.assertFalse(passes_primary_metric_gate([-0.1, 0.2], [0.1, 0.2]))

    def test_tuning_config_stable_id(self):
        a = TuningConfig(
            method="analytic",
            stretch_shrinkage_k=20,
            min_stretch_gp_for_direct_weight=10,
            risk_lambda=0.1,
            max_skaters_per_team=3,
            max_total_from_team_including_goalie_team=4,
            series_lengths=DEFAULT_SERIES_LENGTHS,
            monte_carlo_simulations=20000,
        )
        b = TuningConfig(
            method="analytic",
            stretch_shrinkage_k=20,
            min_stretch_gp_for_direct_weight=10,
            risk_lambda=0.1,
            max_skaters_per_team=3,
            max_total_from_team_including_goalie_team=4,
            series_lengths=DEFAULT_SERIES_LENGTHS,
            monte_carlo_simulations=20000,
        )
        self.assertEqual(a.stable_id(), b.stable_id())


if __name__ == "__main__":
    unittest.main()
