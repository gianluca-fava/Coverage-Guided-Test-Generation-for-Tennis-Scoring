"""
One-shot migration: add a `budget` column to results/results.csv.

Historical data was produced before the two-regime (budget) design and uses
the old 6-column schema:

    generator,ruleset,seed,branch_coverage,mutation_score,time_sec

This script rewrites the file in the new 7-column schema, inserting
`budget=200` for every existing row (all historical runs used budget 200):

    generator,ruleset,seed,budget,branch_coverage,mutation_score,time_sec

It is idempotent: if the file is already in the new format (header already
contains `budget`), it does nothing.

Usage:
    python -m experiments.migrate_csv [--csv PATH] [--budget N]
"""

import argparse
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CSV = os.path.join(ROOT, "results", "results.csv")

OLD_HEADER = ["generator", "ruleset", "seed", "branch_coverage", "mutation_score", "time_sec"]
NEW_HEADER = ["generator", "ruleset", "seed", "budget", "branch_coverage", "mutation_score", "time_sec"]


def migrate(csv_path: str, budget: int) -> None:
    if not os.path.exists(csv_path):
        print(f"ERROR: {csv_path} not found.")
        sys.exit(1)

    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        print(f"ERROR: {csv_path} is empty.")
        sys.exit(1)

    header = rows[0]

    if header == NEW_HEADER:
        print(f"Already migrated (header already contains 'budget'). No changes made.")
        return

    if header != OLD_HEADER:
        print(f"ERROR: unexpected header, refusing to migrate.\n"
              f"  found:    {header}\n  expected: {OLD_HEADER}")
        sys.exit(1)

    data_rows = rows[1:]
    seed_idx = OLD_HEADER.index("seed")

    migrated = []
    for r in data_rows:
        if len(r) != len(OLD_HEADER):
            print(f"ERROR: malformed row (expected {len(OLD_HEADER)} fields): {r}")
            sys.exit(1)
        # Insert budget value right after the 'seed' column.
        new_r = r[: seed_idx + 1] + [str(budget)] + r[seed_idx + 1:]
        migrated.append(new_r)

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(NEW_HEADER)
        writer.writerows(migrated)

    print(f"Migrated {len(migrated)} rows in {csv_path} (budget={budget} added to all).")


def main():
    parser = argparse.ArgumentParser(description="Add budget column to results.csv.")
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Path to results CSV.")
    parser.add_argument("--budget", type=int, default=200,
                        help="Budget value to assign to existing rows [default: 200].")
    args = parser.parse_args()
    migrate(args.csv, args.budget)


if __name__ == "__main__":
    main()
