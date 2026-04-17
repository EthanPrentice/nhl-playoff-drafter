import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from data_loader import DataLoader, ResourceFiles
from team import Team


class DataLoaderTests(unittest.TestCase):
    def test_missing_required_column_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resources = Path(tmpdir)
            (resources / "teams.tsv").write_text("Name\tRound1\tRound2\tConference\nA\t0.5\t0.2\t0.1\n", encoding="utf-8")
            (resources / "players_season.tsv").write_text("Name\tTeam\tPos\tGP\tP\nA\tAAA\tF\t1\t1\n", encoding="utf-8")
            (resources / "players_stretch.tsv").write_text("Name\tTeam\tPos\tGP\tP\nA\tAAA\tF\t1\t1\n", encoding="utf-8")
            (resources / "players_prev_season.tsv").write_text("Name\tTeam\tPos\tGP\tP\nA\tAAA\tF\t1\t1\n", encoding="utf-8")

            loader = DataLoader(
                resources,
                ResourceFiles("teams.tsv", "players_season.tsv", "players_stretch.tsv", "players_prev_season.tsv"),
            )

            with self.assertRaises(ValueError):
                loader.load_teams()

    def test_strict_mode_raises_on_dropped_players(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resources = Path(tmpdir)
            (resources / "teams.tsv").write_text(
                "Name\tRound1\tRound2\tConference\tFinal\nAAA\t0.5\t0.2\t0.1\t0.05\n", encoding="utf-8"
            )
            (resources / "players_season.tsv").write_text("Name\tTeam\tPos\tGP\tP\nA\tAAA\tF\t1\t1\n", encoding="utf-8")
            (resources / "players_stretch.tsv").write_text("Name\tTeam\tPos\tGP\tP\n", encoding="utf-8")
            (resources / "players_prev_season.tsv").write_text("Name\tTeam\tPos\tGP\tP\nA\tAAA\tF\t1\t1\n", encoding="utf-8")

            loader = DataLoader(
                resources,
                ResourceFiles("teams.tsv", "players_season.tsv", "players_stretch.tsv", "players_prev_season.tsv"),
                strict=True,
            )
            teams = [Team({"Name": "AAA", "Round1": "0.5", "Round2": "0.2", "Conference": "0.1", "Final": "0.05"})]
            with self.assertRaises(ValueError):
                loader.load_players(teams)

    def test_non_strict_mode_skips_invalid_numeric_with_reason(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resources = Path(tmpdir)
            (resources / "teams.tsv").write_text(
                "Name\tRound1\tRound2\tConference\tFinal\nAAA\t0.5\t0.2\t0.1\t0.05\n", encoding="utf-8"
            )
            (resources / "players_season.tsv").write_text(
                "Name\tTeam\tPos\tGP\tP\tOTG\nA\tAAA\tF\tbad\t1\t0\n", encoding="utf-8"
            )
            (resources / "players_stretch.tsv").write_text(
                "Name\tTeam\tPos\tGP\tP\tOTG\nA\tAAA\tF\t1\t1\t0\n", encoding="utf-8"
            )
            (resources / "players_prev_season.tsv").write_text(
                "Name\tTeam\tPos\tGP\tP\tOTG\nA\tAAA\tF\t1\t1\t0\n", encoding="utf-8"
            )

            loader = DataLoader(
                resources,
                ResourceFiles("teams.tsv", "players_season.tsv", "players_stretch.tsv", "players_prev_season.tsv"),
                strict=False,
            )
            teams = loader.load_teams()
            players = loader.load_players(teams)
            self.assertEqual(players, [])
            self.assertEqual(loader.diagnostics.dropped_invalid_numeric, 1)
            self.assertEqual(loader.diagnostics.dropped_by_reason["invalid_season_numeric"], 1)

    def test_strict_mode_raises_on_invalid_numeric(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resources = Path(tmpdir)
            (resources / "teams.tsv").write_text(
                "Name\tRound1\tRound2\tConference\tFinal\nAAA\t0.5\t0.2\t0.1\t0.05\n", encoding="utf-8"
            )
            (resources / "players_season.tsv").write_text(
                "Name\tTeam\tPos\tGP\tP\tOTG\nA\tAAA\tF\tbad\t1\t0\n", encoding="utf-8"
            )
            (resources / "players_stretch.tsv").write_text(
                "Name\tTeam\tPos\tGP\tP\tOTG\nA\tAAA\tF\t1\t1\t0\n", encoding="utf-8"
            )
            (resources / "players_prev_season.tsv").write_text(
                "Name\tTeam\tPos\tGP\tP\tOTG\nA\tAAA\tF\t1\t1\t0\n", encoding="utf-8"
            )

            loader = DataLoader(
                resources,
                ResourceFiles("teams.tsv", "players_season.tsv", "players_stretch.tsv", "players_prev_season.tsv"),
                strict=True,
            )
            teams = loader.load_teams()
            with self.assertRaises(ValueError):
                loader.load_players(teams)


if __name__ == "__main__":
    unittest.main()
