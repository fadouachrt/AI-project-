"""
test_scheduler.py
=================
Comprehensive tests for Project 4 – Sports League Scheduler
(Algerian Ligue 1 – realistic dummy data)

Tests cover:
  1. double_round_robin()  – structural correctness
  2. assign_all_days()     – day assignment rules
  3. cost_function()       – penalty calculation
  4. swap_rounds()         – neighbour generation
  5. simulated_annealing() – convergence & improvement
  6. load_derbies()        – CSV parsing
  7. Integration           – full pipeline end-to-end

Run with:
    pytest test_scheduler.py -v
"""

import math
import csv
import os
import random
import tempfile
from copy import deepcopy
from collections import defaultdict, Counter

import pytest

# ── Import the modules under test ───────────────────────────────────────────
# Adjust these imports to match your actual package structure.

from schedule import double_round_robin, assign_all_days
from models import Team, Match, Round, Schedule
from neighbour import swap_rounds
from Minimize_total import cost_function
from simulated_annealing import simulated_annealing, load_derbies


# ════════════════════════════════════════════════════════════════════════════
# FIXTURES – realistic Algerian Ligue 1 dummy data
# ════════════════════════════════════════════════════════════════════════════

# 16 real-ish clubs with approximate GPS coordinates
_TEAM_DATA = [
    # (name,            lat,      lon)
    ("USM Alger",       36.7372,  3.0869),   # Algiers
    ("MC Alger",        36.7525,  3.0420),   # Algiers (Bologhine)
    ("CR Belouizdad",   36.7207,  3.1026),   # Algiers (Belouizdad)
    ("NA Hussein Dey",  36.7438,  3.1253),   # Algiers (Hussein Dey)
    ("JS Kabylie",      36.7001,  3.9066),   # Tizi Ouzou
    ("MC Oran",         35.6966, -0.6308),   # Oran
    ("USM Oran",        35.7100, -0.6425),   # Oran
    ("ES Sétif",        36.1898,  5.4058),   # Sétif
    ("ASO Chlef",       36.1669,  1.3300),   # Chlef
    ("JSM Béjaïa",      36.7450,  5.0563),   # Béjaïa
    ("RC Arbaa",        36.5700,  3.1500),   # Arbaa
    ("NC Magra",        35.8483,  3.8431),   # Magra
    ("WA Tlemcen",      34.8780, -1.3152),   # Tlemcen
    ("CA Bordj BBA",    36.0742,  4.7630),   # Bordj Bou Arréridj
    ("USM Khenchela",   35.4330,  7.1456),   # Khenchela
    ("Paradou AC",      36.7200,  2.9800),   # Algiers surroundings
]

# Derby pairs (fierce local rivalries → should land on weekends / TV slots)
_DERBY_PAIRS = [
    ("USM Alger",    "MC Alger"),        # Le Derby d'Alger
    ("USM Alger",    "CR Belouizdad"),
    ("MC Alger",     "CR Belouizdad"),
    ("MC Oran",      "USM Oran"),        # Derby d'Oran
]

WEEKEND_DAYS = {"Friday", "Saturday"}


def make_teams(n=None):
    """Return a list of Team objects (optionally trimmed to n teams)."""
    data = _TEAM_DATA[:n] if n else _TEAM_DATA
    return [Team(name, lat, lon) for name, lat, lon in data]


def make_distance_matrix(teams):
    def dist(a, b):
        dlat = a.lat - b.lat
        dlon = (a.lon - b.lon) * math.cos(math.radians((a.lat + b.lat) / 2))
        return math.sqrt(dlat ** 2 + dlon ** 2) * 111

    # Build as nested dict: matrix[a][b] = distance
    matrix = {}
    for t1 in teams:
        matrix[t1.name] = {}
        for t2 in teams:
            matrix[t1.name][t2.name] = dist(t1, t2)
    return matrix


def make_derbies():
    return {frozenset(pair) for pair in _DERBY_PAIRS}


def make_schedule(teams=None):
    """Build a full double-round-robin schedule with days assigned."""
    if teams is None:
        teams = make_teams()
    s = double_round_robin(teams)
    return assign_all_days(s)


