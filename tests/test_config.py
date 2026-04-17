import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config import ROSTER, SCORING


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


if __name__ == "__main__":
    unittest.main()
