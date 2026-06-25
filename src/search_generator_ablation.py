"""
Ablation variant of the search-based generator.

Identical algorithm to search_generator.py but with a *degraded* fitness
function: fitness is always a constant (0), so the selection pressure is
completely removed and the generator degenerates into a blind random walk.

This ablation study isolates the contribution of the coverage-guided fitness:
if the ablation variant performs similarly to the full search, the fitness
function adds no value; if it performs worse, the fitness is essential.
"""

import random
from typing import Optional

from src.search_generator import _mutate, _crossover


# ---------------------------------------------------------------------------
# Degraded fitness — constant zero, ignores coverage completely
# ---------------------------------------------------------------------------

def _fitness_ablation(seq: list, archive_branches: set, ruleset: str):
    """Fitness is always 0 — no guidance from branch coverage."""
    return 0, set()


# ---------------------------------------------------------------------------
# Main generator (ablation)
# ---------------------------------------------------------------------------

def generate(
    ruleset: str,
    budget: int = 200,
    pop_size: int = 20,
    elite_ratio: float = 0.3,
    min_len: int = 4,
    max_len: int = 400,
    seed: Optional[int] = None,
) -> list:
    """
    Ablation generator: same structure as search_generator but with
    constant fitness (no coverage guidance).

    Parameters
    ----------
    Same as search_generator.generate().

    Returns
    -------
    list[list[str]]
    """
    rng = random.Random(seed)
    evaluations = 0

    archive_branches: set = set()
    archive_sequences: list = []

    # --- Initialise population ---
    population = []
    for _ in range(pop_size):
        if evaluations >= budget:
            break
        length = rng.randint(min_len, max_len)
        seq = [rng.choice(["A", "B"]) for _ in range(length)]
        population.append(seq)
        evaluations += 1

    if population:
        archive_sequences.extend(population)

    # --- Generational loop ---
    while evaluations < budget:
        # (a+b) Execute & measure fitness — always 0
        scored = []
        for seq in population:
            if evaluations >= budget:
                break
            fit, covered = _fitness_ablation(seq, archive_branches, ruleset)
            scored.append((fit, seq, covered))
            archive_sequences.append(seq)
            evaluations += 1

        # (c) Selection: all candidates tie at fitness=0, pick randomly
        elites_idx = random.Random(rng.random()).choices(
            range(len(scored)), k=max(1, int(len(scored) * elite_ratio))
        )
        elites = [scored[i][1] for i in elites_idx]

        # (d) Mutate
        offspring = []
        while len(offspring) < pop_size and evaluations < budget:
            if len(elites) >= 2 and rng.random() < 0.3:
                parent_a = rng.choice(elites)
                parent_b = rng.choice(elites)
                child = _crossover(parent_a, parent_b, rng)
            else:
                parent = rng.choice(elites)
                child = _mutate(parent, rng, min_len, max_len)
            offspring.append(child)

        population = elites + offspring
        population = population[:pop_size]

    return archive_sequences