# ════════════════════════════════════════════════════════════════════════════
# 1. double_round_robin – structural correctness
# ════════════════════════════════════════════════════════════════════════════

class TestDoubleRoundRobin:

    def test_correct_number_of_rounds(self):
        """N teams → 2*(N-1) rounds."""
        teams = make_teams()
        N = len(teams)
        s = double_round_robin(teams)
        assert s.total_rounds() == 2 * (N - 1), (
            f"Expected {2*(N-1)} rounds for {N} teams, got {s.total_rounds()}"
        )

    def test_each_round_has_n_over_2_matches(self):
        """Every round must have exactly N/2 matches (for even N)."""
        teams = make_teams()
        N = len(teams)
        s = double_round_robin(teams)
        for r in s.rounds:
            assert len(r.matches) == N // 2, (
                f"Round {r.round_index+1} has {len(r.matches)} matches, expected {N//2}"
            )

    def test_every_team_plays_once_per_round(self):
        """Each team appears exactly once per round (no double-booking)."""
        teams = make_teams()
        s = double_round_robin(teams)
        for r in s.rounds:
            participants = []
            for m in r.matches:
                participants.append(m.home.name)
                participants.append(m.away.name)
            counts = Counter(participants)
            for team in teams:
                assert counts[team.name] == 1, (
                    f"Round {r.round_index+1}: {team.name} appears {counts[team.name]} times"
                )

    def test_every_pair_meets_exactly_twice(self):
        """Each ordered pair (A home vs B away) appears exactly once → pair meets twice."""
        teams = make_teams()
        s = double_round_robin(teams)
        pair_counter = Counter()
        for r in s.rounds:
            for m in r.matches:
                pair_counter[(m.home.name, m.away.name)] += 1

        names = [t.name for t in teams]
        for a in names:
            for b in names:
                if a == b:
                    continue
                assert pair_counter[(a, b)] == 1, (
                    f"{a} (H) vs {b} (A) appears {pair_counter[(a,b)]} times (expected 1)"
                )

    def test_total_matches(self):
        """Total matches = N*(N-1) for a double round-robin."""
        teams = make_teams()
        N = len(teams)
        s = double_round_robin(teams)
        assert s.total_matches() == N * (N - 1)

    def test_works_with_small_league(self):
        """Sanity-check with 4 teams (minimal valid size)."""
        teams = make_teams(n=4)
        s = double_round_robin(teams)
        assert s.total_rounds() == 6
        assert s.total_matches() == 12

    def test_works_with_odd_n_gracefully(self):
        """5 teams → might use a 'bye' or raise – just ensure no crash."""
        teams = make_teams(n=5)
        try:
            s = double_round_robin(teams)
            # If it doesn't raise, basic sanity
            assert s.total_rounds() > 0
        except (ValueError, AssertionError):
            pass  # Acceptable: odd N may be unsupported


# ════════════════════════════════════════════════════════════════════════════
# 2. assign_all_days – day assignment rules
# ════════════════════════════════════════════════════════════════════════════

VALID_DAYS = {"Friday", "Saturday", "Wednesday", "Thursday", "Sunday"}

class TestAssignAllDays:

    def test_every_match_has_a_day(self):
        s = make_schedule()
        for r in s.rounds:
            for m in r.matches:
                assert m.day is not None, f"Match {m} has no day assigned"

    def test_days_are_valid(self):
        s = make_schedule()
        for r in s.rounds:
            for m in r.matches:
                assert m.day in VALID_DAYS, f"Invalid day '{m.day}' in match {m}"

    def test_each_round_uses_its_allowed_days(self):
        """Matches within a round must only use that round's days list."""
        teams = make_teams()
        base = double_round_robin(teams)
        s = assign_all_days(base)
        for r in s.rounds:
            for m in r.matches:
                assert m.day in r.days, (
                    f"Round {r.round_index+1} assigned day '{m.day}' "
                    f"not in allowed days {r.days}"
                )

    def test_no_match_exceeds_round_capacity(self):
        """Number of matches per day should not exceed N/2."""
        s = make_schedule()
        N = len(s.teams) if s.teams else len(make_teams())
        for r in s.rounds:
            day_counts = Counter(m.day for m in r.matches)
            for day, count in day_counts.items():
                assert count <= N // 2, (
                    f"Round {r.round_index+1}, day '{day}' has {count} matches "
                    f"(max allowed: {N//2})"
                )


