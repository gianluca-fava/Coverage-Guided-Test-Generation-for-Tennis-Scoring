# Internal Interface Contract

## SUT — `src/tennis_engine.py`

- Exposes `TennisMatch(ruleset: str)`, where `ruleset` is one of `{"wimbledon", "usopen", "ausopen"}`.
- A test is a sequence of point winners: a list of `"A"` / `"B"` strings.
- `match.play_point(winner: str)` drives the engine.
  - Raises `ValueError` if `winner` is not `"A"` or `"B"`.
  - Raises `RuntimeError` if called after `match.is_over` is `True`.
- `match.is_over` (`bool`) — `True` when the match has ended.
- `match.winner` (`str | None`) — `"A"`, `"B"`, or `None` if the match is still in progress.
- `match.score()` returns a dict with **exactly** these keys:

```python
{
  "points":      {"A": <str>, "B": <str>},   # current game: "0","15","30","40","Ad"; tie-break: "0","1",...
  "games":       {"A": <int>, "B": <int>},   # games in the current set
  "sets":        {"A": <int>, "B": <int>},   # sets won
  "in_tiebreak": <bool>,
  "is_over":     <bool>,
  "winner":      <"A" | "B" | None>
}
```

### Ruleset differences (decisive set)

| Ruleset   | Decisive-set tie-break       |
|-----------|------------------------------|
| wimbledon | Tie-break to 10 pts (2-pt margin) at 6-6 |
| usopen    | Standard tie-break to 7 pts at 6-6        |
| ausopen   | Super tie-break to 10 pts (2-pt margin) at 6-6 |

---

## Coverage tool — `src/coverage_tool.py`

- Exposes `measure_branch_coverage(sequences: list[list[str]], ruleset: str) -> dict`
- Uses `coverage.py` in **branch mode**, targeting **only** `src/tennis_engine.py`.
- Returns:
```python
{
  "branch_coverage":  <float in [0, 1]>,
  "covered_branches": <list>,
  "total_branches":   <int>
}
```

---

## Results format — `results/results.csv`

Header: `generator,ruleset,seed,budget,branch_coverage,mutation_score,time_sec`

| Field | Values |
|-------|--------|
| `generator` | `"random"` \| `"search"` \| `"ablation"` |
| `ruleset`   | `"wimbledon"` \| `"usopen"` \| `"ausopen"` |
| `seed`      | integer |
| `budget`    | integer (fitness-evaluation budget per run; two-regime design, e.g. `30` and `200`) |
| `branch_coverage` | float [0, 1] |
| `mutation_score`  | float [0, 1] |
| `time_sec`  | float |

> Historical rows produced before the two-regime design used the old 6-column
> schema (without `budget`). Run `python -m experiments.migrate_csv` once to
> upgrade an old `results.csv` to this format (it back-fills `budget=200`).
