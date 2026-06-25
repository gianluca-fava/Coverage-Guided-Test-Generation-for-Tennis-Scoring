"""
Experiment runner.

For each combination of (generator, ruleset, seed):
  1. Generate test sequences.
  2. Measure branch coverage.
  3. Compute mutation score.
  4. Write one row to results/results.csv.

Usage:
    python -m experiments.run_experiments [--n N] [--budget B] [--out PATH]

Options:
    --n      N      Number of independent seeds per (generator, ruleset) [default: 30]
    --budget B      Fitness-evaluation budget per run [default: 200]
    --out    PATH   Output CSV path [default: results/results.csv]
    --smoke         Shorthand for --n 3 (quick smoke test)
"""

import argparse
import csv
import os
import shutil
import subprocess
import sys
import time

# Ensure project root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.coverage_tool import measure_branch_coverage
from src import random_generator, search_generator, search_generator_ablation

GENERATORS = {
    "random":   random_generator,
    "search":   search_generator,
    "ablation": search_generator_ablation,
}

RULESETS = ["wimbledon", "usopen", "ausopen"]

RESULTS_DIR = os.path.join(ROOT, "results")
CSV_HEADER = ["generator", "ruleset", "seed", "branch_coverage", "mutation_score", "time_sec"]


# ---------------------------------------------------------------------------
# Mutation score
# ---------------------------------------------------------------------------

def _sequences_to_pytest_source(sequences: list, ruleset: str) -> str:
    """
    Convert *sequences* into a self-contained pytest module string.
    Each sequence becomes one test function.

    Note: sys.path uses os.getcwd() so that mutmut can run this from its
    mutants/ sandbox directory and import the mutated engine correctly.
    """
    lines = [
        "import sys, os",
        "# mutmut v3 trampoline requires module to be imported as 'tennis_engine'",
        "# (not 'src.tennis_engine'). Add src/ subdir to path so the import works",
        "# both in the project root and in mutmut's mutants/ sandbox.",
        "sys.path.insert(0, os.path.join(os.getcwd(), 'src'))",
        "from tennis_engine import TennisMatch",
        "",
    ]
    for i, seq in enumerate(sequences):
        fn_name = f"test_seq_{i:05d}"
        # Build a compact repr of the sequence
        seq_repr = repr(seq)
        lines.append(f"def {fn_name}():")
        lines.append(f"    seq = {seq_repr}")
        lines.append(f"    m = TennisMatch({repr(ruleset)})")
        lines.append(f"    for winner in seq:")
        lines.append(f"        if m.is_over:")
        lines.append(f"            break")
        lines.append(f"        m.play_point(winner)")
        lines.append(f"    assert m.score() is not None")
        lines.append("")
    return "\n".join(lines)


_TEMP_TEST_FILE = os.path.join(ROOT, "tests", "test_generated_temp.py")
_MUTMUT_CACHE   = os.path.join(ROOT, ".mutmut-cache")
_MUTANTS_DIR    = os.path.join(ROOT, "mutants")


