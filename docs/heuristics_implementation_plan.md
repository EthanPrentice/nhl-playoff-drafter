# NHL Playoff Drafter — Detailed Heuristics Implementation Plan

Date: 2026-04-17

This plan is intentionally implementation-level (file-by-file, function-by-function), not just conceptual.

---

## Constraints and non-goals

- **Do not change input resource format** in `resources/*/*.tsv` (column names and delimiter remain as-is).
- Preserve current CLI usage: `python src/playoff_draft.py` should still work.
- Backward compatibility target: existing output files (`all.tsv`, `forwards.tsv`, `defense.tsv`, `teams.tsv`) continue to be produced.
- Optional external libraries are allowed **only** if broadly trusted and maintained; if used, add `requirements.txt`.

---

## 1) Cleanup + architecture prep (first task)

### Objective
Create a stable foundation so scoring/model/optimizer changes can be added without repeatedly editing I/O glue code.

### Implementation details

#### 1.1 Module boundaries
Create/standardize the following modules and responsibilities:

- `src/config.py`
  - scoring constants (skater + goalie-team)
  - roster constraints (5F/3D/2G-team)
  - dataset + output paths
- `src/data_loader.py`
  - TSV read helpers
  - required-column validation
  - keyed joins by `(Name, Team)`
  - load diagnostics (matched/missing counts)
- `src/scoring.py` (new)
  - pure stat-to-fantasy conversion functions
  - no file or global I/O
- `src/models.py` (new)
  - expected-games estimators
  - skater and goalie-team EV models
- `src/optimizer.py` (new)
  - lineup optimizer with exact roster constraints
- `src/reporting.py` (new)
  - output writers and ranking/lineup tables
- `src/playoff_draft.py`
  - orchestration only (load -> model -> optimize -> write)

#### 1.2 Data contracts
Define typed intermediate records (dataclass or TypedDict) so modules pass structured objects instead of raw dicts.

- `SkaterProjectionInput`
  - `name`, `team`, `position`, `season_gp`, `season_p`, `season_otg`, `stretch_gp`, `stretch_p`, `stretch_otg`, optional prior-season equivalents
- `GoalieTeamProjectionInput`
  - `team`, `season_wins`, `season_goaltender_assists`, `season_shutouts`, `team_odds`
- `TeamOddsInput`
  - `team`, `round1`, `round2`, `conference`, `final`

#### 1.3 Validation behavior
- Hard-fail on missing required columns.
- Soft-warn and skip rows when numeric parsing fails.
- Emit summary diagnostics:
  - loaded row counts
  - matched skaters
  - unmatched by reason (`no_stretch_match`, `no_team_match`, etc.)

#### 1.4 Test scaffolding
Add:
- `tests/test_data_loader.py`
  - required-column failures
  - join correctness for duplicate names on different teams
- `tests/test_config.py`
  - scoring and roster defaults

### Acceptance criteria
- Main script still runs with unchanged resources.
- Join logic is keyed (no nested O(n^3) loops).
- Data loader emits deterministic counts for matched/unmatched rows.

---

## 2) Formal scoring model layer

### Objective
Encode your exact league scoring rules as explicit formulas.

### Scoring rules to implement
- Skaters: `1*G + 1*A + 1*OTG_bonus`
  - Equivalent in aggregate: `P + OTG`
- Goalie teams: `1*W + 1*GoalieAssists + 5*SO`

### Implementation details

#### 2.1 `src/scoring.py`
Implement pure helpers:

- `skater_points_raw(goals, assists, ot_goals) -> float`
- `skater_points_from_summary(points, ot_goals) -> float`  
  (used when only `P` and `OTG` are present)
- `goalie_team_points_raw(wins, assists, shutouts) -> float`
- `rate_per_game(total_points, games_played) -> float`
- `blend_rates(season_rate, stretch_rate, stretch_gp, k) -> float`

#### 2.2 Parameterization
Expose tunables in config:
- `STRETCH_SHRINKAGE_K` (default `20`)
- `MIN_STRETCH_GP_FOR_DIRECT_WEIGHT` (default `10`)

#### 2.3 Unit tests
- exact formula checks for representative rows
- edge cases: `GP=0`, missing OTG, small stretch sample

### Acceptance criteria
- All scoring math is implemented in one module.
- No heuristic function hard-codes raw multipliers directly in orchestration code.

---

## 3) Expected playoff games model

### Objective
Replace ad hoc team multipliers with explicit expected games per team.

### Implementation details

#### 3.1 Analytic estimator (`src/models.py`)
Given cumulative advancement probabilities (`R1`, `R2`, `CF`, `F`), compute:

- independent round probs:
  - `p1 = R1`
  - `p2 = R2 / R1` (if `R1>0` else 0)
  - `p3 = CF / R2` (if `R2>0` else 0)
  - `p4 = F / CF` (if `CF>0` else 0)
- expected games:
  - baseline appearance in round 1 plus continuation expectation
  - use configurable expected series length constants (`E_LEN_R1..R4`, default `5.9` each)

#### 3.2 Monte Carlo estimator (`src/models.py`)
- run `N` simulations (default `20_000`)
- for each round, sample advance with independent round probs
- sample series length from empirical discrete distribution over `{4,5,6,7}`
- record team game totals, return mean/std/p10/p90

