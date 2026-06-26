# A Search-Based Test Generator for Tennis Scoring Engines

**Coverage-Guided Generation vs Random Baseline**

*Alessandro Ligugnana, Gianluca Fava — Software Testing Project (Traccia B)*

---

## Overview

This project designs and evaluates a **search-based test generator** guided by branch coverage, applied to a tennis scoring engine (the System Under Test, SUT). We compare three strategies:

| Generator | Description |
|-----------|-------------|
| `search`  | Search-based (evolutionary); fitness = own branch coverage + novelty bonus over the archive |
| `random`  | Baseline: purely random sequences, same budget |
| `ablation`| Same algorithm as `search` but with constant fitness (no guidance) |

Evaluation metrics: **branch coverage** (coverage.py) and **mutation score** (mutmut).  
Statistical analysis: **Mann-Whitney U** test and **Vargha-Delaney A12** effect size.

---

## Repository Structure

```
.
├── src/
│   ├── tennis_engine.py          # SUT: tennis scoring engine
│   ├── coverage_tool.py          # Branch coverage measurement (coverage.py)
│   ├── random_generator.py       # Baseline random generator
│   ├── search_generator.py       # Search-based (coverage-guided) generator
│   └── search_generator_ablation.py  # Ablation: same algorithm, constant fitness
├── tests/
│   └── test_tennis_engine.py     # Sanity/oracle test suite (24 tests)
├── experiments/
│   ├── run_experiments.py        # Experiment runner (coverage + mutation score)
│   ├── migrate_csv.py            # One-shot: add `budget` column to an old results.csv
│   └── analyze.py                # Statistical analysis + figures (budget-aware)
├── results/
│   ├── results.csv               # Raw results (all runs; includes `budget` column)
│   ├── summary_table.csv         # Statistical summary (per budget)
│   ├── summary_table.txt         # Human-readable summary
│   └── figures/                  # Boxplots (per budget) + budget curves
├── report/
│   ├── report.tex                # Project report (LaTeX, IEEE two-column)
│   ├── refs.bib                  # Bibliography
│   └── report.pdf                # Compiled report
├── CONTRACT.md                   # Internal interface specification
├── setup.cfg                     # mutmut configuration
└── requirements.txt
```

---

## Installation

```bash
# Clone the repository
git clone https://github.com/gianluca-fava/Coverage-Guided-Test-Generation-for-Tennis-Scoring.git
cd Coverage-Guided-Test-Generation-for-Tennis-Scoring

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Running the Sanity Test Suite

The suite in `tests/test_tennis_engine.py` acts as correctness oracle for the engine.

```bash
python -m pytest tests/ -v
```

Expected: **24 tests passing**.

To also measure branch coverage of the engine:

```bash
python -m pytest tests/ --cov=src.tennis_engine --cov-branch --cov-report=term-missing
```

---

## Measuring Branch Coverage Manually

```python
from src.coverage_tool import measure_branch_coverage

result = measure_branch_coverage(
    sequences=[["A", "B", "A", "B"] * 30],
    ruleset="usopen"
)
print(result["branch_coverage"])   # float in [0, 1]
print(result["total_branches"])    # int
```

---

## Running mutmut (Mutation Testing)

mutmut is configured via `setup.cfg` to mutate only `src/tennis_engine.py`.  
To run mutation testing against the sanity suite manually:

```bash
# Ensure tests/test_generated_temp.py exists (or adapt setup.cfg)
python -m mutmut run
python -m mutmut results --all true
```

---

## Reproducing the Experiments

Mutation testing (mutmut) dominates the runtime, so timings are much larger than
plain test execution. Estimates below are indicative on a recent laptop.

### Quick smoke test (N=3 seeds, ~15–25 minutes)

```bash
python -m experiments.run_experiments --smoke --budget 200
```

### Full experiment, single budget (N=30 seeds, ~4–5 hours)

```bash
python -m experiments.run_experiments --n 30 --budget 200
```

### Two-regime / multi-budget design (the design used in the report)

The evaluation uses several budget regimes to study how the value of coverage
guidance changes with the search budget. Each run is tagged with a `budget`
column in `results/results.csv`. Run one budget at a time (results are appended):

```bash
python -m experiments.run_experiments --n 30 --budget 20
python -m experiments.run_experiments --n 30 --budget 60
python -m experiments.run_experiments --n 30 --budget 200
```

The full three-budget design at N=30 (810 runs) takes roughly **6–7 hours**.
The `--generators` flag (e.g. `--generators search ablation`) reruns only a
subset, which is useful to resume after an interruption.

> **Migrating an older results file.** A `results.csv` produced before the
> `budget` column existed can be upgraded once with
> `python -m experiments.migrate_csv` (it back-fills `budget=200`).

### Statistical analysis and figures

```bash
python -m experiments.analyze
```

Outputs (budget-aware):
- `results/figures/boxplot_branch_coverage_<ruleset>_b<budget>.png`
- `results/figures/boxplot_mutation_score_b<budget>.png`
- `results/figures/budget_curve_branch_coverage.png` and
  `results/figures/budget_curve_mutation_score.png` (median ± IQR vs budget)
- `results/summary_table.csv` and `results/summary_table.txt` (per-budget
  Mann-Whitney U + A12)

---

## SUT Description

`src/tennis_engine.py` implements a full tennis match scorer supporting three tournament rulesets that differ in the decisive-set tie-break rule:

| Ruleset   | Decisive-set tie-break |
|-----------|------------------------|
| `wimbledon` | First to 10 pts, 2-pt margin |
| `usopen`   | Standard: first to 7 pts, 2-pt margin |
| `ausopen`  | Super tie-break: first to 10 pts, 2-pt margin |

---

## Search-Based Generator

The generator (`src/search_generator.py`) implements a coverage-guided evolutionary algorithm:

1. **Initialise** a population of random point sequences.
2. For each generation:
   - **Execute** each candidate against `TennisMatch`.
   - **Measure fitness**: the candidate's own branch coverage `|C(s)|` plus a
     novelty bonus `|C(s) \ A|` for arcs not yet in the archive `A`. The
     own-coverage term keeps a non-zero selection gradient even after the
     archive saturates (a novelty-only fitness collapses to 0 on a small SUT).
   - **Identify promising** candidates (elites by fitness).
   - **Mutate** elites (flip point, insert/delete point, block replacement, extend; also crossover).
3. Accumulate all evaluated sequences in an archive (the returned test suite).

The **ablation variant** (`src/search_generator_ablation.py`) delegates to the
exact same algorithm with a constant fitness = 0, so population, selection,
operators and RNG usage are identical and **only the fitness differs** — this
isolates the contribution of the coverage-guided fitness function.

### Oracle of the generated tests

Generated sequences have no known expected score, so each generated test asserts
**state invariants** of the contract after *every* `play_point` (key set of
`score()`, valid ranges for sets/games/points, `is_over`/`winner` consistency,
monotonicity, terminal `RuntimeError`, rejection of invalid input). A strong
oracle is essential for a meaningful mutation score: a null oracle (e.g. only
`assert score() is not None`) kills only mutants that *crash*, not those that
silently corrupt the score.

---

## AI Use Disclosure

Code, test scripts, statistical analysis, and this README were developed with assistance from an AI coding assistant (Claude, Anthropic). All generated code was reviewed, tested, and validated by the authors. The algorithm design, experimental protocol, and interpretation of results are the authors' own work.

---

## Authors

- Alessandro Ligugnana
- Gianluca Fava
