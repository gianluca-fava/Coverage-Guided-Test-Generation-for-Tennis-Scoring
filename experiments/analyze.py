"""
Statistical analysis and figure generation.

Reads results/results.csv and produces:
  - results/figures/boxplot_branch_coverage_<ruleset>.png  (one per ruleset)
  - results/figures/boxplot_mutation_score.png
  - results/summary_table.csv
  - results/summary_table.txt  (human-readable)

Statistical tests (search vs random, search vs ablation per ruleset):
  - Mann-Whitney U  (scipy.stats.mannwhitneyu)
  - Vargha-Delaney A12 effect size (implemented from scratch)
"""

import os
import sys

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_CSV  = os.path.join(ROOT, "results", "results.csv")
FIGURES_DIR  = os.path.join(ROOT, "results", "figures")
SUMMARY_CSV  = os.path.join(ROOT, "results", "summary_table.csv")
SUMMARY_TXT  = os.path.join(ROOT, "results", "summary_table.txt")

GENERATORS = ["random", "search", "ablation"]
RULESETS   = ["wimbledon", "usopen", "ausopen"]

GENERATOR_COLORS = {
    "random":   "#4C72B0",
    "search":   "#DD8452",
    "ablation": "#55A868",
}


# ---------------------------------------------------------------------------
# Vargha-Delaney A12
# ---------------------------------------------------------------------------

def a12(a, b):
    """
    Vargha-Delaney A12 effect size.

    A12 > 0.5  means treatment *a* tends to outperform *b*.
    A12 = 0.5  means no difference.
    A12 < 0.5  means *b* tends to outperform *a*.
    """
    more = same = 0.0
    for x in a:
        for y in b:
            if x == y:
                same += 1
            elif x > y:
                more += 1
    return (more + 0.5 * same) / (len(a) * len(b))


