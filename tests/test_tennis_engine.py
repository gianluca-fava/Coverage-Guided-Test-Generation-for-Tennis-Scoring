"""
Sanity-test suite for TennisMatch.

Role: correctness oracle — NOT a test generator.
Each test exercises a specific scoring rule and verifies
the expected outcome against the CONTRACT interface.
"""

import pytest
from src.tennis_engine import TennisMatch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def play_sequence(match, sequence):
    """Play every winner in *sequence* until the list is exhausted or match ends."""
    for winner in sequence:
        if match.is_over:
            break
        match.play_point(winner)


def make_score(points_a, points_b, games_a, games_b, sets_a, sets_b,
               in_tiebreak=False, is_over=False, winner=None):
    """Build a score dict matching the CONTRACT schema."""
    return {
        "points":      {"A": points_a, "B": points_b},
        "games":       {"A": games_a,  "B": games_b},
        "sets":        {"A": sets_a,   "B": sets_b},
        "in_tiebreak": in_tiebreak,
        "is_over":     is_over,
        "winner":      winner,
    }


# ---------------------------------------------------------------------------
# 1. Game scoring fundamentals
# ---------------------------------------------------------------------------

class TestGameScoring:

    def test_initial_score(self):
        m = TennisMatch("usopen")
        s = m.score()
        assert s["points"] == {"A": "0", "B": "0"}
        assert s["games"]  == {"A": 0, "B": 0}
        assert s["sets"]   == {"A": 0, "B": 0}
        assert s["in_tiebreak"] is False
        assert s["is_over"] is False
        assert s["winner"] is None

    def test_game_won_at_love(self):
        """A wins a game without B scoring (4 points in a row)."""
        m = TennisMatch("usopen")
        for _ in range(4):
            m.play_point("A")
        s = m.score()
        assert s["games"]["A"] == 1
        assert s["games"]["B"] == 0
        assert s["points"] == {"A": "0", "B": "0"}  # reset after game

    def test_game_point_sequence(self):
        """Verify 0→15→30→40 labels."""
        m = TennisMatch("usopen")
        expected = [
            ("0", "0"),
            ("15", "0"),
            ("30", "0"),
            ("40", "0"),
        ]
        for i, (ea, eb) in enumerate(expected):
            assert m.score()["points"] == {"A": ea, "B": eb}
            if i < 3:
                m.play_point("A")

    def test_deuce_simple(self):
        """Reach deuce (40-40), then A wins advantage then game."""
        m = TennisMatch("usopen")
        # 3 points each → deuce
        for _ in range(3):
            m.play_point("A")
            m.play_point("B")
        assert m.score()["points"] == {"A": "40", "B": "40"}

        m.play_point("A")  # A advantage
        assert m.score()["points"] == {"A": "Ad", "B": "40"}

        m.play_point("B")  # back to deuce
        assert m.score()["points"] == {"A": "40", "B": "40"}

        m.play_point("A")  # A advantage again
        m.play_point("A")  # A wins game
        assert m.score()["games"]["A"] == 1
        assert m.score()["points"] == {"A": "0", "B": "0"}

    def test_deuce_multiple_swings(self):
        """Deuce oscillates several times before B wins."""
        m = TennisMatch("usopen")
        for _ in range(3):
            m.play_point("A")
            m.play_point("B")
        # 5 deuce/advantage cycles
        for _ in range(5):
            m.play_point("A")   # A Ad
            m.play_point("B")   # deuce
        m.play_point("B")       # B Ad
        m.play_point("B")       # B wins
        assert m.score()["games"]["B"] == 1
        assert m.score()["games"]["A"] == 0

    def test_invalid_winner_raises(self):
        m = TennisMatch("usopen")
        with pytest.raises(ValueError):
            m.play_point("C")

    def test_play_after_match_over_raises(self):
        m = TennisMatch("usopen")
        # Force a quick match over with the minimum sequence
        # Win 2 sets 6-0 each (A wins every game, every point)
        for _ in range(2):          # 2 sets
            for _ in range(6):      # 6 games
                for _ in range(4):  # 4 points
                    m.play_point("A")
        assert m.is_over
        with pytest.raises(RuntimeError):
            m.play_point("A")


