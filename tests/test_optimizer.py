import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from models import GoalieTeamProjection, SkaterProjection
from optimizer import LineupConstraints, optimize_lineup


class OptimizerTests(unittest.TestCase):
    def test_exact_constraints_are_satisfied(self):
        forwards = [
            SkaterProjection(name="F1", team="AAA", position="F", expected_points=5.0),
            SkaterProjection(name="F2", team="AAA", position="F", expected_points=4.0),
            SkaterProjection(name="F3", team="BBB", position="F", expected_points=6.0),
            SkaterProjection(name="F4", team="BBB", position="F", expected_points=3.0),
            SkaterProjection(name="F5", team="CCC", position="F", expected_points=2.0),
            SkaterProjection(name="F6", team="DDD", position="F", expected_points=1.0),
        ]
        defense = [
            SkaterProjection(name="D1", team="AAA", position="D", expected_points=4.5),
            SkaterProjection(name="D2", team="BBB", position="D", expected_points=3.5),
            SkaterProjection(name="D3", team="CCC", position="D", expected_points=2.5),
            SkaterProjection(name="D4", team="DDD", position="D", expected_points=1.5),
        ]
        goalie_teams = [
            GoalieTeamProjection(team="AAA", expected_points=7.0),
            GoalieTeamProjection(team="BBB", expected_points=6.0),
            GoalieTeamProjection(team="CCC", expected_points=5.0),
        ]

        lineup = optimize_lineup(
            forwards=forwards,
            defense=defense,
            goalie_teams=goalie_teams,
            constraints=LineupConstraints(forwards=5, defense=3, goalie_teams=2),
        )

        self.assertEqual(len(lineup.forwards), 5)
        self.assertEqual(len(lineup.defense), 3)
        self.assertEqual(len(lineup.goalie_teams), 2)

    def test_tie_breaking_is_deterministic(self):
        forwards = [
            SkaterProjection(name="FA", team="AAA", position="F", expected_points=10.0),
            SkaterProjection(name="FB", team="AAA", position="F", expected_points=10.0),
        ]
        defense = [SkaterProjection(name="DA", team="AAA", position="D", expected_points=5.0)]
        goalie_teams = [GoalieTeamProjection(team="AAA", expected_points=3.0)]

        lineup = optimize_lineup(
            forwards=forwards,
            defense=defense,
            goalie_teams=goalie_teams,
            constraints=LineupConstraints(forwards=1, defense=1, goalie_teams=1),
        )

        self.assertEqual(lineup.forwards[0].name, "FA")

    def test_optional_team_constraints_are_enforced(self):
        forwards = [
            SkaterProjection(name="F1", team="AAA", position="F", expected_points=12.0),
            SkaterProjection(name="F2", team="AAA", position="F", expected_points=11.0),
            SkaterProjection(name="F3", team="BBB", position="F", expected_points=7.0),
        ]
        defense = [
            SkaterProjection(name="D1", team="AAA", position="D", expected_points=9.0),
            SkaterProjection(name="D2", team="BBB", position="D", expected_points=8.0),
        ]
        goalie_teams = [
            GoalieTeamProjection(team="AAA", expected_points=10.0),
            GoalieTeamProjection(team="BBB", expected_points=6.0),
        ]

        lineup = optimize_lineup(
            forwards=forwards,
            defense=defense,
            goalie_teams=goalie_teams,
            constraints=LineupConstraints(
                forwards=2,
                defense=1,
                goalie_teams=1,
                max_skaters_per_team=2,
                max_total_from_team_including_goalie_team=2,
            ),
        )

        team_counts: dict[str, int] = {}
        for skater in [*lineup.forwards, *lineup.defense]:
            team_counts[skater.team] = team_counts.get(skater.team, 0) + 1
        self.assertLessEqual(max(team_counts.values()), 2)

        total_team_counts = dict(team_counts)
        for goalie_team in lineup.goalie_teams:
            total_team_counts[goalie_team.team] = total_team_counts.get(goalie_team.team, 0) + 1
        self.assertLessEqual(max(total_team_counts.values()), 2)


if __name__ == "__main__":
    unittest.main()
