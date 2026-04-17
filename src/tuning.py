from __future__ import annotations

from dataclasses import dataclass

from config import TuningConfig


@dataclass(frozen=True)
class TuningScore:
    config: TuningConfig
    mean_weighted_score: float
    min_weighted_score: float
    mean_lineup_delta: float
    mean_spearman: float
    mean_rmse: float


def weighted_validation_score(*, lineup_delta: float, spearman: float, rmse: float) -> float:
    return (0.60 * lineup_delta) + (0.35 * spearman) - (0.05 * rmse)


def passes_primary_metric_gate(lineup_delta_values: list[float], spearman_values: list[float]) -> bool:
    if not lineup_delta_values or not spearman_values:
        return False
    return min(lineup_delta_values) > 0 and (sum(spearman_values) / len(spearman_values)) >= 0.0