# ---------------------------------------------------------------------------
# 2. Set scoring
# ---------------------------------------------------------------------------

class TestSetScoring:

    def _win_game(self, match, player):
        """Win one game quickly (4 points)."""
        for _ in range(4):
            if not match.is_over:
                match.play_point(player)

    def test_set_6_4(self):
        """A wins set 6-4."""
        m = TennisMatch("usopen")
        for _ in range(4):
            self._win_game(m, "A")
        for _ in range(4):
            self._win_game(m, "B")
        for _ in range(2):
            self._win_game(m, "A")
        s = m.score()
        assert s["sets"]["A"] == 1
        assert s["sets"]["B"] == 0
        assert s["games"] == {"A": 0, "B": 0}  # reset for new set

    def test_set_7_5(self):
        """B wins set 7-5."""
        m = TennisMatch("usopen")
        for _ in range(5):
            self._win_game(m, "B")
        for _ in range(5):
            self._win_game(m, "A")
        # 5-5; B wins 2 more → 5-7
        for _ in range(2):
            self._win_game(m, "B")
        s = m.score()
        assert s["sets"]["B"] == 1
        assert s["sets"]["A"] == 0

    def test_set_tiebreak_reached(self):
        """At 6-6 in the same set a tie-break starts."""
        m = TennisMatch("usopen")
        # Alternate game wins to reach 6-6 within the first set
        for _ in range(6):
            self._win_game(m, "A")
            self._win_game(m, "B")
        assert m.score()["in_tiebreak"] is True

    def test_set_tiebreak_7_standard(self):
        """Standard tie-break: first to 7 wins."""
        m = TennisMatch("usopen")
        for _ in range(6):
            self._win_game(m, "A")
        for _ in range(6):
            self._win_game(m, "B")
        # Tie-break: A wins 7-0
        for _ in range(7):
            m.play_point("A")
        s = m.score()
        assert s["in_tiebreak"] is False
        assert s["sets"]["A"] == 1

    def test_set_tiebreak_requires_2_margin(self):
        """Tie-break at 6-6 each requires 2-point margin."""
        m = TennisMatch("usopen")
        for _ in range(6):
            self._win_game(m, "A")
            self._win_game(m, "B")
        # Score to 6-6 in tie-break
        for _ in range(6):
            m.play_point("A")
            m.play_point("B")
        assert m.score()["in_tiebreak"] is True
        assert m.score()["points"] == {"A": "6", "B": "6"}
        # A gets to 7-6 — not enough
        m.play_point("A")
        assert m.score()["in_tiebreak"] is True
        # A wins 8-6
        m.play_point("A")
        assert m.score()["in_tiebreak"] is False
        assert m.score()["sets"]["A"] == 1


# ---------------------------------------------------------------------------
# 3. Full-match and ruleset differences
# ---------------------------------------------------------------------------

class TestFullMatch:

    def _win_set_6_0(self, match, player):
        for _ in range(6):
            for _ in range(4):
                if not match.is_over:
                    match.play_point(player)

    def test_match_won_best_of_3(self):
        """A wins 2-0 in sets → match over."""
        m = TennisMatch("usopen")
        self._win_set_6_0(m, "A")
        self._win_set_6_0(m, "A")
        assert m.is_over
        assert m.winner == "A"
        assert m.score()["sets"] == {"A": 2, "B": 0}

    def test_match_three_sets(self):
        """B comes back from 0-1 to win 1-2."""
        m = TennisMatch("usopen")
        self._win_set_6_0(m, "A")
        self._win_set_6_0(m, "B")
        self._win_set_6_0(m, "B")
        assert m.is_over
        assert m.winner == "B"
        assert m.score()["sets"] == {"A": 1, "B": 2}


