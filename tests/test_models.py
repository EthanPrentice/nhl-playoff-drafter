import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from contracts import SkaterProjectionInput
from models import project_skaters


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


if __name__ == "__main__":
    unittest.main()