def interpret_a12(value: float) -> str:
    """Qualitative interpretation of A12."""
    diff = abs(value - 0.5)
    if diff < 0.056:
        return "negligible"
    elif diff < 0.14:
        return "small"
    elif diff < 0.21:
        return "medium"
    else:
        return "large"


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def _boxplot(data_dict: dict, title: str, ylabel: str, out_path: str) -> None:
    """
    data_dict: {label: list_of_values, ...}
    """
    fig, ax = plt.subplots(figsize=(7, 5))
    labels = list(data_dict.keys())
    values = [data_dict[k] for k in labels]
    colors = [GENERATOR_COLORS.get(k, "#888888") for k in labels]

    bplot = ax.boxplot(values, patch_artist=True, notch=False, vert=True,
                       medianprops=dict(color="black", linewidth=2))
    for patch, color in zip(bplot["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_ylim(0, 1.05)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def main():
    os.makedirs(FIGURES_DIR, exist_ok=True)

    if not os.path.exists(RESULTS_CSV):
        print(f"ERROR: {RESULTS_CSV} not found. Run run_experiments.py first.")
        sys.exit(1)

    df = pd.read_csv(RESULTS_CSV)
    print(f"Loaded {len(df)} rows from {RESULTS_CSV}\n")

    summary_rows = []

    # ------------------------------------------------------------------
    # 1. Boxplots: branch coverage per ruleset
    # ------------------------------------------------------------------
    for ruleset in RULESETS:
        sub = df[df["ruleset"] == ruleset]
        data = {}
        for gen in GENERATORS:
            vals = sub[sub["generator"] == gen]["branch_coverage"].tolist()
            if vals:
                data[gen] = vals

        out_path = os.path.join(FIGURES_DIR, f"boxplot_branch_coverage_{ruleset}.png")
        _boxplot(
            data,
            title=f"Branch Coverage — {ruleset.capitalize()}",
            ylabel="Branch Coverage",
            out_path=out_path,
        )
        print(f"Saved {out_path}")

    # ------------------------------------------------------------------
    # 2. Boxplot: mutation score (all rulesets combined)
    # ------------------------------------------------------------------
    data_ms = {}
    for gen in GENERATORS:
        vals = df[df["generator"] == gen]["mutation_score"].tolist()
        if vals:
            data_ms[gen] = vals

    out_ms = os.path.join(FIGURES_DIR, "boxplot_mutation_score.png")
    _boxplot(
        data_ms,
        title="Mutation Score (all rulesets)",
        ylabel="Mutation Score",
        out_path=out_ms,
    )
    print(f"Saved {out_ms}")

    # ------------------------------------------------------------------
    # 3. Statistical tests and summary table
    # ------------------------------------------------------------------
    comparisons = [("search", "random"), ("search", "ablation")]
    metrics = ["branch_coverage", "mutation_score"]

    print("\n=== Statistical Summary ===\n")
    header = ["ruleset", "metric", "pair",
              "median_A", "median_B",
              "p_value", "A12", "effect"]
    print(("{:<12} {:<18} {:<20} {:>8} {:>8} {:>10} {:>6} {:>12}".format(*header)))
    print("-" * 100)

    for ruleset in RULESETS:
        sub = df[df["ruleset"] == ruleset]
        for metric in metrics:
            # Medians per generator
            medians = {}
            for gen in GENERATORS:
                vals = sub[sub["generator"] == gen][metric].tolist()
                medians[gen] = (np.median(vals) if vals else float("nan"), vals)

            for (gen_a, gen_b) in comparisons:
                med_a, vals_a = medians.get(gen_a, (float("nan"), []))
                med_b, vals_b = medians.get(gen_b, (float("nan"), []))

                if len(vals_a) < 2 or len(vals_b) < 2:
                    p_val = float("nan")
                    a12_val = float("nan")
                    effect = "n/a"
                else:
                    stat, p_val = stats.mannwhitneyu(vals_a, vals_b, alternative="two-sided")
                    a12_val = a12(vals_a, vals_b)
                    effect = interpret_a12(a12_val)

                pair_str = f"{gen_a} vs {gen_b}"
                print(("{:<12} {:<18} {:<20} {:>8.3f} {:>8.3f} {:>10.4f} {:>6.3f} {:>12}".format(
                    ruleset, metric, pair_str, med_a, med_b, p_val, a12_val, effect
                )))

                summary_rows.append({
                    "ruleset":   ruleset,
                    "metric":    metric,
                    "pair":      pair_str,
                    "median_A":  round(med_a, 4),
                    "median_B":  round(med_b, 4),
                    "p_value":   round(p_val, 6),
                    "A12":       round(a12_val, 4),
                    "effect":    effect,
                })
        print()

    # ------------------------------------------------------------------
    # 4. Medians overview per (generator, ruleset)
    # ------------------------------------------------------------------
    print("\n=== Medians per (generator, ruleset) ===\n")
    pivot_cov = df.groupby(["generator", "ruleset"])["branch_coverage"].median().unstack()
    pivot_mut = df.groupby(["generator", "ruleset"])["mutation_score"].median().unstack()
    print("Branch Coverage (median):")
    print(pivot_cov.to_string())
    print("\nMutation Score (median):")
    print(pivot_mut.to_string())

    # ------------------------------------------------------------------
    # 5. Save summary CSV and TXT
    # ------------------------------------------------------------------
    summary_df = pd.DataFrame(summary_rows, columns=header)
    summary_df.to_csv(SUMMARY_CSV, index=False)
    print(f"\nSaved summary CSV → {SUMMARY_CSV}")

    with open(SUMMARY_TXT, "w") as f:
        f.write("=== Statistical Summary ===\n\n")
        f.write(summary_df.to_string(index=False))
        f.write("\n\n=== Branch Coverage Medians ===\n\n")
        f.write(pivot_cov.to_string())
        f.write("\n\n=== Mutation Score Medians ===\n\n")
        f.write(pivot_mut.to_string())
    print(f"Saved summary TXT  → {SUMMARY_TXT}")


if __name__ == "__main__":
    main()
