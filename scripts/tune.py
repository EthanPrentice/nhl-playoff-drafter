#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from backtesting import SeasonBacktestResult, run_season_backtest
from config import TUNING_BASELINE, TUNING_GRID, TuningConfig
from tuning import TuningScore, passes_primary_metric_gate, weighted_validation_score


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tune playoff drafter heuristics with coarse sweep + local refinement.")
    parser.add_argument("--seasons", nargs="+", type=int, required=True, help="Backtest seasons, e.g. 2024 2025")
    parser.add_argument("--coarse-limit", type=int, default=None, help="Optional cap on number of coarse configs")
    parser.add_argument("--refine-top-k", type=int, default=TUNING_GRID.refinement_top_k)
    parser.add_argument("--prune-margin", type=float, default=0.75, help="Early-pruning margin vs best split score")
    parser.add_argument("--realized-root", type=Path, default=None)
    return parser.parse_args()


def _git_commit() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True)
            .strip()
        )
    except Exception:
        return "unknown"


def _rolling_validation_splits(seasons: list[int]) -> list[tuple[list[int], list[int]]]:
    if len(seasons) < 2:
        return [(seasons, seasons)]

    splits: list[tuple[list[int], list[int]]] = []
    for idx in range(len(seasons)):
        validation = [seasons[idx]]
        train = [season for i, season in enumerate(seasons) if i != idx]
        splits.append((train, validation))
    return splits


def _coarse_configs() -> list[TuningConfig]:
    configs: list[TuningConfig] = []
    for method in TUNING_GRID.methods:
        mc_sims = TUNING_GRID.coarse_monte_carlo_simulations if method == "monte_carlo" else TUNING_BASELINE.monte_carlo_simulations
        for shrinkage_k in TUNING_GRID.shrinkage_k_values:
            for min_stretch_gp in TUNING_GRID.min_stretch_gp_values:
                for risk_lambda in TUNING_GRID.risk_lambda_values:
                    for max_skaters in TUNING_GRID.max_skaters_per_team_values:
                        for max_total in TUNING_GRID.max_total_from_team_values:
                            if max_skaters is not None and max_total is not None and max_total < max_skaters:
                                continue
                            for series_profile in TUNING_GRID.series_length_profiles:
                                configs.append(
                                    TuningConfig(
                                        method=method,
                                        stretch_shrinkage_k=shrinkage_k,
                                        min_stretch_gp_for_direct_weight=min_stretch_gp,
                                        risk_lambda=risk_lambda,
                                        max_skaters_per_team=max_skaters,
                                        max_total_from_team_including_goalie_team=max_total,
                                        series_lengths=series_profile,
                                        monte_carlo_simulations=mc_sims,
                                    )
                                )
    return sorted(configs, key=lambda config: config.stable_id())