class TestDecisiveSetRulesets:

    def _win_game(self, match, player):
        for _ in range(4):
            if not match.is_over:
                match.play_point(player)

    def _reach_decisive_set_tiebreak(self, ruleset):
        """Drive match to 1-1 in sets, then 6-6 in games of the decisive set."""
        m = TennisMatch(ruleset)
        # Set 1: A wins 6-0
        for _ in range(6):
            self._win_game(m, "A")
        # Set 2: B wins 6-0
        for _ in range(6):
            self._win_game(m, "B")
        # Set 3: alternate game wins to reach 6-6, then tiebreak starts
        for _ in range(6):
            self._win_game(m, "A")
            self._win_game(m, "B")
        assert m.score()["in_tiebreak"] is True
        return m

    def test_usopen_decisive_tiebreak_to_7(self):
        """US Open: decisive tie-break is standard (7 pts)."""
        m = self._reach_decisive_set_tiebreak("usopen")
        for _ in range(7):
            m.play_point("A")
        assert m.is_over
        assert m.winner == "A"

    def test_wimbledon_decisive_tiebreak_to_10(self):
        """Wimbledon: decisive tie-break to 10 points."""
        m = self._reach_decisive_set_tiebreak("wimbledon")
        # 7 points not enough for Wimbledon tie-break
        for _ in range(7):
            m.play_point("A")
        assert not m.is_over
        # Reach 10
        for _ in range(3):
            m.play_point("A")
        assert m.is_over
        assert m.winner == "A"

    def test_ausopen_decisive_tiebreak_to_10(self):
        """Australian Open: decisive super tie-break to 10 points."""
        m = self._reach_decisive_set_tiebreak("ausopen")
        for _ in range(7):
            m.play_point("A")
        assert not m.is_over
        for _ in range(3):
            m.play_point("A")
        assert m.is_over
        assert m.winner == "A"

    def test_wimbledon_decisive_tiebreak_needs_2_margin(self):
        """Wimbledon decisive tie-break: 9-9 then A wins 11-9."""
        m = self._reach_decisive_set_tiebreak("wimbledon")
        for _ in range(9):
            m.play_point("A")
            m.play_point("B")
        assert not m.is_over
        m.play_point("A")   # 10-9 — not enough
        assert not m.is_over
        m.play_point("A")   # 11-9 — A wins
        assert m.is_over
        assert m.winner == "A"

    def test_ausopen_decisive_tiebreak_needs_2_margin(self):
        """Australian Open super tie-break: 9-9 then B wins 10-11... wait, B needs 11-9."""
        m = self._reach_decisive_set_tiebreak("ausopen")
        for _ in range(9):
            m.play_point("A")
            m.play_point("B")
        assert not m.is_over
        m.play_point("B")   # 9-10 — not enough
        assert not m.is_over
        m.play_point("B")   # 9-11 — B wins
        assert m.is_over
        assert m.winner == "B"

    def test_invalid_ruleset_raises(self):
        with pytest.raises(ValueError):
            TennisMatch("rollandgarros")


# ---------------------------------------------------------------------------
# 4. Score dict structure (contract compliance)
# ---------------------------------------------------------------------------

class TestScoreContract:

    def test_score_keys(self):
        m = TennisMatch("usopen")
        s = m.score()
        assert set(s.keys()) == {"points", "games", "sets", "in_tiebreak", "is_over", "winner"}

    def test_score_points_keys(self):
        m = TennisMatch("usopen")
        p = m.score()["points"]
        assert set(p.keys()) == {"A", "B"}

    def test_score_games_keys(self):
        m = TennisMatch("usopen")
        g = m.score()["games"]
        assert set(g.keys()) == {"A", "B"}

    def test_score_sets_keys(self):
        m = TennisMatch("usopen")
        s = m.score()["sets"]
        assert set(s.keys()) == {"A", "B"}
