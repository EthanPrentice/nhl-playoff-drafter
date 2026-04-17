import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from data_loader import LoadDiagnostics
from models import GoalieTeamProjection, SkaterProjection
from optimizer import OptimizedLineup
from reporting import write_diagnostics, write_draft_outputs


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

    def test_write_draft_outputs_creates_reporting_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            skaters = [
                SkaterProjection(
                    name="A Forward",
                    team="AAA",
                    position="F",
                    expected_points=10.0,
                    floor_points=8.0,
                    ceiling_points=12.0,
                    season_rate=1.0,
                    stretch_rate=1.2,
                    blended_rate=1.1,
                    stretch_weight=0.5,
                    team_games_factor=9.0,
                ),
                SkaterProjection(
                    name="A Defense",
                    team="BBB",
                    position="D",
                    expected_points=7.5,
                    floor_points=6.0,
                    ceiling_points=9.0,
                    season_rate=0.8,
                    stretch_rate=0.9,
                    blended_rate=0.85,
                    stretch_weight=0.3,
                    team_games_factor=8.0,
                ),
            ]
            goalie_teams = [
                GoalieTeamProjection(
                    team="AAA",
                    expected_points=6.0,
                    floor_points=4.5,
                    ceiling_points=7.5,
                    wins_component=4.0,
                    assists_component=0.5,
                    shutouts_component=1.5,
                    team_games_factor=9.0,
                )
            ]
            lineup = OptimizedLineup(
                forwards=[skaters[0]],
                defense=[skaters[1]],
                goalie_teams=goalie_teams,
                objective_value=23.5,
            )

            write_draft_outputs(
                output_dir=output_dir,
                skater_projections=skaters,
                goalie_team_projections=goalie_teams,
                optimal_lineup=lineup,
                alternative_lineups={"high_floor": lineup},
            )

            self.assertTrue((output_dir / "forwards.tsv").exists())
            self.assertTrue((output_dir / "defense.tsv").exists())
            self.assertTrue((output_dir / "goalie_teams.tsv").exists())
            self.assertTrue((output_dir / "optimal_lineup.tsv").exists())
            self.assertTrue((output_dir / "alternative_lineups.tsv").exists())
            self.assertTrue((output_dir / "team_exposure.tsv").exists())


if __name__ == "__main__":
    unittest.main()