def _refined_neighbors(config: TuningConfig) -> list[TuningConfig]:
    refined: dict[str, TuningConfig] = {}
    for dk in (-5, 5):
        refined_cfg = replace(config, stretch_shrinkage_k=max(5, config.stretch_shrinkage_k + dk))
        refined[refined_cfg.stable_id()] = refined_cfg

    for dgp in (-2, 2):
        refined_cfg = replace(
            config,
            min_stretch_gp_for_direct_weight=max(2, config.min_stretch_gp_for_direct_weight + dgp),
        )
        refined[refined_cfg.stable_id()] = refined_cfg

    for drisk in (-0.05, 0.05):
        refined_cfg = replace(config, risk_lambda=round(max(-0.5, min(0.75, config.risk_lambda + drisk)), 3))
        refined[refined_cfg.stable_id()] = refined_cfg

    for dsl in (-0.1, 0.1):
        refined_cfg = replace(
            config,
            series_lengths=replace(
                config.series_lengths,
                round1=max(5.0, min(6.4, config.series_lengths.round1 + dsl)),
                round2=max(5.0, min(6.4, config.series_lengths.round2 + dsl)),
                round3=max(5.0, min(6.4, config.series_lengths.round3 + dsl)),
                round4=max(5.0, min(6.4, config.series_lengths.round4 + dsl)),
            ),
        )
        refined[refined_cfg.stable_id()] = refined_cfg

    for max_skaters in (None, 3):
        refined_cfg = replace(config, max_skaters_per_team=max_skaters)
        if (
            refined_cfg.max_skaters_per_team is None
            or refined_cfg.max_total_from_team_including_goalie_team is None
            or refined_cfg.max_total_from_team_including_goalie_team >= refined_cfg.max_skaters_per_team
        ):
            refined[refined_cfg.stable_id()] = refined_cfg

    for max_total in (None, 3, 4):
        refined_cfg = replace(config, max_total_from_team_including_goalie_team=max_total)
        if (
            refined_cfg.max_skaters_per_team is None
            or refined_cfg.max_total_from_team_including_goalie_team is None
            or refined_cfg.max_total_from_team_including_goalie_team >= refined_cfg.max_skaters_per_team
        ):
            refined[refined_cfg.stable_id()] = refined_cfg

    for stable_id, candidate in list(refined.items()):
        if candidate.method == "monte_carlo":
            refined[stable_id] = replace(candidate, monte_carlo_simulations=TUNING_GRID.refine_monte_carlo_simulations)
    return sorted(refined.values(), key=lambda item: item.stable_id())


def _evaluate_config(
    config: TuningConfig,
    seasons: list[int],
    prune_margin: float,
    realized_root: Path | None,
    split_baseline_best: dict[int, float],
    season_cache: dict[tuple[int, str], SeasonBacktestResult],
) -> tuple[TuningScore, list[SeasonBacktestResult]]:
    split_scores: list[float] = []
    split_lineup_deltas: list[float] = []
    split_spearman: list[float] = []
    split_rmse: list[float] = []
    season_results: list[SeasonBacktestResult] = []

    splits = _rolling_validation_splits(seasons)

    for split_idx, (_, validation_seasons) in enumerate(splits):
        split_values: list[float] = []
        for season in validation_seasons:
            cache_key = (season, config.stable_id())
            if cache_key in season_cache:
                result = season_cache[cache_key]
            else:
                result = run_season_backtest(
                    root_dir=ROOT,
                    season=season,
                    method=config.method,
                    shrinkage_k=config.stretch_shrinkage_k,
                    risk_lambda=config.risk_lambda,
                    min_stretch_gp_for_direct_weight=config.min_stretch_gp_for_direct_weight,
                    max_skaters_per_team=config.max_skaters_per_team,
                    max_total_from_team_including_goalie_team=config.max_total_from_team_including_goalie_team,
                    series_len_r1=config.series_lengths.round1,
                    series_len_r2=config.series_lengths.round2,
                    series_len_r3=config.series_lengths.round3,
                    series_len_r4=config.series_lengths.round4,
                    monte_carlo_simulations=config.monte_carlo_simulations,
                    realized_root_dir=realized_root,
                )
                season_cache[cache_key] = result
            season_results.append(result)

            lineup_delta = result.optimized_lineup_realized - result.baseline_lineup_realized
            score = weighted_validation_score(
                lineup_delta=lineup_delta,
                spearman=result.overall.spearman,
                rmse=result.overall.rmse,
            )
            split_values.append(score)
            split_lineup_deltas.append(lineup_delta)
            split_spearman.append(result.overall.spearman)
            split_rmse.append(result.overall.rmse)

        split_score = sum(split_values) / len(split_values)
        split_scores.append(split_score)

        current_best = split_baseline_best.get(split_idx, float("-inf"))
        if split_score > current_best:
            split_baseline_best[split_idx] = split_score
        elif split_score < current_best - prune_margin:
            break

    if not split_scores:
        split_scores = [-1e9]

    score = TuningScore(
        config=config,
        mean_weighted_score=sum(split_scores) / len(split_scores),
        min_weighted_score=min(split_scores),
        mean_lineup_delta=(sum(split_lineup_deltas) / len(split_lineup_deltas)) if split_lineup_deltas else -1e9,
        mean_spearman=(sum(split_spearman) / len(split_spearman)) if split_spearman else -1e9,
        mean_rmse=(sum(split_rmse) / len(split_rmse)) if split_rmse else 1e9,
    )
    return score, season_results