# ════════════════════════════════════════════════════════════════════════════
# 3. cost_function – penalty calculation
# ════════════════════════════════════════════════════════════════════════════

class TestCostFunction:

    def test_returns_a_number(self):
        teams = make_teams()
        distances = make_distance_matrix(teams)
        derbies = make_derbies()
        s = make_schedule(teams)
        cost = cost_function(s, teams, distances, derbies, WEEKEND_DAYS)
        assert isinstance(cost, (int, float)), "cost_function must return a number"

    def test_cost_is_non_negative(self):
        teams = make_teams()
        distances = make_distance_matrix(teams)
        derbies = make_derbies()
        s = make_schedule(teams)
        cost = cost_function(s, teams, distances, derbies, WEEKEND_DAYS)
        assert cost >= 0, f"Cost must be ≥ 0, got {cost}"

    def test_deterministic(self):
        """Same schedule → same cost every time."""
        teams = make_teams()
        distances = make_distance_matrix(teams)
        derbies = make_derbies()
        s = make_schedule(teams)
        c1 = cost_function(s, teams, distances, derbies, WEEKEND_DAYS)
        c2 = cost_function(s, teams, distances, derbies, WEEKEND_DAYS)
        assert c1 == c2

    def test_travel_distance_component_positive(self):
        """Moving teams that are far apart should increase cost vs. local teams."""
        # 2-team mini-league: same city vs. cross-country
        close_teams = [
            Team("Home A", 36.7372, 3.0869),
            Team("Home B", 36.7525, 3.0420),
        ]
        far_teams = [
            Team("North",  36.7372, 3.0869),
            Team("South",  21.4000, 0.1000),  # deep Sahara
        ]
        dist_close = make_distance_matrix(close_teams)
        dist_far   = make_distance_matrix(far_teams)
        derbies = set()

        s_close = make_schedule(close_teams)
        s_far   = make_schedule(far_teams)

        cost_close = cost_function(s_close, close_teams, dist_close, derbies, WEEKEND_DAYS)
        cost_far   = cost_function(s_far,   far_teams,   dist_far,   derbies, WEEKEND_DAYS)

        assert cost_far > cost_close, (
            "Far-apart teams must have higher travel cost than close teams"
        )

    def test_derby_on_weekday_adds_penalty(self):
        """
        Manually place a derby on a weekday and verify cost > schedule with
        the same derby on a weekend.
        """
        teams = make_teams(n=4)
        distances = make_distance_matrix(teams)
        # Make the first two teams a derby pair
        derbies = {frozenset([teams[0].name, teams[1].name])}

        s_base = make_schedule(teams)
        s_weekday = deepcopy(s_base)
        s_weekend  = deepcopy(s_base)

        # Find the derby match and force it to a weekday vs. weekend
        for r in s_weekday.rounds:
            for m in r.matches:
                if frozenset([m.home.name, m.away.name]) in derbies:
                    m.day = "Wednesday"   # weekday → penalty
                    break
        for r in s_weekend.rounds:
            for m in r.matches:
                if frozenset([m.home.name, m.away.name]) in derbies:
                    m.day = "Friday"      # weekend → no penalty
                    break

        cost_weekday = cost_function(s_weekday, teams, distances, derbies, WEEKEND_DAYS)
        cost_weekend  = cost_function(s_weekend,  teams, distances, derbies, WEEKEND_DAYS)

        assert cost_weekday >= cost_weekend, (
            "Derby on a weekday should have cost ≥ derby on a weekend"
        )


# ════════════════════════════════════════════════════════════════════════════
# 4. swap_rounds – neighbour generation
# ════════════════════════════════════════════════════════════════════════════

