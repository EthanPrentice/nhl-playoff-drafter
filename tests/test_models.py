import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from contracts import SkaterProjectionInput, TeamOddsInput
from models import (
    estimate_expected_games,
    expected_games_analytic,
    expected_games_monte_carlo,
    project_skaters,
)


class ModelsTests(unittest.TestCase):
    def test_small_stretch_sample_uses_season_rate(self):
        projections = project_skaters(
            [
                SkaterProjectionInput(
                    name="A",
                    team="AAA",
                    position="F",
                    season_gp=82,
                    season_p=82,
                    season_otg=0,
                    stretch_gp=5,
                    stretch_p=25,
                    stretch_otg=0,
                )
            ],
            expected_team_games={"AAA": 6.0},
        )

        self.assertEqual(len(projections), 1)
        self.assertAlmostEqual(projections[0].expected_points, 6.0)

    def test_expected_games_analytic_monotonicity(self):
        weak = TeamOddsInput(team="WEAK", round1=0.40, round2=0.15, conference=0.06, final=0.02)
        strong = TeamOddsInput(team="STRONG", round1=0.70, round2=0.40, conference=0.22, final=0.11)

        weak_games = expected_games_analytic(weak)
        strong_games = expected_games_analytic(strong)

        self.assertGreater(strong_games.mean, weak_games.mean)
        self.assertGreater(weak_games.p90, weak_games.p10)
        self.assertGreater(strong_games.p90, strong_games.p10)
        self.assertGreater(weak_games.std, 0)
        self.assertGreater(strong_games.std, 0)

    def test_expected_games_monte_carlo_outputs_distribution(self):
        team = TeamOddsInput(team="AAA", round1=0.60, round2=0.30, conference=0.15, final=0.08)
        result = expected_games_monte_carlo(team, simulations=1500, seed=42)

        self.assertGreater(result.mean, 0)
        self.assertGreaterEqual(result.std, 0)
        self.assertGreaterEqual(result.p10, 4)
        self.assertLessEqual(result.p90, 28)
        self.assertGreaterEqual(result.p90, result.p10)

    def test_selector_falls_back_to_analytic_for_unknown_method(self):
        team = TeamOddsInput(team="AAA", round1=0.60, round2=0.30, conference=0.15, final=0.08)
        analytic = expected_games_analytic(team)

        selected = estimate_expected_games([team], method="not-a-method")

        self.assertAlmostEqual(selected["AAA"].mean, analytic.mean)


if __name__ == "__main__":
    unittest.main()
