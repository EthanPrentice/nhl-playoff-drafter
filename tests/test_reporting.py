import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from data_loader import LoadDiagnostics
from reporting import write_diagnostics


class ReportingTests(unittest.TestCase):
    def test_write_diagnostics_includes_counts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            diagnostics = LoadDiagnostics(
                season_rows=10,
                stretch_rows=9,
                prev_rows=8,
                team_rows=16,
                teams_loaded=15,
                players_loaded=100,
                skipped_missing_stretch=2,
                skipped_missing_team=1,
                dropped_invalid_numeric=3,
                dropped_by_reason={"invalid_season_numeric": 3},
                critical_missing_counts={"players_season.tsv:OTG": 5},
            )
            write_diagnostics(diagnostics, output_dir)

            with open(output_dir / "diagnostics.tsv", newline="", encoding="utf-8") as file_handle:
                rows = list(csv.reader(file_handle, delimiter="\t"))

            self.assertEqual(rows[0], ["metric", "value"])
            self.assertIn(["players_loaded", "100"], rows)
            self.assertIn(["dropped_reason:invalid_season_numeric", "3"], rows)
            self.assertIn(["missing_critical:players_season.tsv:OTG", "5"], rows)


if __name__ == "__main__":
    unittest.main()
