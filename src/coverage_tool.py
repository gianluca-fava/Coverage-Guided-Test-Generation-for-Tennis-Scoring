"""
Branch coverage measurement for src/tennis_engine.py.

Uses coverage.py in branch mode with the JSON report API,
targeting only the engine module.
"""

import json
import os
import sys
import tempfile
import importlib

import coverage

# Absolute path to the engine module file
_ENGINE_PATH = os.path.join(os.path.dirname(__file__), "tennis_engine.py")
# Relative path used as key in coverage JSON output
_ENGINE_REL = os.path.join("src", "tennis_engine.py")


def measure_branch_coverage(sequences: list, ruleset: str) -> dict:
    """
    Run *sequences* against TennisMatch(ruleset) and measure branch coverage
    on src/tennis_engine.py only.

    Parameters
    ----------
    sequences : list[list[str]]
        Each element is a list of "A"/"B" point winners.
    ruleset : str
        One of "wimbledon", "usopen", "ausopen".

    Returns
    -------
    dict with keys:
        "branch_coverage"  : float in [0, 1]
        "covered_branches" : list  (executed branch arc pairs)
        "total_branches"   : int
    """
    # Fresh coverage instance each call
    cov = coverage.Coverage(
        branch=True,
        include=[_ENGINE_PATH],
        omit=None,
        config_file=False,
    )
    cov.start()

    try:
        # Ensure the module is importable; re-use cached version
        if "src.tennis_engine" in sys.modules:
            engine_mod = sys.modules["src.tennis_engine"]
        else:
            engine_mod = importlib.import_module("src.tennis_engine")

        TennisMatch = engine_mod.TennisMatch

        for seq in sequences:
            try:
                match = TennisMatch(ruleset)
                for winner in seq:
                    if match.is_over:
                        break
                    if winner in ("A", "B"):
                        match.play_point(winner)
            except Exception:
                # Invalid sequences are tolerated; coverage still collected
                pass
    finally:
        cov.stop()
        # NOTE: deliberately do NOT call cov.save(). The JSON report below is
        # produced from the data this fresh Coverage instance holds in memory;
        # save() would only persist a shared .coverage file on disk, which is an
        # unnecessary artifact and a cross-run/cross-process leakage hazard.

    # --- Produce JSON report and parse it ---
    tmp_path = tempfile.mktemp(suffix=".json")
    try:
        cov.json_report(outfile=tmp_path, pretty_print=False)
        with open(tmp_path) as f:
            data = json.load(f)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # The JSON key is always a path relative to the project root
    file_data = None
    for key, val in data.get("files", {}).items():
        if key.endswith(os.path.join("src", "tennis_engine.py")):
            file_data = val
            break

    if file_data is None:
        return {"branch_coverage": 0.0, "covered_branches": [], "total_branches": 0}

    summary = file_data.get("summary", {})
    covered   = summary.get("covered_branches", 0)
    total     = summary.get("num_branches", 0)
    ratio     = summary.get("percent_branches_covered", 0.0) / 100.0

    # executed_branches from JSON: list of [from_line, to_line] pairs
    executed_arcs = file_data.get("executed_branches", [])

    return {
        "branch_coverage":  ratio,
        "covered_branches": executed_arcs,
        "total_branches":   total,
    }
