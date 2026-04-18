from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import heuristics
from config import ROSTER
from data_loader import DataLoader, ResourceFiles
from models import estimate_expected_games, project_goalie_teams, project_skaters
from optimizer import LineupConstraints, OptimizedLineup, optimize_lineup
from player import Player
from playoff_draft import set_player_estimated_values, set_team_estimated_values


@dataclass(frozen=True)
class PositionMetrics:
    spearman: float
    mae: float
    rmse: float
    top_k_precision: float
    top_k_recall: float


@dataclass(frozen=True)
class SeasonBacktestResult:
    season: int
    method: str
    shrinkage_k: int
    risk_lambda: float
    total_players: int
    total_forwards: int
    total_defense: int
    total_goalie_teams: int
    overall: PositionMetrics
    forwards: PositionMetrics
    defense: PositionMetrics
    goalie_teams: PositionMetrics
    optimized_lineup_realized: float
    baseline_lineup_realized: float


def _safe_float(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    text = str(value).strip()
    if text == "":
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _dense_rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda idx: values[idx])
    ranks = [0.0] * len(values)

    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1

    return ranks


def _pearson(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0

    mean_a = sum(a) / len(a)
    mean_b = sum(b) / len(b)
    num = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    den_a = math.sqrt(sum((x - mean_a) ** 2 for x in a))
    den_b = math.sqrt(sum((y - mean_b) ** 2 for y in b))
    if den_a == 0 or den_b == 0:
        return 0.0
    return num / (den_a * den_b)


def spearman_rank_correlation(predicted: list[float], realized: list[float]) -> float:
    if len(predicted) != len(realized) or not predicted:
        return 0.0
    return _pearson(_dense_rank(predicted), _dense_rank(realized))


def mae(predicted: list[float], realized: list[float]) -> float:
    if len(predicted) != len(realized) or not predicted:
        return 0.0
    return sum(abs(p - r) for p, r in zip(predicted, realized)) / len(predicted)


def rmse(predicted: list[float], realized: list[float]) -> float:
    if len(predicted) != len(realized) or not predicted:
        return 0.0
    return math.sqrt(sum((p - r) ** 2 for p, r in zip(predicted, realized)) / len(predicted))


def top_k_precision_recall(predicted_scores: dict[str, float], realized_scores: dict[str, float], k: int) -> tuple[float, float]:
    if k <= 0 or not predicted_scores or not realized_scores:
        return 0.0, 0.0

    pred_top = {
        key
        for key, _ in sorted(predicted_scores.items(), key=lambda item: (-item[1], item[0]))[: min(k, len(predicted_scores))]
    }
    realized_top = {
        key
        for key, _ in sorted(realized_scores.items(), key=lambda item: (-item[1], item[0]))[: min(k, len(realized_scores))]
    }

    if not pred_top:
        return 0.0, 0.0

    overlap = len(pred_top.intersection(realized_top))
    precision = overlap / len(pred_top)
    recall = overlap / len(realized_top) if realized_top else 0.0
    return precision, recall


def _compute_metrics(
    projected: dict[str, float],
    realized: dict[str, float],
    k: int,
) -> PositionMetrics:
    shared_keys = sorted(set(projected).intersection(realized))
    if not shared_keys:
        return PositionMetrics(0.0, 0.0, 0.0, 0.0, 0.0)

    projected_values = [projected[key] for key in shared_keys]
    realized_values = [realized[key] for key in shared_keys]
    precision, recall = top_k_precision_recall(
        {key: projected[key] for key in shared_keys},
        {key: realized[key] for key in shared_keys},
        k=k,
    )
    return PositionMetrics(
        spearman=spearman_rank_correlation(projected_values, realized_values),
        mae=mae(projected_values, realized_values),
        rmse=rmse(projected_values, realized_values),
        top_k_precision=precision,
        top_k_recall=recall,
    )


def _legacy_baseline_lineup(players: list[Player], team_names: list[str]) -> tuple[list[Player], list[Player], list[str]]:
    forwards = sorted(
        [player for player in players if player.position == "F"],
        key=lambda player: (-player.estimatedValue, player.team.name, player.name),
    )[: ROSTER.forwards]
    defense = sorted(
        [player for player in players if player.position == "D"],
        key=lambda player: (-player.estimatedValue, player.team.name, player.name),
    )[: ROSTER.defense]
    goalie_teams = sorted(team_names)[: ROSTER.goalie_teams]
    return forwards, defense, goalie_teams


def _read_realized_file(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with open(path, "r", encoding="utf-8") as file_handle:
        lines = [line.rstrip("\n") for line in file_handle if line.strip()]

    if not lines:
        return rows

    header_line = lines[0]
    if "\t" not in header_line and len(lines) > 1 and "\t" in lines[1]:
        parsed = [line.split("\t") for line in lines]
    else:
        parsed = list(csv.reader(lines, delimiter="\t"))

    headers = [col.strip() for col in parsed[0]]
    for data in parsed[1:]:
        values = [val.strip() for val in data]
        if len(values) < len(headers):
            values.extend([""] * (len(headers) - len(values)))
        rows.append(dict(zip(headers, values)))
    return rows


def _load_realized_from_explicit_files(
    skaters_file: Path,
    goalie_teams_file: Path | None = None,
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    # Expected columns for skaters file: Name, Team, Pos, P, OTG (OTG optional)
    # Expected columns for goalie teams file: Name, EV
    realized_skaters: dict[str, float] = {}
    for row in _read_realized_file(skaters_file):
        name = row.get("Name", "").strip()
        team = row.get("Team", "").strip()
        pos = row.get("Pos", "").strip()
        if not name or not team or pos not in {"F", "D"}:
            continue
        key = f"{name}|{team}|{pos}"
        realized_skaters[key] = _safe_float(row.get("P")) + _safe_float(row.get("OTG"))

    realized_goalie_teams: dict[str, float] = {}
    if goalie_teams_file is not None and goalie_teams_file.exists():
        for row in _read_realized_file(goalie_teams_file):
            team_name = row.get("Name", "").strip()
            if not team_name:
                continue
            realized_goalie_teams[team_name] = _safe_float(row.get("EV"))

    realized_forwards = {k: v for k, v in realized_skaters.items() if k.endswith("|F")}
    realized_defense = {k: v for k, v in realized_skaters.items() if k.endswith("|D")}
    return realized_forwards, realized_defense, realized_goalie_teams


def load_realized_points(
    season: int,
    root_dir: Path,
    realized_root_dir: Path | None = None,
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    explicit_realized_root = realized_root_dir

    # Preferred workflow: place realized playoff skater results in
    # resources/<season>/players_playoffs.tsv with season-like columns.
    if realized_root_dir is None:
        realized_root_dir = root_dir / "resources" / str(season)
        skaters_file = realized_root_dir / "players_playoffs.tsv"
        teams_playoffs_file = realized_root_dir / "teams_playoffs.tsv"
        if skaters_file.exists():
            return _load_realized_from_explicit_files(
                skaters_file=skaters_file,
                goalie_teams_file=teams_playoffs_file if teams_playoffs_file.exists() else None,
            )

    if explicit_realized_root is not None:
        skaters_file = realized_root_dir / f"season_{season}_skaters.tsv"
        goalie_teams_file = realized_root_dir / f"season_{season}_goalie_teams.tsv"
        if not skaters_file.exists():
            raise FileNotFoundError(
                f"Missing realized skater file for {season}. Expected either "
                f"{(root_dir / 'resources' / str(season) / 'players_playoffs.tsv')} "
                f"or {skaters_file}. "
                "Supported schemas: "
                "1) resources/<season>/players_playoffs.tsv with season-like columns "
                "(Name, Team, Pos, P, OTG), optional resources/<season>/teams_playoffs.tsv (Name, EV); "
                "2) --realized-root with season_<year>_skaters.tsv and optional season_<year>_goalie_teams.tsv."
            )
        return _load_realized_from_explicit_files(
            skaters_file=skaters_file,
            goalie_teams_file=goalie_teams_file if goalie_teams_file.exists() else None,
        )

    raise FileNotFoundError(
        f"Missing realized skater file for {season}. Expected resources file "
        f"{(root_dir / 'resources' / str(season) / 'players_playoffs.tsv')}. "
        "Add players_playoffs.tsv (same schema as players_season.tsv) to run backtesting."
    )


def _lineup_realized_points(
    lineup: OptimizedLineup,
    realized_forwards: dict[str, float],
    realized_defense: dict[str, float],
    realized_goalie_teams: dict[str, float],
) -> float:
    total = 0.0
    for player in lineup.forwards:
        total += realized_forwards.get(f"{player.name}|{player.team}|F", 0.0)
    for player in lineup.defense:
        total += realized_defense.get(f"{player.name}|{player.team}|D", 0.0)
    for team in lineup.goalie_teams:
        total += realized_goalie_teams.get(team.team, 0.0)
    return total


def run_season_backtest(
    root_dir: Path,
    season: int,
    method: str,
    shrinkage_k: int,
    risk_lambda: float,
    min_stretch_gp_for_direct_weight: int = 10,
    max_skaters_per_team: int | None = None,
    max_total_from_team_including_goalie_team: int | None = None,
    series_len_r1: float = 5.9,
    series_len_r2: float = 5.9,
    series_len_r3: float = 5.9,
    series_len_r4: float = 5.9,
    monte_carlo_simulations: int = 20_000,
    realized_root_dir: Path | None = None,
) -> SeasonBacktestResult:
    resources_dir = root_dir / "resources" / str(season)
    loader = DataLoader(
        resources_dir=resources_dir,
        resource_files=ResourceFiles(
            teams_file="teams.tsv",
            player_season_file="players_season.tsv",
            player_stretch_file="players_stretch.tsv",
            player_prev_season_file=(
                "players_prev_season.tsv"
                if (resources_dir / "players_prev_season.tsv").exists()
                else "players_season.tsv"
            ),
        ),
        strict=False,
    )

    teams = loader.load_teams()
    players = loader.load_players(teams)

    set_team_estimated_values(teams, players, heuristics.get_team_weight_diff_penalty)
    set_player_estimated_values(players, heuristics.sum_team_odds_multiply_points_stretch_weighted_per_game)

    expected_games = estimate_expected_games(
        loader.to_team_odds_inputs(teams),
        method=method,
        monte_carlo_simulations=monte_carlo_simulations,
        series_len_r1=series_len_r1,
        series_len_r2=series_len_r2,
        series_len_r3=series_len_r3,
        series_len_r4=series_len_r4,
    )
    expected_team_games = {team_name: stats.mean for team_name, stats in expected_games.items()}

    skater_projections = project_skaters(
        loader.to_skater_projection_inputs(players),
        expected_team_games,
        stretch_shrinkage_k=shrinkage_k,
        min_stretch_gp_for_direct_weight=min_stretch_gp_for_direct_weight,
    )
    goalie_projections = project_goalie_teams(loader.to_goalie_team_projection_inputs(teams), expected_team_games)

    optimized = optimize_lineup(
        forwards=[item for item in skater_projections if item.position == "F"],
        defense=[item for item in skater_projections if item.position == "D"],
        goalie_teams=goalie_projections,
        constraints=LineupConstraints(
            forwards=ROSTER.forwards,
            defense=ROSTER.defense,
            goalie_teams=ROSTER.goalie_teams,
            max_skaters_per_team=max_skaters_per_team,
            max_total_from_team_including_goalie_team=max_total_from_team_including_goalie_team,
        ),
        risk_lambda=risk_lambda,
    )

    baseline_forwards, baseline_defense, baseline_goalie_teams = _legacy_baseline_lineup(players, [team.name for team in teams])

    realized_forwards, realized_defense, realized_goalie_teams = load_realized_points(
        season=season,
        root_dir=root_dir,
        realized_root_dir=realized_root_dir,
    )

    projected_forwards = {f"{item.name}|{item.team}|F": item.expected_points for item in skater_projections if item.position == "F"}
    projected_defense = {f"{item.name}|{item.team}|D": item.expected_points for item in skater_projections if item.position == "D"}
    projected_goalie_teams = {item.team: item.expected_points for item in goalie_projections}

    all_projected = {**projected_forwards, **projected_defense}
    all_realized = {**realized_forwards, **realized_defense}

    optimized_realized = _lineup_realized_points(optimized, realized_forwards, realized_defense, realized_goalie_teams)

    baseline_realized = sum(realized_forwards.get(f"{player.name}|{player.team.name}|F", 0.0) for player in baseline_forwards)
    baseline_realized += sum(realized_defense.get(f"{player.name}|{player.team.name}|D", 0.0) for player in baseline_defense)
    baseline_realized += sum(realized_goalie_teams.get(team_name, 0.0) for team_name in baseline_goalie_teams)

    return SeasonBacktestResult(
        season=season,
        method=method,
        shrinkage_k=shrinkage_k,
        risk_lambda=risk_lambda,
        total_players=len(all_projected),
        total_forwards=len(projected_forwards),
        total_defense=len(projected_defense),
        total_goalie_teams=len(projected_goalie_teams),
        overall=_compute_metrics(all_projected, all_realized, k=ROSTER.forwards + ROSTER.defense),
        forwards=_compute_metrics(projected_forwards, realized_forwards, k=ROSTER.forwards),
        defense=_compute_metrics(projected_defense, realized_defense, k=ROSTER.defense),
        goalie_teams=_compute_metrics(projected_goalie_teams, realized_goalie_teams, k=ROSTER.goalie_teams),
        optimized_lineup_realized=optimized_realized,
        baseline_lineup_realized=baseline_realized,
    )
