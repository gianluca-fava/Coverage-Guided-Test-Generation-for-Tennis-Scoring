"""
Random test generator — baseline.

Generates *budget* sequences of random length in [min_len, max_len],
each point winner drawn uniformly from {"A", "B"}.
"""

import random
from typing import Optional


def generate(
    ruleset: str,
    budget: int = 200,
    min_len: int = 4,
    max_len: int = 400,
    seed: Optional[int] = None,
) -> list:
    """
    Generate *budget* random point sequences.

    Parameters
    ----------
    ruleset : str   — passed through but not used by the random generator
    budget  : int   — number of sequences to produce
    min_len : int   — minimum sequence length
    max_len : int   — maximum sequence length
    seed    : int | None — random seed for reproducibility

    Returns
    -------
    list[list[str]]  — each inner list is a sequence of "A"/"B" strings
    """
    rng = random.Random(seed)
    sequences = []
    for _ in range(budget):
        length = rng.randint(min_len, max_len)
        seq = [rng.choice(["A", "B"]) for _ in range(length)]
        sequences.append(seq)
    return sequences
