# A Search-Based Test Generator for Tennis Scoring Engines

**Coverage-Guided Generation vs Random Baseline**

*Alessandro Ligugnana, Gianluca Fava — Software Testing Project (Traccia B)*

---

## Overview

This project designs and evaluates a **search-based test generator** guided by branch coverage, applied to a tennis scoring engine (the System Under Test, SUT). We compare three strategies:

| Generator | Description |
|-----------|-------------|
| `search`  | Search-based (evolutionary), fitness = new branch arcs covered |
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
│   └── analyze.py                # Statistical analysis + figures
├── results/
│   ├── results.csv               # Raw results (all runs)
│   ├── summary_table.csv         # Statistical summary
│   ├── summary_table.txt         # Human-readable summary
│   └── figures/                  # Boxplots
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
python -m pytest tests/ --cov=src/tennis_engine --cov-branch --cov-report=term-missing
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

### Quick smoke test (N=3 seeds, ~2 minutes)

```bash
python -m experiments.run_experiments --smoke --budget 200
```

### Full experiment (N=30 seeds, ~40 minutes)

```bash
python -m experiments.run_experiments --n 30 --budget 200
```

This writes `results/results.csv` with all data.

### Statistical analysis and figures

```bash
python -m experiments.analyze
```

Outputs:
- `results/figures/boxplot_branch_coverage_<ruleset>.png` — one boxplot per ruleset
- `results/figures/boxplot_mutation_score.png`
- `results/summary_table.csv` and `results/summary_table.txt`

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
   - **Measure fitness**: count branch arcs newly covered beyond the running archive.
   - **Identify promising** candidates (elites by fitness + tournament selection).
   - **Mutate** elites (flip point, insert/delete point, block replacement, extend; also crossover).
3. Accumulate all evaluated sequences in an archive.

The **ablation variant** (`src/search_generator_ablation.py`) uses constant fitness = 0, degenerating selection into random choice — isolating the contribution of the coverage-guided fitness function.

---

## AI Use Disclosure

Code, test scripts, statistical analysis, and this README were developed with assistance from an AI coding assistant (Claude, Anthropic). All generated code was reviewed, tested, and validated by the authors. The algorithm design, experimental protocol, and interpretation of results are the authors' own work.

---

## Authors

- Alessandro Ligugnana
- Gianluca Fava