def _write_runs(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            delimiter="\t",
            fieldnames=[
                "timestamp_utc",
                "git_commit",
                "run_id",
                "parent_run_id",
                "stage",
                "season_set",
                "config_id",
                "method",
                "k",
                "min_stretch_gp",
                "risk_lambda",
                "max_skaters_per_team",
                "max_total_from_team",
                "series_lengths",
                "mc_simulations",
                "mean_weighted_score",
                "min_weighted_score",
                "mean_lineup_delta",
                "mean_spearman",
                "mean_rmse",
                "runtime_sec",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_candidates(path: Path, top_scores: list[TuningScore]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(
            [
                "config_id",
                "method",
                "k",
                "min_stretch_gp",
                "risk_lambda",
                "max_skaters_per_team",
                "max_total_from_team",
                "series_lengths",
                "mean_weighted_score",
                "min_weighted_score",
                "mean_lineup_delta",
                "mean_spearman",
                "mean_rmse",
            ]
        )
        for score in top_scores:
            config = score.config
            writer.writerow(
                [
                    config.stable_id(),
                    config.method,
                    config.stretch_shrinkage_k,
                    config.min_stretch_gp_for_direct_weight,
                    f"{config.risk_lambda:.3f}",
                    "" if config.max_skaters_per_team is None else config.max_skaters_per_team,
                    "" if config.max_total_from_team_including_goalie_team is None else config.max_total_from_team_including_goalie_team,
                    f"{config.series_lengths.round1:.2f},{config.series_lengths.round2:.2f},{config.series_lengths.round3:.2f},{config.series_lengths.round4:.2f}",
                    f"{score.mean_weighted_score:.6f}",
                    f"{score.min_weighted_score:.6f}",
                    f"{score.mean_lineup_delta:.6f}",
                    f"{score.mean_spearman:.6f}",
                    f"{score.mean_rmse:.6f}",
                ]
            )


def main() -> None:
    args = parse_args()
    seasons = sorted(dict.fromkeys(args.seasons))
    season_set = ",".join(str(year) for year in seasons)
    git_commit = _git_commit()
    timestamp = datetime.now(timezone.utc).isoformat()

    season_cache: dict[tuple[int, str], SeasonBacktestResult] = {}
    split_baseline_best: dict[int, float] = {}
    all_rows: list[dict[str, str]] = []

    coarse_configs = _coarse_configs()
    if args.coarse_limit is not None:
        coarse_configs = coarse_configs[: args.coarse_limit]

    coarse_scores: list[TuningScore] = []
    run_counter = 0
    for config in coarse_configs:
        start = time.perf_counter()
        score, _ = _evaluate_config(
            config=config,
            seasons=seasons,
            prune_margin=args.prune_margin,
            realized_root=args.realized_root,
            split_baseline_best=split_baseline_best,
            season_cache=season_cache,
        )
        runtime_sec = time.perf_counter() - start
        coarse_scores.append(score)

        run_counter += 1
        all_rows.append(
            {
                "timestamp_utc": timestamp,
                "git_commit": git_commit,
                "run_id": f"run-{run_counter:05d}",
                "parent_run_id": "",
                "stage": "coarse",
                "season_set": season_set,
                "config_id": config.stable_id(),
                "method": config.method,
                "k": str(config.stretch_shrinkage_k),
                "min_stretch_gp": str(config.min_stretch_gp_for_direct_weight),
                "risk_lambda": f"{config.risk_lambda:.3f}",
                "max_skaters_per_team": "" if config.max_skaters_per_team is None else str(config.max_skaters_per_team),
                "max_total_from_team": (
                    ""
                    if config.max_total_from_team_including_goalie_team is None
                    else str(config.max_total_from_team_including_goalie_team)
                ),
                "series_lengths": (
                    f"{config.series_lengths.round1:.2f},{config.series_lengths.round2:.2f},"
                    f"{config.series_lengths.round3:.2f},{config.series_lengths.round4:.2f}"
                ),
                "mc_simulations": str(config.monte_carlo_simulations),
                "mean_weighted_score": f"{score.mean_weighted_score:.6f}",
                "min_weighted_score": f"{score.min_weighted_score:.6f}",
                "mean_lineup_delta": f"{score.mean_lineup_delta:.6f}",
                "mean_spearman": f"{score.mean_spearman:.6f}",
                "mean_rmse": f"{score.mean_rmse:.6f}",
                "runtime_sec": f"{runtime_sec:.3f}",
            }
        )

    coarse_scores = sorted(coarse_scores, key=lambda item: (item.mean_weighted_score, item.min_weighted_score), reverse=True)
    coarse_best = coarse_scores[: TUNING_GRID.coarse_top_k]

    refined_scores: list[TuningScore] = []
    for parent in coarse_best:
        for config in _refined_neighbors(parent.config):
            start = time.perf_counter()
            score, _ = _evaluate_config(
                config=config,
                seasons=seasons,
                prune_margin=args.prune_margin,
                realized_root=args.realized_root,
                split_baseline_best=split_baseline_best,
                season_cache=season_cache,
            )
            runtime_sec = time.perf_counter() - start
            refined_scores.append(score)

            run_counter += 1
            all_rows.append(
                {
                    "timestamp_utc": timestamp,
                    "git_commit": git_commit,
                    "run_id": f"run-{run_counter:05d}",
                    "parent_run_id": parent.config.stable_id(),
                    "stage": "refine",
                    "season_set": season_set,
                    "config_id": config.stable_id(),
                    "method": config.method,
                    "k": str(config.stretch_shrinkage_k),
                    "min_stretch_gp": str(config.min_stretch_gp_for_direct_weight),
                    "risk_lambda": f"{config.risk_lambda:.3f}",
                    "max_skaters_per_team": "" if config.max_skaters_per_team is None else str(config.max_skaters_per_team),
                    "max_total_from_team": (
                        ""
                        if config.max_total_from_team_including_goalie_team is None
                        else str(config.max_total_from_team_including_goalie_team)
                    ),
                    "series_lengths": (
                        f"{config.series_lengths.round1:.2f},{config.series_lengths.round2:.2f},"
                        f"{config.series_lengths.round3:.2f},{config.series_lengths.round4:.2f}"
                    ),
                    "mc_simulations": str(config.monte_carlo_simulations),
                    "mean_weighted_score": f"{score.mean_weighted_score:.6f}",
                    "min_weighted_score": f"{score.min_weighted_score:.6f}",
                    "mean_lineup_delta": f"{score.mean_lineup_delta:.6f}",
                    "mean_spearman": f"{score.mean_spearman:.6f}",
                    "mean_rmse": f"{score.mean_rmse:.6f}",
                    "runtime_sec": f"{runtime_sec:.3f}",
                }
            )

    combined_scores = coarse_scores + refined_scores
    combined_scores = [
        item
        for item in combined_scores
        if passes_primary_metric_gate([item.mean_lineup_delta], [item.mean_spearman])
    ]
    combined_scores = sorted(combined_scores, key=lambda item: (item.mean_weighted_score, item.min_weighted_score), reverse=True)
    final_candidates = combined_scores[: args.refine_top_k]

    out_dir = ROOT / "out" / "tuning"
    _write_runs(out_dir / "runs.tsv", all_rows)
    _write_candidates(out_dir / "candidates.tsv", final_candidates)

    print(f"Wrote {out_dir / 'runs.tsv'}")
    print(f"Wrote {out_dir / 'candidates.tsv'}")
    if final_candidates:
        winner = final_candidates[0]
        print(f"Best config: {winner.config.stable_id()} score={winner.mean_weighted_score:.4f}")


if __name__ == "__main__":
    main()
