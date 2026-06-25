"""
Tennis scoring engine.

Supported rulesets: 'wimbledon', 'usopen', 'ausopen'.

Decisive-set tie-break rules:
  - wimbledon: tie-break to 10 points (2-point margin) at 6-6
  - usopen:    standard tie-break to 7 points (2-point margin) at 6-6
  - ausopen:   super tie-break to 10 points (2-point margin) at 6-6

API:
    match = TennisMatch(ruleset)
    match.play_point("A" | "B")   # raises ValueError / RuntimeError on bad input
    match.is_over                 # bool
    match.winner                  # "A" | "B" | None
    match.score()                 # dict — see CONTRACT.md for exact keys
"""

VALID_RULESETS = {"wimbledon", "usopen", "ausopen"}


class TennisMatch:
    def __init__(self, ruleset: str):
        if ruleset not in VALID_RULESETS:
            raise ValueError(f"Unknown ruleset '{ruleset}'. Choose from {VALID_RULESETS}.")

        self.ruleset = ruleset

        # Sets won
        self._sets_A = 0
        self._sets_B = 0

        # Games in the current set
        self._games_A = 0
        self._games_B = 0

        # Points in the current game (raw integers)
        self._points_A = 0
        self._points_B = 0

        # State flags
        self._in_tiebreak = False
        self._is_over = False
        self._winner = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_over(self) -> bool:
        return self._is_over

    @property
    def winner(self):
        return self._winner

    def score(self) -> dict:
        return {
            "points":      self._points_display(),
            "games":       {"A": self._games_A, "B": self._games_B},
            "sets":        {"A": self._sets_A,  "B": self._sets_B},
            "in_tiebreak": self._in_tiebreak,
            "is_over":     self._is_over,
            "winner":      self._winner,
        }

    def play_point(self, winner: str) -> None:
        if winner not in ("A", "B"):
            raise ValueError(f"winner must be 'A' or 'B', got {winner!r}.")
        if self._is_over:
            raise RuntimeError("Match is already over; cannot play further points.")

        if self._in_tiebreak:
            self._play_tiebreak_point(winner)
        else:
            self._play_game_point(winner)

    # ------------------------------------------------------------------
    # Internal — display helpers
    # ------------------------------------------------------------------

    _POINT_NAMES = {0: "0", 1: "15", 2: "30", 3: "40"}

    def _points_display(self) -> dict:
        if self._in_tiebreak:
            return {"A": str(self._points_A), "B": str(self._points_B)}

        pa = self._points_A
        pb = self._points_B

        # Deuce / advantage phase: both reached 3 (40)
        if pa >= 3 and pb >= 3:
            if pa == pb:
                return {"A": "40", "B": "40"}  # deuce
            elif pa > pb:
                return {"A": "Ad", "B": "40"}
            else:
                return {"A": "40", "B": "Ad"}

        return {"A": self._POINT_NAMES[pa], "B": self._POINT_NAMES[pb]}

    # ------------------------------------------------------------------
    # Internal — regular game
    # ------------------------------------------------------------------

    def _play_game_point(self, winner: str) -> None:
        if winner == "A":
            self._points_A += 1
        else:
            self._points_B += 1

        pa = self._points_A
        pb = self._points_B

        # Check whether the game is won
        if pa >= 4 and pb < 3:
            # A wins game outright (no deuce possible if B never reached 3)
            self._game_won("A")
        elif pb >= 4 and pa < 3:
            # B wins game outright
            self._game_won("B")
        elif pa >= 3 and pb >= 3:
            # Deuce/advantage territory
            if pa >= 4 and pa - pb >= 2:
                self._game_won("A")
            elif pb >= 4 and pb - pa >= 2:
                self._game_won("B")
            # else: still in deuce/advantage — continue

    # ------------------------------------------------------------------
    # Internal — tie-break
    # ------------------------------------------------------------------

    def _play_tiebreak_point(self, winner: str) -> None:
        if winner == "A":
            self._points_A += 1
        else:
            self._points_B += 1

        pa = self._points_A
        pb = self._points_B

        target = self._tiebreak_target()

        if pa >= target and pa - pb >= 2:
            self._tiebreak_won("A")
        elif pb >= target and pb - pa >= 2:
            self._tiebreak_won("B")

    def _tiebreak_target(self) -> int:
        """Return the minimum points to win the current tie-break."""
        is_decisive = self._sets_A + self._sets_B == 2  # third set

        if not is_decisive:
            # Non-decisive sets: standard tie-break to 7
            return 7

        # Decisive set
        if self.ruleset == "usopen":
            return 7
        elif self.ruleset == "wimbledon":
            return 10
        else:
            # ausopen
            return 10

    # ------------------------------------------------------------------
    # Internal — game / set / match accounting
    # ------------------------------------------------------------------

    def _game_won(self, player: str) -> None:
        self._points_A = 0
        self._points_B = 0

        if player == "A":
            self._games_A += 1
        else:
            self._games_B += 1

        self._check_set_over()

    def _tiebreak_won(self, player: str) -> None:
        self._in_tiebreak = False
        self._points_A = 0
        self._points_B = 0

        if player == "A":
            self._games_A += 1
        else:
            self._games_B += 1

        self._check_set_over()

    def _check_set_over(self) -> None:
        ga = self._games_A
        gb = self._games_B

        set_winner = None

        # --- Win by reaching 6 with a 2-game lead ---
        if ga >= 6 and ga - gb >= 2:
            set_winner = "A"
        elif gb >= 6 and gb - ga >= 2:
            set_winner = "B"

        # --- Win at 7-5 ---
        elif ga == 7 and gb == 5:
            set_winner = "A"
        elif gb == 7 and ga == 5:
            set_winner = "B"

        # --- Tie-break at 6-6 ---
        elif ga == 6 and gb == 6:
            self._in_tiebreak = True
            return  # no set won yet

        # --- Tie-break just finished: 7-6 ---
        elif ga == 7 and gb == 6:
            set_winner = "A"
        elif gb == 7 and ga == 6:
            set_winner = "B"

        if set_winner is not None:
            self._set_won(set_winner)

    def _set_won(self, player: str) -> None:
        if player == "A":
            self._sets_A += 1
        else:
            self._sets_B += 1

        # Check match over (best of 3)
        if self._sets_A == 2:
            self._match_over("A")
        elif self._sets_B == 2:
            self._match_over("B")
        else:
            # Start new set
            self._games_A = 0
            self._games_B = 0
            self._points_A = 0
            self._points_B = 0
            self._in_tiebreak = False

    def _match_over(self, player: str) -> None:
        self._is_over = True
        self._winner = player