def compute_mutation_score(sequences: list, ruleset: str) -> float:
    """
    Write *sequences* to tests/test_generated_temp.py, run mutmut v3
    against src/tennis_engine.py, parse results, return mutation score.

    Returns 0.0 on any error.
    """
    try:
        test_src = _sequences_to_pytest_source(sequences, ruleset)
        with open(_TEMP_TEST_FILE, "w") as f:
            f.write(test_src)

        env = os.environ.copy()

        # Delete only the results cache; keep mutants/ dir (same source = same mutants)
        if os.path.exists(_MUTMUT_CACHE):
            os.remove(_MUTMUT_CACHE)

        # Run mutmut (config in setup.cfg: source_paths + pytest_add_cli_args_test_selection)
        subprocess.run(
            [sys.executable, "-m", "mutmut", "run"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            timeout=300,
        )

        # Retrieve results (--all True → show killed + survived)
        result = subprocess.run(
            [sys.executable, "-m", "mutmut", "results", "--all", "true"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

        score = _parse_mutation_score(result.stdout + result.stderr)
        return score

    except Exception as e:
        print(f"  [mutation score] error: {e}", file=sys.stderr)
        return 0.0
    finally:
        # Clean up temp test file and results cache; keep mutants/ dir
        if os.path.exists(_TEMP_TEST_FILE):
            os.remove(_TEMP_TEST_FILE)
        if os.path.exists(_MUTMUT_CACHE):
            os.remove(_MUTMUT_CACHE)


def _parse_mutation_score(output: str) -> float:
    """
    Parse mutmut v3 results output.

    mutmut results --all outputs lines like:
        mutant_name: killed
        mutant_name: survived
        mutant_name: not checked
    We count killed / (killed + survived) ignoring "not checked".
    """
    killed   = output.count(": killed")
    survived = output.count(": survived")
    total    = killed + survived
    return killed / total if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_all(n_seeds: int, budget: int, out_path: str,
            generator_filter: list = None) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    generators = {
        k: v for k, v in GENERATORS.items()
        if generator_filter is None or k in generator_filter
    }

    # Open CSV (write header if new file)
    file_exists = os.path.exists(out_path)
    with open(out_path, "a", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADER)
        if not file_exists:
            writer.writeheader()

        total_runs = len(generators) * len(RULESETS) * n_seeds
        run_idx = 0

        for gen_name, gen_module in generators.items():
            for ruleset in RULESETS:
                for seed in range(n_seeds):
                    run_idx += 1
                    print(
                        f"[{run_idx:3d}/{total_runs}] "
                        f"generator={gen_name:8s}  ruleset={ruleset:10s}  seed={seed:3d}",
                        flush=True,
                    )

                    t0 = time.perf_counter()

                    # 1. Generate sequences
                    sequences = gen_module.generate(
                        ruleset=ruleset,
                        budget=budget,
                        seed=seed,
                    )

                    # 2. Branch coverage
                    cov_result = measure_branch_coverage(sequences, ruleset)
                    branch_cov = cov_result["branch_coverage"]

                    # 3. Mutation score
                    mut_score = compute_mutation_score(sequences, ruleset)

                    elapsed = time.perf_counter() - t0

                    print(
                        f"         branch_cov={branch_cov:.3f}  "
                        f"mut_score={mut_score:.3f}  "
                        f"time={elapsed:.1f}s",
                        flush=True,
                    )

                    writer.writerow({
                        "generator":      gen_name,
                        "ruleset":        ruleset,
                        "seed":           seed,
                        "branch_coverage": branch_cov,
                        "mutation_score":  mut_score,
                        "time_sec":        round(elapsed, 3),
                    })
                    csv_file.flush()


def main():
    parser = argparse.ArgumentParser(description="Run test generation experiments.")
    parser.add_argument("--n",      type=int,   default=30,
                        help="Number of seeds per (generator, ruleset) [default: 30]")
    parser.add_argument("--budget", type=int,   default=200,
                        help="Fitness-evaluation budget per run [default: 200]")
    parser.add_argument("--out",    type=str,
                        default=os.path.join(ROOT, "results", "results.csv"),
                        help="Output CSV path")
    parser.add_argument("--smoke",  action="store_true",
                        help="Quick smoke test: --n 3")
    parser.add_argument("--generators", nargs="+", choices=list(GENERATORS.keys()),
                        default=None,
                        help="Run only these generators (default: all)")
    args = parser.parse_args()

    if args.smoke:
        args.n = 3

    print(f"Experiment settings: n={args.n}, budget={args.budget}, out={args.out}, "
          f"generators={args.generators or 'all'}")
    run_all(n_seeds=args.n, budget=args.budget, out_path=args.out,
            generator_filter=args.generators)
    print(f"\nDone. Results written to {args.out}")


if __name__ == "__main__":
    main()