#### 3.3 Model selector
- config key: `EXPECTED_GAMES_METHOD = "analytic" | "monte_carlo"`
- fallback to analytic if Monte Carlo fails

#### 3.4 Tests
- sanity: stronger teams have higher expected games
- monotonicity checks when probabilities increase

### Acceptance criteria
- Team EV uses expected games rather than raw summed odds.
- Both methods available behind config flag.

---

## 4) Roster optimizer (5F / 3D / 2 goalie teams)

### Objective
Generate an actual best lineup under hard roster constraints.

### Implementation details

#### 4.1 Dependency decision
Preferred first choice: `pulp` (widely used, simple LP API).  
If added, include `requirements.txt` with pinned major versions.

#### 4.2 `src/optimizer.py`
Implement:
- `optimize_lineup(forwards, defense, goalie_teams, constraints, risk_lambda=0.0)`
- binary decision vars per candidate
- hard constraints:
  - exactly 5 forwards
  - exactly 3 defense
  - exactly 2 goalie teams
- optional constraints:
  - `max_skaters_per_team`
  - `max_total_from_team_including_goalie_team`

Objective:
- default: maximize expected points
- optional risk-adjusted objective: maximize `E - lambda*SD`

#### 4.3 Tests
- constraint satisfaction always exact
- deterministic output on fixed toy data
- tie-breaking deterministic by stable key sort

### Acceptance criteria
- Produces one valid optimal lineup and objective value.
- Can emit top-N alternative lineups by exclusion constraints (optional).

---

## 5) Data reliability + quality diagnostics

### Objective
Harden ingest/projection pipeline and make data issues visible.

### Implementation details

- Add explicit parse helpers with contextual errors (`file`, `row`, `column`).
- Track per-file null/missing counts for critical fields (`GP`, `P`, `OTG`, odds columns).
- Add `--strict` mode:
  - strict: fail on any dropped row
  - default: continue with warning and report
- Write diagnostics report to `out/season_2026/diagnostics.tsv`.

### Tests
- parser behavior in strict vs non-strict mode
- diagnostics output shape and counts

### Acceptance criteria
- Every dropped row is accounted for with a reason code.
- Pipeline behavior is predictable under malformed data.

---

## 6) Backtesting + calibration harness

### Objective
Quantify whether new heuristics outperform the baseline.

### Implementation details

#### 6.1 Script
Add `scripts/backtest.py` with args:
- `--seasons 2024 2025`
- `--method analytic|monte_carlo`
- `--k-values 10 20 30`
- `--risk-lambda-grid 0 0.1 0.2`

#### 6.2 Workflow
For each season:
1. load historical input snapshot
2. generate projections
3. build optimized lineup
4. compare against realized playoff fantasy points

#### 6.3 Metrics
- Spearman rank correlation (overall and by position)
- Top-K precision/recall by position
- MAE/RMSE for projected vs realized points
- lineup realized points vs baseline lineup

#### 6.4 Outputs
- `out/backtest/summary.tsv`
- `out/backtest/season_<year>_details.tsv`
- optional markdown summary report

### Acceptance criteria
- Reproducible backtest command.
- At least two metrics improve vs existing baseline.

---

## 7) Reporting outputs for draft decisions

### Objective
Make outputs decision-ready for actual drafting.

### Implementation details

#### 7.1 Ranking exports
- `forwards.tsv`: rank, EV, floor/ceiling, key rates
- `defense.tsv`: same fields
- `goalie_teams.tsv`: EV breakdown (`W`, `A`, `SO`, expected games)

#### 7.2 Lineup exports
- `optimal_lineup.tsv`
- `alternative_lineups.tsv` (high-floor and high-ceiling variants)
- `team_exposure.tsv` (selected shares by NHL team)

#### 7.3 Explainability fields
For each candidate include:
- contribution breakdown (`team_games_factor`, `rate_factor`, shrinkage weight)
- confidence band from MC or proxy variance

### Acceptance criteria
- Outputs clearly explain why each pick is ranked.
- One-command run produces all artifacts.

---

## Sequential stacked-branch workflow (no Graphite; branch prefix `codex/improveHeuristics/`)

Each task ships on its own branch, each branch based on previous branch head.

1. `codex/improveHeuristics/initialCleanup` (current branch for cleanup + plan)
2. `codex/improveHeuristics/scoring-model` (base: `codex/improveHeuristics/initialCleanup`)
3. `codex/improveHeuristics/expected-games` (base: `codex/improveHeuristics/scoring-model`)
4. `codex/improveHeuristics/optimizer` (base: `codex/improveHeuristics/expected-games`)
5. `codex/improveHeuristics/data-reliability` (base: `codex/improveHeuristics/optimizer`)
6. `codex/improveHeuristics/backtesting` (base: `codex/improveHeuristics/data-reliability`)
7. `codex/improveHeuristics/reporting` (base: `codex/improveHeuristics/backtesting`)

### Per-branch execution checklist
- Implement only scoped files/functions for the branch.
- Add/adjust tests for that scope.
- Run:
  - `python src/playoff_draft.py`
  - `pytest` (once tests are added)
- Commit with phase-specific message.
- Open PR targeting previous stack branch.
- Rebase/retarget open stack PRs after merges.

### Merge policy
- Merge only when branch acceptance criteria are satisfied.
- Do not start next phase code until previous phase CI is green.
