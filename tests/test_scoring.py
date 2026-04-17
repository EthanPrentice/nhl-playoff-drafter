import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from scoring import (
    blend_rates,
    goalie_team_points_raw,
    rate_per_game,
    skater_points_from_summary,
    skater_points_raw,
)


class ScoringTests(unittest.TestCase):
    def test_skater_points_formula(self):
        self.assertEqual(skater_points_raw(goals=30, assists=40, ot_goals=4), 74.0)
        self.assertEqual(skater_points_from_summary(points=70, ot_goals=4), 74.0)

    def test_skater_points_missing_otg_defaults_to_zero(self):
        self.assertEqual(skater_points_raw(goals=30, assists=40, ot_goals=None), 70.0)
        self.assertEqual(skater_points_from_summary(points=70, ot_goals=None), 70.0)

    def test_goalie_team_formula(self):
        self.assertEqual(goalie_team_points_raw(wins=40, assists=10, shutouts=4), 70.0)

    def test_rate_per_game_handles_zero_games(self):
        self.assertEqual(rate_per_game(total_points=10, games_played=0), 0.0)

    def test_blend_rates(self):
        self.assertAlmostEqual(blend_rates(season_rate=1.0, stretch_rate=2.0, stretch_gp=20, k=20), 1.5)

    def test_blend_rates_with_non_positive_shrinkage(self):
        self.assertEqual(blend_rates(season_rate=1.0, stretch_rate=2.0, stretch_gp=20, k=0), 2.0)


if __name__ == "__main__":
    unittest.main()
