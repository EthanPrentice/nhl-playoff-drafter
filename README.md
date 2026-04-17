# NHL Playoff Drafter

A data-driven playoff fantasy drafting tool for NHL skaters and goalie **teams**.

This project currently provides:
- TSV-based data loading with validation/diagnostics,
- heuristic team/player valuation,
- typed projection contracts and scoring helpers,
- lineup optimization under exact roster constraints (5F / 3D / 2 goalie teams),
- a backtesting/calibration harness across historical seasons and parameter grids,
- ranked output exports for downstream draft decisions.

---

## Table of Contents

- [What this tool does](#what-this-tool-does)
- [Current scoring/roster assumptions](#current-scoringroster-assumptions)
- [Repository structure](#repository-structure)
- [Architecture overview](#architecture-overview)
- [Data inputs](#data-inputs)
- [How to run](#how-to-run)
- [Outputs](#outputs)
- [Testing](#testing)
- [Development workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

---

## What this tool does

At a high level, the pipeline:
1. Loads and validates team/player TSV data.
2. Joins season/stretch/previous-season player rows by `(Name, Team)`.
3. Computes team-level heuristic values.
4. Computes player heuristic values.
5. Builds typed projection inputs and projected values.
6. Selects a lineup under roster constraints.
7. Writes ranked TSV outputs to `out/season_2026`.
8. Optionally runs historical backtests and writes metrics to `out/backtest`.

The current optimizer is intentionally simple (greedy by projected value) and is planned to be replaced by a constrained optimization model in a follow-up phase.

---

## Current scoring/roster assumptions

### Scoring
- **Skaters**
  - Goal = 1
  - Assist = 1
  - OT goal bonus = +1 (OT goals effectively count as 2 total)
- **Goalie teams**
  - Win = 1
  - Goalie assist = 1
  - Shutout = 5

### Roster constraints
- 5 Forwards
- 3 Defense
- 2 Goalie teams

Defaults are defined in `src/config.py` and used throughout the pipeline.

---

## Repository structure

```text
.
├── docs/
│   └── heuristics_implementation_plan.md
├── resources/
│   ├── 2024/
│   ├── 2025/
│   └── 2026/
├── src/
│   ├── config.py
│   ├── contracts.py
│   ├── data_loader.py
│   ├── heuristics.py
│   ├── models.py
│   ├── optimizer.py
│   ├── player.py
│   ├── playoff_draft.py
│   ├── reporting.py
│   ├── scoring.py
│   └── team.py
├── tests/
│   ├── test_config.py
│   └── test_data_loader.py
└── README.md
```

---

## Architecture overview

### `src/playoff_draft.py` (orchestration)
Entry point that wires the pipeline end-to-end:
- load data,
- apply heuristics,
- project skaters/goalie teams,
- optimize lineup,
- write outputs,
- print diagnostics.

### `src/config.py`
Central location for:
- scoring constants,
- roster constraints,
- path/file constants,
- model tuning defaults (e.g., stretch shrinkage constant).

### `src/data_loader.py`
Responsible for ingesting TSV inputs and producing structured objects:
- validates required columns,
- joins players by `(Name, Team)`,
- tracks load diagnostics (`loaded`, `skipped`, reasons),
- supports `strict` mode (fail on row drops),
- exposes typed conversion helpers for modeling.

### `src/contracts.py`
Typed dataclasses used to pass model inputs between modules.

### `src/scoring.py`
Pure, test-friendly scoring functions:
- skater score from raw or summary stats,
- goalie-team score,
- per-game rate,
- season/stretch blending.

### `src/models.py`
Projection layer that transforms typed inputs + expected team games into projected values.

### `src/optimizer.py`
Lineup selection module. Current implementation is deterministic greedy top-N by position, constrained by roster slots.

### `src/reporting.py`
Output writers for ranked team and skater TSV files.

### `src/heuristics.py`
Legacy and current heuristic functions for team/player estimated values.

---

## Data inputs

Input files are expected under `resources/2026` by default:
- `teams.tsv`
- `players_season.tsv`
- `players_stretch.tsv`
- `players_prev_season.tsv`

> Important: input format is intentionally preserved; the project assumes existing TSV schemas and tab delimiters.

If required columns are missing, loading fails early with an explicit error.

---

## How to run

From repository root:

```bash
python src/playoff_draft.py
```

Expected terminal output includes:
- loader diagnostics summary,
- optimized lineup slot counts,
- `SUCCESS` on completion.

---

## Outputs

Generated under `out/season_2026/`:
- `teams.tsv`
- `all.tsv`
- `forwards.tsv`
- `defense.tsv`

`all.tsv` contains full ranked skater output; forwards/defense are split filtered views.

---

## Testing

Run all current unit tests:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

Current test coverage includes:
- config defaults (`tests/test_config.py`),
- data loader validation and strict-mode behavior (`tests/test_data_loader.py`),
- scoring/model/optimizer behavior and backtest metric math (`tests/test_*.py`).

Run the backtesting harness:

```bash
python scripts/backtest.py --seasons 2024 2025 --method analytic --k-values 10 20 30 --risk-lambda-grid 0 0.1 0.2
```

Backtesting compares projections built from `resources/<season>/players_season.tsv` + `players_stretch.tsv`
against realized playoff outcomes from:

- required: `resources/<season>/players_playoffs.tsv` (same schema as `players_season.tsv`)
- optional: `resources/<season>/teams_playoffs.tsv` (`Name`, `EV`) for goalie-team realized scoring

If you keep realized files outside `resources/<season>/`, provide explicit files via `--realized-root`:

```bash
python scripts/backtest.py --seasons 2025 --method analytic --realized-root /path/to/realized
```

Expected files under `--realized-root`:
- `season_<year>_skaters.tsv` with columns: `Name`, `Team`, `Pos`, `P`, `OTG` (`OTG` optional)
- optional `season_<year>_goalie_teams.tsv` with columns: `Name`, `EV`

Backtesting outputs:
- `out/backtest/summary.tsv`
- `out/backtest/season_<year>_details.tsv`

---

## Development workflow

### Branch strategy
This project uses stacked branches with the `codex/improveHeuristics/*` convention. See `docs/heuristics_implementation_plan.md` for current phase ordering.

### Coding guidance
- Keep modules focused on single responsibilities.
- Prefer typed contracts over unstructured dict passing between pipeline stages.
- Keep scoring/model functions pure where possible for easier testing.
- Do not change resource input formats unless explicitly requested.

### Adding dependencies
Only add widely supported libraries. If you add any package, include/update `requirements.txt`.

---

## Troubleshooting

### `ValueError: File <name> missing required columns`
Your TSV schema does not contain required fields. Compare against expected columns in `DataLoader.REQUIRED_*_COLUMNS`.

### Fewer players than expected in outputs
Check loader diagnostics printed by the main script. Common reasons:
- no stretch row match,
- team code mismatch between players and teams files.

### Strict mode failures
If `strict=True` is enabled in `DataLoader`, any skipped rows raise an error by design.

---

## Roadmap

See the detailed implementation roadmap in:
- `docs/heuristics_implementation_plan.md`

Near-term planned upgrades:
- formal expected-games model (analytic + Monte Carlo),
- stronger optimizer (ILP/OR tools),
- richer goalie-team projections with actual goalie-team rate inputs,
- backtesting harness and calibration.
