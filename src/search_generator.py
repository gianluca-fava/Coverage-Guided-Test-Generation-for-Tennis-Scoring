"""
Search-based test generator — coverage-guided evolutionary algorithm.

Algorithm (vocabulary aligned with course material):
  1. Initialise a population of random candidate sequences.
  2. For each generation:
       a. Execute each candidate against the engine.
       b. Measure fitness: branch arcs covered by the candidate, plus a bonus
          for arcs that are new w.r.t. the running *archive*. The own-coverage
          term keeps a selection gradient even after the archive saturates.
       c. Identify the most promising candidates (elitism + tournament).
       d. Mutate promising candidates to produce offspring.
       e. Update archive with newly covered branches.
  3. Return all sequences in the final archive population.

Budget = total number of fitness evaluations (individual sequence executions).
"""

import random
from typing import Optional

from src.coverage_tool import measure_branch_coverage


# ---------------------------------------------------------------------------
# Mutation operators
# ---------------------------------------------------------------------------

def _mutate(seq: list, rng: random.Random, min_len: int = 4, max_len: int = 400) -> list:
    """Apply one or more mutation operators to *seq*."""
    seq = list(seq)  # copy

    op = rng.randint(0, 4)

    if op == 0:
        # Flip a random point winner
        if seq:
            idx = rng.randrange(len(seq))
            seq[idx] = "B" if seq[idx] == "A" else "A"

    elif op == 1:
        # Insert a random point at a random position
        if len(seq) < max_len:
            idx = rng.randint(0, len(seq))
            seq.insert(idx, rng.choice(["A", "B"]))

    elif op == 2:
        # Delete a random point
        if len(seq) > min_len:
            idx = rng.randrange(len(seq))
            seq.pop(idx)

    elif op == 3:
        # Extend with a short random suffix (only if there is room)
        room = max_len - len(seq)
        if room >= 1:
            extra = rng.randint(1, min(10, room))
            for _ in range(extra):
                seq.append(rng.choice(["A", "B"]))

    else:
        # Replace a random contiguous block
        if len(seq) >= 2:
            i = rng.randrange(len(seq) - 1)
            j = rng.randint(i + 1, min(i + 5, len(seq)))
            block = [rng.choice(["A", "B"]) for _ in range(j - i)]
            seq[i:j] = block

    # Clamp length
    seq = seq[:max_len]
    while len(seq) < min_len:
        seq.append(rng.choice(["A", "B"]))

    return seq


def _crossover(a: list, b: list, rng: random.Random) -> list:
    """Single-point crossover between two sequences."""
    if not a or not b:
        return list(a or b)
    cut_a = rng.randint(1, len(a))
    cut_b = rng.randint(0, len(b) - 1)
    return a[:cut_a] + b[cut_b:]


# ---------------------------------------------------------------------------
# Fitness function
# ---------------------------------------------------------------------------

def _fitness(seq: list, archive_branches: set, ruleset: str):
    """
    Fitness = (branch arcs covered by *seq*) + (arcs that are NEW w.r.t. the
    running *archive_branches*).

    The first term keeps a non-zero selection gradient even after the archive
    saturates — essential on a small SUT where branch coverage saturates within
    the first generation; the second term rewards sequences that reach arcs not
    yet seen. (A fitness based on novelty alone collapses to 0 for every
    candidate as soon as the archive fills, removing all selection pressure.)

    Returns (fitness, covered_set).
    """
    result = measure_branch_coverage([seq], ruleset)
    covered = set(map(tuple, result["covered_branches"]))
    novelty = len(covered - archive_branches)
    return len(covered) + novelty, covered


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate(
    ruleset: str,
    budget: int = 200,
    pop_size: int = 8,
    elite_ratio: float = 0.3,
    min_len: int = 4,
    max_len: int = 400,
    seed: Optional[int] = None,
    fitness_fn=None,
) -> list:
    """
    Search-based generator driven by branch coverage.

    Parameters
    ----------
    ruleset    : str  — one of "wimbledon", "usopen", "ausopen"
    budget     : int  — total fitness evaluations allowed
    pop_size   : int  — population size
    elite_ratio: float— fraction kept as elites each generation
    min_len    : int  — minimum sequence length
    max_len    : int  — maximum sequence length
    seed       : int | None
    fitness_fn : callable | None — fitness function (seq, archive, ruleset) ->
                 (score, covered_set). Defaults to the coverage-guided _fitness.
                 The ablation variant injects a constant-0 fitness here so that
                 it reuses THIS exact algorithm and differs ONLY in the fitness.

    Returns
    -------
    list[list[str]]  — all sequences accumulated in the archive
    """
    if fitness_fn is None:
        fitness_fn = _fitness
    rng = random.Random(seed)
    evaluations = 0

    # Archive: set of covered branch arcs (as tuples) + all sequences seen
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

    # Record the initial population in the returned archive of sequences.
    # IMPORTANT: do NOT pre-seed archive_branches with the whole population's
    # coverage here. Doing so makes the novelty term of _fitness zero from the
    # very first evaluation (the archive already contains everything the
    # population covers), which kills the selection gradient and degenerates the
    # search into the ablation/random walk. The covered-arc archive is filled
    # incrementally inside the generational loop instead.
    if population:
        archive_sequences.extend(population)

    # --- Generational loop ---
    while evaluations < budget:
        # --- (a) Execute & (b) Measure fitness for each candidate ---
        scored = []
        for seq in population:
            if evaluations >= budget:
                break
            fit, covered = fitness_fn(seq, archive_branches, ruleset)
            scored.append((fit, seq, covered))
            evaluations += 1

        # --- (c) Identify promising candidates (elites + random) ---
        scored.sort(key=lambda x: x[0], reverse=True)

        # Update archive with all newly covered branches
        for fit, seq, covered in scored:
            archive_branches |= covered
            archive_sequences.append(seq)

        # Keep elites
        n_elites = max(1, int(len(scored) * elite_ratio))
        elites = [seq for _, seq, _ in scored[:n_elites]]

        # --- (d) Mutate to produce offspring ---
        offspring = []
        while len(offspring) < pop_size and evaluations < budget:
            if len(elites) >= 2 and rng.random() < 0.3:
                # Crossover two elites
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
