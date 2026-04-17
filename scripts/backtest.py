#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from backtesting import SeasonBacktestResult, run_season_backtest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run playoff drafter backtesting across seasons and parameter grids.")
    parser.add_argument("--seasons", nargs="+", type=int, required=True, help="Season years to evaluate, e.g. 2024 2025")
    parser.add_argument("--method", choices=["analytic", "monte_carlo"], default="analytic")
    parser.add_argument("--k-values", nargs="+", type=int, default=[20], help="Shrinkage K values to evaluate")
    parser.add_argument("--risk-lambda-grid", nargs="+", type=float, default=[0.0])
    parser.add_argument(
        "--realized-root",
        type=Path,
        default=None,
        help=(
            "Optional directory containing explicit realized files. "
            "When omitted, backtesting expects resources/<season>/players_playoffs.tsv. "
            "If provided, expected files are: "
            "season_<year>_skaters.tsv (Name, Team, Pos, P, OTG) and optional "
            "season_<year>_goalie_teams.tsv (Name, EV)."
        ),
    )
    return parser.parse_args()


def _write_summary(path: Path, results: list[SeasonBacktestResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle, delimiter="\t")
        writer.writerow(
            [
                "season",
                "method",
                "k",
                "risk_lambda",
                "spearman_overall",
                "spearman_forwards",
                "spearman_defense",
                "spearman_goalie_teams",
                "mae_overall",
                "rmse_overall",
                "lineup_realized_optimized",
                "lineup_realized_baseline",
                "lineup_delta",
            ]
        )
        for result in results:
            writer.writerow(
                [
                    result.season,
                    result.method,
                    result.shrinkage_k,
                    f"{result.risk_lambda:.3f}",
                    f"{result.overall.spearman:.6f}",
                    f"{result.forwards.spearman:.6f}",
                    f"{result.defense.spearman:.6f}",
                    f"{result.goalie_teams.spearman:.6f}",
                    f"{result.overall.mae:.6f}",
                    f"{result.overall.rmse:.6f}",
                    f"{result.optimized_lineup_realized:.6f}",
                    f"{result.baseline_lineup_realized:.6f}",
                    f"{(result.optimized_lineup_realized - result.baseline_lineup_realized):.6f}",
                ]
            )


def _write_season_details(path: Path, results: list[SeasonBacktestResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle, delimiter="\t")
        writer.writerow(
            [
                "season",
                "method",
                "k",
                "risk_lambda",
                "position",
                "spearman",
                "mae",
                "rmse",
                "top_k_precision",
                "top_k_recall",
                "pool_size",
            ]
        )

        for result in results:
            entries = [
                ("overall", result.overall, result.total_players),
                ("forwards", result.forwards, result.total_forwards),
                ("defense", result.defense, result.total_defense),
                ("goalie_teams", result.goalie_teams, result.total_goalie_teams),
            ]
            for position_name, metrics, pool_size in entries:
                writer.writerow(
                    [
                        result.season,
                        result.method,
                        result.shrinkage_k,
                        f"{result.risk_lambda:.3f}",
                        position_name,
                        f"{metrics.spearman:.6f}",
                        f"{metrics.mae:.6f}",
                        f"{metrics.rmse:.6f}",
                        f"{metrics.top_k_precision:.6f}",
                        f"{metrics.top_k_recall:.6f}",
                        pool_size,
                    ]
                )


def main() -> None:
    args = parse_args()
    all_results: list[SeasonBacktestResult] = []

    for season in args.seasons:
        season_results: list[SeasonBacktestResult] = []
        for k_value in args.k_values:
            for risk_lambda in args.risk_lambda_grid:
                result = run_season_backtest(
                    root_dir=ROOT,
                    season=season,
                    method=args.method,
                    shrinkage_k=k_value,
                    risk_lambda=risk_lambda,
                    realized_root_dir=args.realized_root,
                )
                all_results.append(result)
                season_results.append(result)

        details_path = ROOT / "out" / "backtest" / f"season_{season}_details.tsv"
        _write_season_details(details_path, season_results)

    summary_path = ROOT / "out" / "backtest" / "summary.tsv"
    _write_summary(summary_path, all_results)
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
