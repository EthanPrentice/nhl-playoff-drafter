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
    teams_loaded: int = 0
    skipped_missing_stretch: int = 0
    skipped_missing_team: int = 0
    dropped_invalid_numeric: int = 0
    dropped_by_reason: dict[str, int] = field(default_factory=dict)
    critical_missing_counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def bump_drop_reason(self, reason: str) -> None:
        self.dropped_by_reason[reason] = self.dropped_by_reason.get(reason, 0) + 1


@dataclass(frozen=True)
class ParseContext:
    file: str
    row: int
    column: str


@dataclass(frozen=True)
class ParseIssue:
    context: ParseContext
    reason: str
    value: str

    def as_warning(self) -> str:
        return (
            f"{self.reason}: file={self.context.file}, row={self.context.row}, "
            f"column={self.context.column}, value={self.value!r}"
        )


class DataLoader:
    REQUIRED_TEAM_COLUMNS = {"Name", "Round1", "Round2", "Conference", "Final"}
    REQUIRED_PLAYER_COLUMNS = {"Name", "Team", "Pos", "GP", "P"}
    CRITICAL_PLAYER_FIELDS = ("GP", "P", "OTG")
    CRITICAL_TEAM_FIELDS = ("Round1", "Round2", "Conference", "Final")

    def __init__(self, resources_dir: Path, resource_files: ResourceFiles, strict: bool = False):
        self.resources_dir = Path(resources_dir)
        self.resource_files = resource_files
        self.strict = strict
        self.diagnostics = LoadDiagnostics()

    def load_teams(self) -> list[Team]:
        teams_data = self._read_tsv(self.resource_files.teams_file)
        self.diagnostics.team_rows = len(teams_data)
        self._validate_columns(self.resource_files.teams_file, teams_data, self.REQUIRED_TEAM_COLUMNS)
        self._track_missing_counts(
            filename=self.resource_files.teams_file,
            rows=teams_data,
            critical_fields=self.CRITICAL_TEAM_FIELDS,
        )

        teams: list[Team] = []
        for row_idx, row in enumerate(teams_data, start=2):
            issue = self._validate_numeric_fields(
                filename=self.resource_files.teams_file,
                row=row,
                row_idx=row_idx,
                fields=self.CRITICAL_TEAM_FIELDS,
            )
            if issue is not None:
                self._drop_row("invalid_team_numeric", issue)
                continue

            teams.append(Team(row))

        self.diagnostics.teams_loaded = len(teams)
        return teams

    def load_players(self, teams: list[Team]) -> list[Player]:
        season_rows = self._read_tsv(self.resource_files.player_season_file)
        stretch_rows = self._read_tsv(self.resource_files.player_stretch_file)
        prev_rows = self._read_tsv(self.resource_files.player_prev_season_file)

        self.diagnostics.season_rows = len(season_rows)
        self.diagnostics.stretch_rows = len(stretch_rows)
        self.diagnostics.prev_rows = len(prev_rows)

        self._validate_columns(self.resource_files.player_season_file, season_rows, self.REQUIRED_PLAYER_COLUMNS)
        self._validate_columns(self.resource_files.player_stretch_file, stretch_rows, self.REQUIRED_PLAYER_COLUMNS)
        self._track_missing_counts(
            filename=self.resource_files.player_season_file,
            rows=season_rows,
            critical_fields=self.CRITICAL_PLAYER_FIELDS,
        )
        self._track_missing_counts(
            filename=self.resource_files.player_stretch_file,
            rows=stretch_rows,
            critical_fields=self.CRITICAL_PLAYER_FIELDS,
        )
        self._track_missing_counts(
            filename=self.resource_files.player_prev_season_file,
            rows=prev_rows,
            critical_fields=self.CRITICAL_PLAYER_FIELDS,
        )

        teams_by_name = {team.name: team for team in teams}
        stretch_by_key = self._index_by_player_key(stretch_rows)
        prev_by_key = self._index_by_player_key(prev_rows)

        players: list[Player] = []
        for row_idx, season in enumerate(season_rows, start=2):
            key = self._player_key(season)
            stretch = stretch_by_key.get(key)
            team = teams_by_name.get(season.get("Team", ""))
            if stretch is None:
                self.diagnostics.skipped_missing_stretch += 1
                self.diagnostics.bump_drop_reason("no_stretch_match")
                continue
            if team is None:
                self.diagnostics.skipped_missing_team += 1
                self.diagnostics.bump_drop_reason("no_team_match")
                continue

            prev = prev_by_key.get(key, {})
            season_issue = self._validate_numeric_fields(
                filename=self.resource_files.player_season_file,
                row=season,
                row_idx=row_idx,
                fields=self.CRITICAL_PLAYER_FIELDS,
            )
            if season_issue is not None:
                self._drop_row("invalid_season_numeric", season_issue)
                continue

            stretch_issue = self._validate_numeric_fields(
                filename=self.resource_files.player_stretch_file,
                row=stretch,
                row_idx=self._row_index(stretch_rows, stretch),
                fields=self.CRITICAL_PLAYER_FIELDS,
            )
            if stretch_issue is not None:
                self._drop_row("invalid_stretch_numeric", stretch_issue)
                continue

            if prev and (
                prev_issue := self._validate_numeric_fields(
                    filename=self.resource_files.player_prev_season_file,
                    row=prev,
                    row_idx=self._row_index(prev_rows, prev),
                    fields=self.CRITICAL_PLAYER_FIELDS,
                )
            ):
                self._drop_row("invalid_prev_numeric", prev_issue)
                continue

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

    def _row_index(self, rows: list[dict[str, str]], match_row: dict[str, str]) -> int:
        for idx, row in enumerate(rows, start=2):
            if row is match_row:
                return idx
        return 0

    def _drop_row(self, reason: str, issue: ParseIssue) -> None:
        self.diagnostics.dropped_invalid_numeric += 1
        self.diagnostics.bump_drop_reason(reason)
        self.diagnostics.warnings.append(issue.as_warning())

    def _track_missing_counts(self, filename: str, rows: list[dict[str, str]], critical_fields: tuple[str, ...]) -> None:
        for column in critical_fields:
            key = f"{filename}:{column}"
            self.diagnostics.critical_missing_counts[key] = 0

        for row in rows:
            for column in critical_fields:
                value = row.get(column, "")
                if value is None or value.strip() == "":
                    key = f"{filename}:{column}"
                    self.diagnostics.critical_missing_counts[key] += 1

    @staticmethod
    def _validate_numeric_fields(
        filename: str,
        row: dict[str, str],
        row_idx: int,
        fields: tuple[str, ...],
    ) -> ParseIssue | None:
        for column in fields:
            raw_value = row.get(column, "")
            if raw_value is None or raw_value.strip() == "":
                continue
            try:
                float(raw_value)
            except ValueError:
                return ParseIssue(
                    context=ParseContext(file=filename, row=row_idx, column=column),
                    reason="invalid numeric",
                    value=raw_value,
                )
        return None

    def _finalize_diagnostics(self) -> None:
        if self.diagnostics.skipped_missing_stretch:
            self.diagnostics.warnings.append(
                f"Skipped {self.diagnostics.skipped_missing_stretch} players with no stretch row match"
            )
        if self.diagnostics.skipped_missing_team:
            self.diagnostics.warnings.append(
                f"Skipped {self.diagnostics.skipped_missing_team} players with no known team"
            )
        if self.diagnostics.dropped_invalid_numeric:
            self.diagnostics.warnings.append(
                f"Skipped {self.diagnostics.dropped_invalid_numeric} rows with invalid numeric values"
            )

        total_dropped = (
            self.diagnostics.skipped_missing_stretch
            + self.diagnostics.skipped_missing_team
            + self.diagnostics.dropped_invalid_numeric
        )
        if self.strict and total_dropped:
            joined = "; ".join(self.diagnostics.dropped_by_reason.keys())
            raise ValueError(f"Strict mode enabled, dropped players during load: {joined}")

    def diagnostics_summary(self) -> str:
        summary = (
            f"loaded teams={self.diagnostics.teams_loaded}, players={self.diagnostics.players_loaded} "
            f"from season={self.diagnostics.season_rows}, "
            f"stretch={self.diagnostics.stretch_rows}, "
            f"prev={self.diagnostics.prev_rows}; "
            f"skipped_missing_stretch={self.diagnostics.skipped_missing_stretch}, "
            f"skipped_missing_team={self.diagnostics.skipped_missing_team}, "
            f"dropped_invalid_numeric={self.diagnostics.dropped_invalid_numeric}"
        )
        return summary