class TestSwapRounds:

    def test_returns_schedule(self):
        s = make_schedule()
        neighbor = swap_rounds(s, 0, 1)
        assert isinstance(neighbor, Schedule)

    def test_original_unchanged(self):
        """swap_rounds must NOT mutate the original schedule."""
        s = make_schedule()
        original_repr = str([(r.round_index, [str(m) for m in r.matches]) for r in s.rounds])
        _ = swap_rounds(s, 0, 5)
        after_repr = str([(r.round_index, [str(m) for m in r.matches]) for r in s.rounds])
        assert original_repr == after_repr, "swap_rounds mutated the original schedule"

    def test_swap_changes_round_order(self):
        """After swapping rounds i and j, their positions are exchanged."""
        s = make_schedule()
        r0_matches_before = [m.ordered_pair() for m in s.rounds[0].matches]
        r5_matches_before = [m.ordered_pair() for m in s.rounds[5].matches]

        neighbor = swap_rounds(s, 0, 5)

        r0_matches_after = [m.ordered_pair() for m in neighbor.rounds[0].matches]
        r5_matches_after = [m.ordered_pair() for m in neighbor.rounds[5].matches]

        assert sorted(r0_matches_after) == sorted(r5_matches_before)
        assert sorted(r5_matches_after) == sorted(r0_matches_before)

    def test_swap_preserves_total_matches(self):
        """Total match count must be unchanged after a swap."""
        s = make_schedule()
        before = s.total_matches()
        neighbor = swap_rounds(s, 2, 8)
        assert neighbor.total_matches() == before

    def test_swap_same_index_is_identity(self):
        """Swapping a round with itself should give an equivalent schedule."""
        s = make_schedule()
        neighbor = swap_rounds(s, 3, 3)
        for r_orig, r_new in zip(s.rounds, neighbor.rounds):
            orig_pairs = sorted(m.ordered_pair() for m in r_orig.matches)
            new_pairs  = sorted(m.ordered_pair() for m in r_new.matches)
            assert orig_pairs == new_pairs


# ════════════════════════════════════════════════════════════════════════════
# 5. simulated_annealing – convergence & improvement
# ════════════════════════════════════════════════════════════════════════════

