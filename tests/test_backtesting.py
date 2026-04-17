import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from backtesting import load_realized_points, mae, rmse, spearman_rank_correlation, top_k_precision_recall


class BacktestingMetricsTests(unittest.TestCase):
    def test_spearman_perfect_and_inverse(self):
        self.assertAlmostEqual(spearman_rank_correlation([1, 2, 3], [10, 20, 30]), 1.0)
        self.assertAlmostEqual(spearman_rank_correlation([1, 2, 3], [30, 20, 10]), -1.0)

    def test_mae_and_rmse(self):
        predicted = [1.0, 2.0, 3.0]
        realized = [2.0, 2.0, 2.0]
        self.assertAlmostEqual(mae(predicted, realized), 2.0 / 3.0)
        self.assertAlmostEqual(rmse(predicted, realized), (2.0 / 3.0) ** 0.5)

    def test_top_k_precision_recall(self):
        predicted = {"a": 9.0, "b": 8.0, "c": 2.0, "d": 1.0}
        realized = {"a": 10.0, "d": 9.0, "b": 1.0, "c": 0.5}
        precision, recall = top_k_precision_recall(predicted, realized, k=2)

        self.assertAlmostEqual(precision, 0.5)
        self.assertAlmostEqual(recall, 0.5)

    def test_load_realized_points_from_explicit_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            realized_root = root / "realized"
            realized_root.mkdir(parents=True, exist_ok=True)
            (realized_root / "season_2025_skaters.tsv").write_text(
                "Name\tTeam\tPos\tP\tOTG\n"
                "Player A\tAAA\tF\t10\t1\n"
                "Player B\tBBB\tD\t5\t0\n",
                encoding="utf-8",
            )
            (realized_root / "season_2025_goalie_teams.tsv").write_text(
                "Name\tEV\nAAA\t4\n",
                encoding="utf-8",
            )

            forwards, defense, goalie_teams = load_realized_points(
                season=2025,
                root_dir=root,
                realized_root_dir=realized_root,
            )

            self.assertEqual(forwards["Player A|AAA|F"], 11.0)
            self.assertEqual(defense["Player B|BBB|D"], 5.0)
            self.assertEqual(goalie_teams["AAA"], 4.0)

    def test_load_realized_points_from_resources_players_playoffs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            resources_dir = root / "resources" / "2025"
            resources_dir.mkdir(parents=True, exist_ok=True)
            (resources_dir / "players_playoffs.tsv").write_text(
                "Name\tTeam\tPos\tP\tOTG\n"
                "Player C\tCCC\tF\t6\t2\n"
                "Player D\tDDD\tD\t4\t1\n",
                encoding="utf-8",
            )

            forwards, defense, goalie_teams = load_realized_points(season=2025, root_dir=root)

            self.assertEqual(forwards["Player C|CCC|F"], 8.0)
            self.assertEqual(defense["Player D|DDD|D"], 5.0)
            self.assertEqual(goalie_teams, {})


if __name__ == "__main__":
    unittest.main()
