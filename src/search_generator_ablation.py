"""
Ablation variant of the search-based generator.

This variant runs the *exact same* evolutionary algorithm as
``search_generator.generate`` — same population, same selection, same mutation
and crossover operators, same RNG usage, same number of generations — and
differs in **one and only one** thing: the fitness function is a constant 0,
so there is no coverage guidance and the selection has no signal to act on.

Implementing the ablation by delegating to ``search_generator.generate`` (with
an injected constant fitness) is deliberate: it guarantees that the ONLY
difference between the full search and the ablation is the fitness function.
Any other implementation difference would be a confounding factor and would
invalidate the ablation study.
"""

from typing import Optional

from src import search_generator


# ---------------------------------------------------------------------------
# Degraded fitness — constant zero, ignores coverage completely
# ---------------------------------------------------------------------------

def _fitness_ablation(seq: list, archive_branches: set, ruleset: str):
    """Fitness is always 0 — removes all coverage guidance / selection signal."""
    return 0, set()


# ---------------------------------------------------------------------------
# Main generator (ablation) — same algorithm, constant fitness
# ---------------------------------------------------------------------------

def generate(
    ruleset: str,
    budget: int = 200,
    pop_size: int = 8,
    elite_ratio: float = 0.3,
    min_len: int = 4,
    max_len: int = 400,
    seed: Optional[int] = None,
) -> list:
    """
    Ablation generator: identical to ``search_generator.generate`` but with a
    constant (zero) fitness, so it isolates exactly the contribution of the
    coverage-guided fitness function.

    Parameters are the same as ``search_generator.generate``.
    """
    return search_generator.generate(
        ruleset=ruleset,
        budget=budget,
        pop_size=pop_size,
        elite_ratio=elite_ratio,
        min_len=min_len,
        max_len=max_len,
        seed=seed,
        fitness_fn=_fitness_ablation,
    )