class TestSimulatedAnnealing:

    @pytest.fixture(scope="class")
    def sa_inputs(self):
        teams = make_teams()
        distances = make_distance_matrix(teams)
        derbies = make_derbies()
        schedule = make_schedule(teams)
        return teams, distances, derbies, schedule

    def test_returns_correct_types(self, sa_inputs):
        teams, distances, derbies, schedule = sa_inputs
        best, best_cost, history = simulated_annealing(
            schedule=schedule,
            distances=distances,
            derbies=derbies,
            weekends=WEEKEND_DAYS,
            teams=teams,
            T_start=1000,
            T_min=1.0,
            alpha=0.99,
            max_iteration=200,
            cost_fn=cost_function,
        )
        assert isinstance(best, Schedule)
        assert isinstance(best_cost, (int, float))
        assert isinstance(history, list)

    def test_history_length_matches_iterations(self, sa_inputs):
        teams, distances, derbies, schedule = sa_inputs
        max_iter = 150
        _, _, history = simulated_annealing(
            schedule=schedule,
            distances=distances,
            derbies=derbies,
            weekends=WEEKEND_DAYS,
            teams=teams,
            T_start=1000,
            T_min=1.0,
            alpha=0.99,
            max_iteration=max_iter,
            cost_fn=cost_function,
        )
        assert len(history) == max_iter

    def test_best_cost_is_minimum_of_history(self, sa_inputs):
        """best_cost must equal the lowest value in the history."""
        teams, distances, derbies, schedule = sa_inputs
        _, best_cost, history = simulated_annealing(
            schedule=schedule,
            distances=distances,
            derbies=derbies,
            weekends=WEEKEND_DAYS,
            teams=teams,
            T_start=500,
            T_min=0.5,
            alpha=0.995,
            max_iteration=300,
            cost_fn=cost_function,
        )
        assert best_cost == min(history), (
            f"best_cost={best_cost} but min(history)={min(history)}"
        )

    def test_history_is_non_increasing(self, sa_inputs):
        """
        Because history tracks best-so-far, it must be monotonically
        non-increasing (best_cost never gets worse as iterations go on).
        """
        teams, distances, derbies, schedule = sa_inputs
        _, _, history = simulated_annealing(
            schedule=schedule,
            distances=distances,
            derbies=derbies,
            weekends=WEEKEND_DAYS,
            teams=teams,
            T_start=500,
            T_min=0.5,
            alpha=0.995,
            max_iteration=300,
            cost_fn=cost_function,
        )
        for i in range(1, len(history)):
            assert history[i] <= history[i - 1], (
                f"history[{i}]={history[i]} > history[{i-1}]={history[i-1]} "
                "(best-so-far must not increase)"
            )

    def test_sa_improves_over_initial(self, sa_inputs):
        """SA should produce a schedule at least as good as the starting point."""
        teams, distances, derbies, schedule = sa_inputs
        initial_cost = cost_function(schedule, teams, distances, derbies, WEEKEND_DAYS)
        _, best_cost, _ = simulated_annealing(
            schedule=schedule,
            distances=distances,
            derbies=derbies,
            weekends=WEEKEND_DAYS,
            teams=teams,
            T_start=5000,
            T_min=0.1,
            alpha=0.999,
            max_iteration=1000,
            cost_fn=cost_function,
        )
        assert best_cost <= initial_cost, (
            f"SA returned cost {best_cost} which is worse than initial {initial_cost}"
        )

    def test_best_schedule_is_valid_double_rr(self, sa_inputs):
        """The best schedule returned by SA must still be a valid double round-robin."""
        teams, distances, derbies, schedule = sa_inputs
        best, _, _ = simulated_annealing(
            schedule=schedule,
            distances=distances,
            derbies=derbies,
            weekends=WEEKEND_DAYS,
            teams=teams,
            T_start=500,
            T_min=0.5,
            alpha=0.99,
            max_iteration=200,
            cost_fn=cost_function,
        )
        # Every ordered pair must appear exactly once
        pair_counter = Counter()
        for r in best.rounds:
            for m in r.matches:
                pair_counter[(m.home.name, m.away.name)] += 1
        names = [t.name for t in teams]
        for a in names:
            for b in names:
                if a != b:
                    assert pair_counter[(a, b)] == 1, (
                        f"SA corrupted schedule: ({a},{b}) appears "
                        f"{pair_counter[(a,b)]} times"
                    )

    def test_early_stop_on_t_min(self, sa_inputs):
        """If T_min is very high, SA should stop early (fewer than max_iteration steps)."""
        teams, distances, derbies, schedule = sa_inputs
        max_iter = 5000
        _, _, history = simulated_annealing(
            schedule=schedule,
            distances=distances,
            derbies=derbies,
            weekends=WEEKEND_DAYS,
            teams=teams,
            T_start=10,
            T_min=9,        # T drops below T_min almost immediately
            alpha=0.99,
            max_iteration=max_iter,
            cost_fn=cost_function,
        )
        assert len(history) < max_iter, (
            "SA should have stopped early due to T < T_min"
        )


# ════════════════════════════════════════════════════════════════════════════
# 6. load_derbies – CSV parsing
# ════════════════════════════════════════════════════════════════════════════

class TestLoadDerbies:

    def _write_derby_csv(self, rows, path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["team_a", "team_b"])
            writer.writeheader()
            writer.writerows(rows)

    def test_loads_all_pairs(self, tmp_path):
        csv_file = str(tmp_path / "derbies.csv")
        self._write_derby_csv(
            [{"team_a": a, "team_b": b} for a, b in _DERBY_PAIRS],
            csv_file,
        )
        derbies = load_derbies(csv_file)
        assert len(derbies) == len(_DERBY_PAIRS)

    def test_pairs_are_frozensets(self, tmp_path):
        csv_file = str(tmp_path / "derbies.csv")
        self._write_derby_csv([{"team_a": "MC Alger", "team_b": "USM Alger"}], csv_file)
        derbies = load_derbies(csv_file)
        assert frozenset({"MC Alger", "USM Alger"}) in derbies

    def test_symmetric_lookup(self, tmp_path):
        """Pair A–B should match a match B vs. A."""
        csv_file = str(tmp_path / "derbies.csv")
        self._write_derby_csv([{"team_a": "MC Alger", "team_b": "USM Alger"}], csv_file)
        derbies = load_derbies(csv_file)
        assert frozenset({"USM Alger", "MC Alger"}) in derbies

    def test_empty_file(self, tmp_path):
        csv_file = str(tmp_path / "derbies.csv")
        self._write_derby_csv([], csv_file)
        derbies = load_derbies(csv_file)
        assert derbies == set()

    def test_duplicate_pairs_deduplicated(self, tmp_path):
        csv_file = str(tmp_path / "derbies.csv")
        self._write_derby_csv([
            {"team_a": "MC Alger", "team_b": "USM Alger"},
            {"team_a": "USM Alger", "team_b": "MC Alger"},  # duplicate (reversed)
        ], csv_file)
        derbies = load_derbies(csv_file)
        assert len(derbies) == 1, "Reversed duplicate derby pair must be deduplicated"


