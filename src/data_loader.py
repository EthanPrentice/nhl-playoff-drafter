import csv
from dataclasses import dataclass, field
from pathlib import Path

from contracts import GoalieTeamProjectionInput, SkaterProjectionInput, TeamOddsInput
from player import Player
from team import Team


@dataclass(frozen=True)
class ResourceFiles:
    teams_file: str
    player_season_file: str
    player_stretch_file: str
    player_prev_season_file: str


@dataclass
class LoadDiagnostics:
    season_rows: int = 0
    stretch_rows: int = 0
    prev_rows: int = 0
    team_rows: int = 0
    players_loaded: int = 0
    skipped_missing_stretch: int = 0
    skipped_missing_team: int = 0
    warnings: list[str] = field(default_factory=list)


class DataLoader:
    REQUIRED_TEAM_COLUMNS = {"Name", "Round1", "Round2", "Conference", "Final"}
    REQUIRED_PLAYER_COLUMNS = {"Name", "Team", "Pos", "GP", "P"}

    def __init__(self, resources_dir: Path, resource_files: ResourceFiles, strict: bool = False):
        self.resources_dir = Path(resources_dir)
        self.resource_files = resource_files
        self.strict = strict
        self.diagnostics = LoadDiagnostics()

    def load_teams(self) -> list[Team]:
        teams_data = self._read_tsv(self.resource_files.teams_file)
        self.diagnostics.team_rows = len(teams_data)
        self._validate_columns(self.resource_files.teams_file, teams_data, self.REQUIRED_TEAM_COLUMNS)
        return [Team(row) for row in teams_data]

    def load_players(self, teams: list[Team]) -> list[Player]:
        season_rows = self._read_tsv(self.resource_files.player_season_file)
        stretch_rows = self._read_tsv(self.resource_files.player_stretch_file)
        prev_rows = self._read_tsv(self.resource_files.player_prev_season_file)

        self.diagnostics.season_rows = len(season_rows)
        self.diagnostics.stretch_rows = len(stretch_rows)
        self.diagnostics.prev_rows = len(prev_rows)

        self._validate_columns(self.resource_files.player_season_file, season_rows, self.REQUIRED_PLAYER_COLUMNS)
        self._validate_columns(self.resource_files.player_stretch_file, stretch_rows, self.REQUIRED_PLAYER_COLUMNS)

        teams_by_name = {team.name: team for team in teams}
        stretch_by_key = self._index_by_player_key(stretch_rows)
        prev_by_key = self._index_by_player_key(prev_rows)

        players: list[Player] = []
        for season in season_rows:
            key = self._player_key(season)
            stretch = stretch_by_key.get(key)
            team = teams_by_name.get(season.get("Team", ""))
            if stretch is None:
                self.diagnostics.skipped_missing_stretch += 1
                continue
            if team is None:
                self.diagnostics.skipped_missing_team += 1
                continue

            prev = prev_by_key.get(key, {})
            players.append(Player(team, season, stretch, prev))

        self.diagnostics.players_loaded = len(players)
        self._finalize_diagnostics()
        return players


    def to_skater_projection_inputs(self, players: list[Player]) -> list[SkaterProjectionInput]:
        results: list[SkaterProjectionInput] = []
        for player in players:
            results.append(
                SkaterProjectionInput(
                    name=player.name,
                    team=player.team.name,
                    position=player.position,
                    season_gp=player.seasonStats.games_played,
                    season_p=player.seasonStats.points,
                    season_otg=player.seasonStats.overtime_goals,
                    stretch_gp=player.stretchStats.games_played,
                    stretch_p=player.stretchStats.points,
                    stretch_otg=player.stretchStats.overtime_goals,
                    prior_gp=player.prevSeasonStats.games_played,
                    prior_p=player.prevSeasonStats.points,
                    prior_otg=player.prevSeasonStats.overtime_goals,
                )
            )
        return results

    def to_team_odds_inputs(self, teams: list[Team]) -> list[TeamOddsInput]:
        return [
            TeamOddsInput(
                team=team.name,
                round1=team.odds.round1,
                round2=team.odds.round2,
                conference=team.odds.conference,
                final=team.odds.final,
            )
            for team in teams
        ]

    def to_goalie_team_projection_inputs(self, teams: list[Team]) -> list[GoalieTeamProjectionInput]:
        team_odds = {item.team: item for item in self.to_team_odds_inputs(teams)}
        return [
            GoalieTeamProjectionInput(
                team=team.name,
                season_wins=0,
                season_goaltender_assists=0,
                season_shutouts=0,
                team_odds=team_odds[team.name],
            )
            for team in teams
        ]

    def _read_tsv(self, filename: str) -> list[dict[str, str]]:
        file_path = self.resources_dir / filename
        with open(file_path, mode="r", newline="", encoding="utf-8") as file_handle:
            return list(csv.DictReader(file_handle, delimiter="\t"))

    @staticmethod
    def _validate_columns(filename: str, rows: list[dict[str, str]], required: set[str]):
        if not rows:
            raise ValueError(f"File {filename} is empty")

        missing = required - set(rows[0].keys())
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(f"File {filename} missing required columns: {missing_list}")

    @staticmethod
    def _player_key(row: dict[str, str]) -> tuple[str, str]:
        return row.get("Name", ""), row.get("Team", "")

    def _index_by_player_key(self, rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
        return {self._player_key(row): row for row in rows}

    def _finalize_diagnostics(self) -> None:
        if self.diagnostics.skipped_missing_stretch:
            self.diagnostics.warnings.append(
                f"Skipped {self.diagnostics.skipped_missing_stretch} players with no stretch row match"
            )
        if self.diagnostics.skipped_missing_team:
            self.diagnostics.warnings.append(
                f"Skipped {self.diagnostics.skipped_missing_team} players with no known team"
            )

        if self.strict and (self.diagnostics.skipped_missing_stretch or self.diagnostics.skipped_missing_team):
            joined = "; ".join(self.diagnostics.warnings)
            raise ValueError(f"Strict mode enabled, dropped players during load: {joined}")

    def diagnostics_summary(self) -> str:
        summary = (
            f"loaded players={self.diagnostics.players_loaded} "
            f"from season={self.diagnostics.season_rows}, "
            f"stretch={self.diagnostics.stretch_rows}, "
            f"prev={self.diagnostics.prev_rows}; "
            f"skipped_missing_stretch={self.diagnostics.skipped_missing_stretch}, "
            f"skipped_missing_team={self.diagnostics.skipped_missing_team}"
        )
        return summary