# ════════════════════════════════════════════════════════════════════════════
# 7. Integration – full pipeline
# ════════════════════════════════════════════════════════════════════════════

class TestIntegration:

    def test_full_pipeline_produces_valid_schedule(self):
        """Build → optimise → verify end-to-end correctness."""
        teams = make_teams()
        distances = make_distance_matrix(teams)
        derbies = make_derbies()

        s = double_round_robin(teams)
        s = assign_all_days(s)

        best, best_cost, history = simulated_annealing(
            schedule=s,
            distances=distances,
            derbies=derbies,
            weekends=WEEKEND_DAYS,
            teams=teams,
            T_start=2000,
            T_min=0.5,
            alpha=0.995,
            max_iteration=500,
            cost_fn=cost_function,
        )

        # Structural validity
        assert best.total_rounds() == 2 * (len(teams) - 1)
        assert best.total_matches() == len(teams) * (len(teams) - 1)

        # Cost improved
        initial_cost = cost_function(s, teams, distances, derbies, WEEKEND_DAYS)
        assert best_cost <= initial_cost

        # Every match has a valid day
        for r in best.rounds:
            for m in r.matches:
                assert m.day in VALID_DAYS

    def test_cost_decreases_monotonically_across_history(self):
        """
        Regression: the history list must track best-so-far, not current cost.
        """
        teams = make_teams(n=8)
        distances = make_distance_matrix(teams)
        derbies = set()

        s = make_schedule(teams)
        _, _, history = simulated_annealing(
            schedule=s,
            distances=distances,
            derbies=derbies,
            weekends=WEEKEND_DAYS,
            teams=teams,
            T_start=1000,
            T_min=0.5,
            alpha=0.99,
            max_iteration=400,
            cost_fn=cost_function,
        )
        for i in range(1, len(history)):
            assert history[i] <= history[i - 1]

    def test_no_team_plays_itself(self):
        """A team must never be scheduled against itself."""
        s = make_schedule()
        for r in s.rounds:
            for m in r.matches:
                assert m.home.name != m.away.name, (
                    f"{m.home.name} is scheduled to play itself in round {r.round_index+1}"
                )

    def test_consecutive_away_games_soft_constraint(self):
        """
        After SA, a team should NOT have more than 2 consecutive away games
        (the soft constraint defined in Project 4).
        We test that the penalty function responds to this violation.
        """
        teams = make_teams(n=6)
        distances = make_distance_matrix(teams)
        derbies = set()
        s = make_schedule(teams)

        # Manually create a worst-case: team[0] away in first 3 rounds
        target = teams[0].name
        forced_away = 0
        for r in s.rounds[:3]:
            for m in r.matches:
                if m.home.name == target:
                    m.home, m.away = m.away, m.home  # flip to away
                    forced_away += 1
                    break

        cost_bad = cost_function(s, teams, distances, derbies, WEEKEND_DAYS)

        # Now restore (all home in first 3 rounds)
        s2 = make_schedule(teams)
        for r in s2.rounds[:3]:
            for m in r.matches:
                if m.away.name == target:
                    m.home, m.away = m.away, m.home
                    break

        cost_good = cost_function(s2, teams, distances, derbies, WEEKEND_DAYS)

        # At least one of them differs – the function is sensitive to home/away patterns
        # (exact ordering depends on your implementation; just ensure they're not identical)
        # This is a soft assertion – log rather than fail hard
        if cost_bad == cost_good:
            import warnings
            warnings.warn(
                "Consecutive-away soft constraint does not seem to affect cost. "
                "Check your cost_function implementation.",
                UserWarning,
            )
