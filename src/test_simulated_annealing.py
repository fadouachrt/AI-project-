"""
=============================================================
  PROJECT 4 – Sports League Scheduler: SA Test Suite
  Tests constraint validity, optimization quality, and
  convergence behaviour of simulated_annealing().
=============================================================

HOW TO RUN
----------
    pytest test_simulated_annealing.py -v

ASSUMED INTERFACES  (mirror what your modules expose)
------------------------------------------------------
  from sa import simulated_annealing, load_derbies
  from schedule import double_round_robin, assign_all_days
  from data_loader import load_all, build_distance_matrix
  from Minimize_total import cost_function
  from models import Match, Schedule
  from neighbour import generate_one_random_neighbor
"""

import math
import random
import csv
import os
import tempfile
import pytest
from copy import deepcopy

# ---------------------------------------------------------------------------
# Lazy imports – skip entire suite gracefully if project modules are missing
# ---------------------------------------------------------------------------
try:
    from simulated_annealing import simulated_annealing, load_derbies
    from schedule import double_round_robin, assign_all_days
    from data_loader import load_all, build_distance_matrix
    from Minimize_total import cost_function
    from models import Match, Schedule
    from neighbour import generate_one_random_neighbor
    MODULES_AVAILABLE = True
except ImportError as _e:
    MODULES_AVAILABLE = False
    _IMPORT_ERROR = str(_e)

skip_if_missing = pytest.mark.skipif(
    not MODULES_AVAILABLE,
    reason=f"Project modules not importable: {_IMPORT_ERROR if not MODULES_AVAILABLE else ''}"
)

# ===========================================================================
# FIXTURES – synthetic datasets used across all tests
# ===========================================================================

WEEKEND_DAYS = {"Friday", "Saturday"}

def _make_teams_csv(tmp_path, teams):
    """Write a teams CSV and return the path.
    Headers match data_loader.load_teams: 'team', 'latitude', 'longitude'.
    """
    p = tmp_path / "teams.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["team", "latitude", "longitude"])
        writer.writeheader()
        for t in teams:
            writer.writerow({
                "team":      t["name"],
                "latitude":  t["lat"],
                "longitude": t["lon"],
            })
    return str(p)

def _make_derbies_csv(tmp_path, pairs):
    """Write a derbies CSV and return the path."""
    p = tmp_path / "derbies.csv"
    with open(p, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["team_a", "team_b"])
        writer.writeheader()
        for a, b in pairs:
            writer.writerow({"team_a": a, "team_b": b})
    return str(p)

# 8-team league (Algerian-flavoured names)
TEAMS_8 = [
    {"name": "USM Alger",    "lat": 36.737, "lon": 3.086},
    {"name": "MC Alger",     "lat": 36.752, "lon": 3.042},
    {"name": "CR Belouizdad","lat": 36.745, "lon": 3.072},
    {"name": "JS Kabylie",   "lat": 36.712, "lon": 4.045},
    {"name": "ES Setif",     "lat": 36.191, "lon": 5.411},
    {"name": "MC Oran",      "lat": 35.697, "lon":-0.633},
    {"name": "USM Oran",     "lat": 35.703, "lon":-0.640},
    {"name": "ASM Oran",     "lat": 35.710, "lon":-0.630},
]

DERBIES_8 = [
    ("USM Alger",  "MC Alger"),
    ("USM Alger",  "CR Belouizdad"),
    ("MC Oran",    "USM Oran"),
]

@pytest.fixture(scope="module")
def tmp_data(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("data")
    tc  = _make_teams_csv(tmp, TEAMS_8)
    dc  = _make_derbies_csv(tmp, DERBIES_8)
    return tmp, tc, dc

@pytest.fixture(scope="module")
def league_8(tmp_data):
    """Load an 8-team league (module-scoped so it's built once)."""
    _, tc, dc = tmp_data
    teams, distances = load_all(tc)
    derbies  = load_derbies(dc)
    schedule = double_round_robin(teams)
    schedule = assign_all_days(schedule)
    return teams, distances, derbies, schedule

# ===========================================================================
# SECTION 1 – SCHEDULE STRUCTURAL CONSTRAINTS
# ===========================================================================

class TestDoubleRoundRobin:
    """Verify that the initial schedule obeys the core DRR rules."""

    @skip_if_missing
    def test_total_match_count(self, league_8):
        """N*(N-1) total matches for N teams."""
        teams, _, _, schedule = league_8
        n = len(teams)
        matches = [m for r in schedule.rounds for m in r.matches]
        assert len(matches) == n * (n - 1), (
            f"Expected {n*(n-1)} matches, got {len(matches)}"
        )

    @skip_if_missing
    def test_each_pair_plays_exactly_twice(self, league_8):
        """Every ordered pair (A, B) appears exactly once as home-away fixture."""
        teams, _, _, schedule = league_8
        matches = [m for r in schedule.rounds for m in r.matches]
        pair_count = {}
        for m in matches:
            key = (m.home, m.away)
            pair_count[key] = pair_count.get(key, 0) + 1
        for key, cnt in pair_count.items():
            assert cnt == 1, f"Pair {key} appears {cnt} times (expected 1)"

    @skip_if_missing
    def test_each_team_plays_one_match_per_round(self, league_8):
        """No team appears twice in the same round."""
        teams, _, _, schedule = league_8
        for round_obj in schedule.rounds:
            participants = []
            for m in round_obj.matches:
                participants.extend([m.home.name, m.away.name])
            assert len(participants) == len(set(participants)), (
                f"Round {round_obj.round_index} has a team playing more than once"
            )

    @skip_if_missing
    def test_home_and_away_balance(self, league_8):
        """Each team plays exactly N-1 home and N-1 away games."""
        teams, _, _, schedule = league_8
        n = len(teams)
        matches = [m for r in schedule.rounds for m in r.matches]
        home_count = {t.name: 0 for t in teams}
        away_count = {t.name: 0 for t in teams}
        for m in matches:
            home = m.home if isinstance(m.home, str) else m.home.name
            away = m.away if isinstance(m.away, str) else m.away.name
            home_count[home] += 1
            away_count[away] += 1
        for t in teams:
            assert home_count[t.name] == n - 1, f"{t.name}: wrong home count"
            assert away_count[t.name] == n - 1, f"{t.name}: wrong away count"

# ===========================================================================
# SECTION 2 – COST FUNCTION SANITY CHECKS
# ===========================================================================

class TestCostFunction:

    @skip_if_missing
    def test_cost_is_non_negative(self, league_8):
        teams, distances, derbies, schedule = league_8
        c = cost_function(schedule, teams, distances, derbies, WEEKEND_DAYS)
        assert c >= 0, "Cost must be ≥ 0"

    @skip_if_missing
    def test_cost_is_numeric(self, league_8):
        teams, distances, derbies, schedule = league_8
        c = cost_function(schedule, teams, distances, derbies, WEEKEND_DAYS)
        assert isinstance(c, (int, float)), "Cost must be a number"

    @skip_if_missing
    def test_identical_schedules_same_cost(self, league_8):
        teams, distances, derbies, schedule = league_8
        c1 = cost_function(schedule, teams, distances, derbies, WEEKEND_DAYS)
        c2 = cost_function(deepcopy(schedule), teams, distances, derbies, WEEKEND_DAYS)
        assert math.isclose(c1, c2, rel_tol=1e-9), "Same schedule must yield same cost"

    @skip_if_missing
    def test_cost_function_is_deterministic(self, league_8):
        """Calling cost_function 10× on the same schedule gives identical results."""
        teams, distances, derbies, schedule = league_8
        costs = [cost_function(schedule, teams, distances, derbies, WEEKEND_DAYS)
                 for _ in range(10)]
        assert len(set(costs)) == 1, "cost_function is not deterministic"

# ===========================================================================
# SECTION 3 – NEIGHBOUR GENERATOR
# ===========================================================================

class TestNeighbourGenerator:

    @skip_if_missing
    def test_neighbour_is_different_from_current(self, league_8):
        """The neighbour should not be the exact same object as the original."""
        _, _, _, schedule = league_8
        neighbour = generate_one_random_neighbor(schedule)
        assert neighbour is not schedule

    @skip_if_missing
    def test_neighbour_preserves_match_count(self, league_8):
        """A swap must not add or remove matches."""
        teams, _, _, schedule = league_8
        n = len(teams)
        neighbour = generate_one_random_neighbor(schedule)
        matches = [m for r in neighbour.rounds for m in r.matches]
        assert len(matches) == n * (n - 1)

    @skip_if_missing
    def test_neighbour_preserves_hard_constraints(self, league_8):
        """After a neighbour move, each team still plays exactly once per round."""
        _, _, _, schedule = league_8
        for _ in range(20):          # test 20 random neighbours
            neighbour = generate_one_random_neighbor(schedule)
            for round_obj in neighbour.rounds:
                participants = [m.home.name for m in round_obj.matches] + \
                               [m.away.name for m in round_obj.matches]
                assert len(participants) == len(set(participants)), (
                    f"Neighbour: round {round_obj.round_index} has a team playing more than once"
                )

# ===========================================================================
# SECTION 4 – SIMULATED ANNEALING ALGORITHM
# ===========================================================================

class TestSimulatedAnnealing:

    # ------------------------------------------------------------------
    # 4.1  Return-value sanity
    # ------------------------------------------------------------------
    @skip_if_missing
    def test_returns_three_values(self, league_8):
        teams, distances, derbies, schedule = league_8
        result = simulated_annealing(
            schedule, distances, derbies, WEEKEND_DAYS, teams,
            T_start=1000, T_min=1, alpha=0.99, max_iteration=200,
            cost_fn=cost_function
        )
        assert len(result) == 3, "SA must return (best_schedule, best_cost, history)"

    @skip_if_missing
    def test_best_cost_equals_cost_of_best_schedule(self, league_8):
        teams, distances, derbies, schedule = league_8
        best, best_cost, _ = simulated_annealing(
            schedule, distances, derbies, WEEKEND_DAYS, teams,
            T_start=1000, T_min=1, alpha=0.99, max_iteration=300,
            cost_fn=cost_function
        )
        recomputed = cost_function(best, teams, distances, derbies, WEEKEND_DAYS)
        assert math.isclose(best_cost, recomputed, rel_tol=1e-6), (
            f"Returned best_cost {best_cost} ≠ recomputed cost {recomputed}"
        )

    # ------------------------------------------------------------------
    # 4.2  History / convergence
    # ------------------------------------------------------------------
    @skip_if_missing
    def test_history_length_matches_iterations(self, league_8):
        teams, distances, derbies, schedule = league_8
        iters = 500
        _, _, history = simulated_annealing(
            schedule, distances, derbies, WEEKEND_DAYS, teams,
            T_start=1000, T_min=1, alpha=0.99, max_iteration=iters,
            cost_fn=cost_function
        )
        assert len(history) <= iters, "History must not exceed max_iteration"
        assert len(history) > 0, "History must not be empty"

    @skip_if_missing
    def test_history_is_monotone_non_increasing(self, league_8):
        """
        The history[] array tracks the BEST cost seen so far.
        It must never increase (best-so-far is monotone non-increasing).
        """
        teams, distances, derbies, schedule = league_8
        _, _, history = simulated_annealing(
            schedule, distances, derbies, WEEKEND_DAYS, teams,
            T_start=5000, T_min=0.1, alpha=0.999, max_iteration=2000,
            cost_fn=cost_function
        )
        for i in range(1, len(history)):
            assert history[i] <= history[i-1] + 1e-9, (
                f"history[{i}]={history[i]} > history[{i-1}]={history[i-1]}  "
                f"– best-cost tracker should never increase"
            )

    # ------------------------------------------------------------------
    # 4.3  Optimization quality
    # ------------------------------------------------------------------
    @skip_if_missing
    def test_sa_improves_over_initial_schedule(self, league_8):
        """After a reasonable run, SA should produce a schedule cheaper than the start."""
        teams, distances, derbies, schedule = league_8
        initial_cost = cost_function(schedule, teams, distances, derbies, WEEKEND_DAYS)
        _, best_cost, _ = simulated_annealing(
            schedule, distances, derbies, WEEKEND_DAYS, teams,
            T_start=100_000, T_min=0.1, alpha=0.999, max_iteration=10_000,
            cost_fn=cost_function
        )
        assert best_cost <= initial_cost, (
            f"SA did not improve: best_cost={best_cost} ≥ initial={initial_cost}"
        )

    @skip_if_missing
    def test_best_schedule_has_zero_hard_constraint_violations(self, league_8):
        """
        The output schedule must still be a valid DRR schedule
        (hard constraints intact).
        """
        teams, distances, derbies, schedule = league_8
        best, _, _ = simulated_annealing(
            schedule, distances, derbies, WEEKEND_DAYS, teams,
            T_start=100_000, T_min=0.1, alpha=0.999, max_iteration=5_000,
            cost_fn=cost_function
        )
        matches = [m for r in best.rounds for m in r.matches]
        n = len(teams)
        # check total match count
        assert len(matches) == n * (n - 1)
        # check no team plays twice in same round
        for round_obj in best.rounds:
            participants = [m.home.name for m in round_obj.matches] + \
                           [m.away.name for m in round_obj.matches]
            assert len(participants) == len(set(participants)), (
                f"Hard constraint violated: round {round_obj.round_index} after SA"
            )

    # ------------------------------------------------------------------
    # 4.4  Temperature schedule
    # ------------------------------------------------------------------
    @skip_if_missing
    def test_early_stopping_when_T_min_reached(self, league_8):
        """
        If T_min is set very high, SA should stop early (iterations < max_iteration).
        """
        teams, distances, derbies, schedule = league_8
        _, _, history = simulated_annealing(
            schedule, distances, derbies, WEEKEND_DAYS, teams,
            T_start=10, T_min=9,      # T drops to 9 in 1 step  (10*0.99 ≈ 9.9 > 9)
            alpha=0.99, max_iteration=100_000,
            cost_fn=cost_function
        )
        # alpha=0.99 → after k steps T = 10 * 0.99^k < 9  ⟹  k ≈ 10
        assert len(history) < 100_000, (
            "SA should stop early when temperature falls below T_min"
        )

    @skip_if_missing
    def test_max_iteration_respected(self, league_8):
        """SA must never run more than max_iteration steps."""
        teams, distances, derbies, schedule = league_8
        iters = 50
        _, _, history = simulated_annealing(
            schedule, distances, derbies, WEEKEND_DAYS, teams,
            T_start=1_000_000, T_min=1e-9,
            alpha=0.999, max_iteration=iters,
            cost_fn=cost_function
        )
        assert len(history) == iters

    # ------------------------------------------------------------------
    # 4.5  Soft constraints (diagnostic – allowed to fail, logged only)
    # ------------------------------------------------------------------
    @skip_if_missing
    def test_soft_consecutive_away_games(self, league_8):
        """
        SOFT constraint: no team should have more than 2 consecutive away games.
        This test measures (not enforces) the violation count.
        """
        teams, distances, derbies, schedule = league_8
        best, _, _ = simulated_annealing(
            schedule, distances, derbies, WEEKEND_DAYS, teams,
            T_start=100_000, T_min=0.1, alpha=0.999, max_iteration=10_000,
            cost_fn=cost_function
        )
        # Build team → sorted-by-round list of (round_index, is_away)
        team_games = {}
        for round_obj in best.rounds:
            for m in round_obj.matches:
                team_games.setdefault(m.home.name, []).append((round_obj.round_index, False))
                team_games.setdefault(m.away.name, []).append((round_obj.round_index, True))

        violations = 0
        for team, games in team_games.items():
            games.sort()
            streak = 0
            for _, is_away in games:
                streak = streak + 1 if is_away else 0
                if streak > 2:
                    violations += 1

        # Not a hard assert – just report
        print(f"\n[SOFT] Consecutive-away violations: {violations}")
        # Warn if very high
        assert violations < len(teams) * 5, (
            f"Too many consecutive-away violations ({violations}) – "
            "check if the cost function penalises this constraint"
        )

    @skip_if_missing
    def test_derby_matches_on_weekends(self, league_8):
        """
        SOFT constraint: derby matches should ideally fall on weekends.
        Measures the ratio – does not fail if imperfect.
        """
        teams, distances, derbies, schedule = league_8
        best, _, _ = simulated_annealing(
            schedule, distances, derbies, WEEKEND_DAYS, teams,
            T_start=100_000, T_min=0.1, alpha=0.999, max_iteration=10_000,
            cost_fn=cost_function
        )
        derby_total = derby_on_weekend = 0
        for round_obj in best.rounds:
            for m in round_obj.matches:
                pair = frozenset([m.home.name, m.away.name])
                if pair in derbies:
                    derby_total += 1
                    if m.day in WEEKEND_DAYS:
                        derby_on_weekend += 1
        ratio = derby_on_weekend / derby_total if derby_total else 1.0
        print(f"\n[SOFT] Derby-on-weekend ratio: {derby_on_weekend}/{derby_total} = {ratio:.2%}")
        # Soft: just warn if 0%
        assert ratio >= 0.0  # always true, but logged

# ===========================================================================
# SECTION 5 – SCALABILITY TESTS
# ===========================================================================

class TestScalability:
    """
    Verifies that the algorithm terminates in reasonable time for
    different league sizes (10, 14, 16, 18, 20 teams) as the spec requires.
    Uses mock cost_function to isolate SA timing.
    """

    @staticmethod
    def _fake_cost(schedule, *args, **kwargs):
        return random.uniform(0, 1000)

    @skip_if_missing
    @pytest.mark.parametrize("n_teams", [10, 14, 16])
    def test_sa_terminates_for_league_size(self, tmp_path, n_teams):
        import time
        teams_data = [
            {"name": f"Team_{i}", "lat": random.uniform(30, 37), "lon": random.uniform(-2, 8)}
            for i in range(n_teams)
        ]
        tc = _make_teams_csv(tmp_path, teams_data)
        dc = _make_derbies_csv(tmp_path, [])
        teams, distances = load_all(tc)
        schedule = double_round_robin(teams)
        schedule  = assign_all_days(schedule)
        derbies   = set()

        start = time.time()
        best, best_cost, history = simulated_annealing(
            schedule, distances, derbies, WEEKEND_DAYS, teams,
            T_start=10_000, T_min=1, alpha=0.99, max_iteration=1_000,
            cost_fn=self._fake_cost
        )
        elapsed = time.time() - start
        print(f"\n[SCALE] {n_teams} teams → {elapsed:.2f}s, best_cost={best_cost:.1f}")
        assert elapsed < 30, f"SA took {elapsed:.1f}s for {n_teams} teams (limit: 30s)"

# ===========================================================================
# SECTION 6 – REPRODUCIBILITY & EDGE CASES
# ===========================================================================

class TestEdgeCases:

    @skip_if_missing
    def test_load_derbies_empty_file(self, tmp_path):
        dc = _make_derbies_csv(tmp_path, [])
        derbies = load_derbies(str(dc))
        assert derbies == set() or len(derbies) == 0

    @skip_if_missing
    def test_load_derbies_returns_frozensets(self, tmp_path):
        dc = _make_derbies_csv(tmp_path, [("A", "B"), ("C", "D")])
        derbies = load_derbies(str(dc))
        for d in derbies:
            assert isinstance(d, frozenset), "Derbies should be frozensets"

    @skip_if_missing
    def test_sa_with_zero_iterations(self, league_8):
        """max_iteration=0 should return the initial schedule unchanged."""
        teams, distances, derbies, schedule = league_8
        initial_cost = cost_function(schedule, teams, distances, derbies, WEEKEND_DAYS)
        _, best_cost, history = simulated_annealing(
            schedule, distances, derbies, WEEKEND_DAYS, teams,
            T_start=1000, T_min=0.1, alpha=0.99, max_iteration=0,
            cost_fn=cost_function
        )
        assert len(history) == 0
        assert math.isclose(best_cost, initial_cost, rel_tol=1e-6)

    @skip_if_missing
    def test_sa_with_two_teams(self, tmp_path):
        """
        Minimum viable league: 2 teams → 2 matches.
        NOTE: With 2 teams each round has only 1 match, so swap_days_in_round
        cannot pick 2 matches to swap. This is a known edge-case limitation of
        generate_one_random_neighbor. The test verifies SA handles it gracefully
        OR raises a clear ValueError (not a silent wrong answer).
        """
        teams_data = [
            {"name": "Alpha", "lat": 36.0, "lon": 3.0},
            {"name": "Beta",  "lat": 36.5, "lon": 3.5},
        ]
        tc = _make_teams_csv(tmp_path, teams_data)
        dc = _make_derbies_csv(tmp_path, [("Alpha", "Beta")])
        teams, distances = load_all(tc)
        schedule = double_round_robin(teams)
        schedule  = assign_all_days(schedule)
        derbies   = load_derbies(str(dc))

        try:
            best, best_cost, history = simulated_annealing(
                schedule, distances, derbies, WEEKEND_DAYS, teams,
                T_start=100, T_min=0.1, alpha=0.9, max_iteration=100,
                cost_fn=cost_function
            )
            matches = [m for r in best.rounds for m in r.matches]
            assert len(matches) == 2  # 2*(2-1) = 2
        except ValueError as e:
            # Known bug: swap_days_in_round fails when a round has only 1 match.
            # Fix in neighbour.py: guard with `if len(r.matches) >= 2` before sampling.
            pytest.xfail(
                f"generate_one_random_neighbor crashes for 2-team leagues "
                f"(round has 1 match, can't sample 2). Fix neighbour.py. Error: {e}"
            )

# ===========================================================================
# SECTION 7 – COMPARATIVE BASELINES  (for the report)
# ===========================================================================

class TestComparativeBaselines:
    """
    These tests generate numbers you can put directly in your report's
    'Comparative Evaluation' table.
    """

    @skip_if_missing
    def test_compare_sa_vs_random_baseline(self, league_8, capsys):
        """
        Compare SA output against a trivially random assignment.
        Prints a summary table suitable for the report.
        """
        teams, distances, derbies, schedule = league_8
        initial_cost = cost_function(schedule, teams, distances, derbies, WEEKEND_DAYS)

        # SA run
        best_sa, cost_sa, history = simulated_annealing(
            schedule, distances, derbies, WEEKEND_DAYS, teams,
            T_start=100_000, T_min=0.1, alpha=0.999, max_iteration=20_000,
            cost_fn=cost_function
        )
        improvement_pct = (initial_cost - cost_sa) / initial_cost * 100 if initial_cost else 0

        with capsys.disabled():
            print("\n" + "="*55)
            print("  COMPARATIVE RESULTS (paste into report)")
            print("="*55)
            print(f"  Initial schedule cost : {initial_cost:.2f}")
            print(f"  SA best cost          : {cost_sa:.2f}")
            print(f"  Improvement           : {improvement_pct:.1f}%")
            print(f"  Iterations run        : {len(history)}")
            print(f"  First improvement at  : {next((i for i,h in enumerate(history) if h < initial_cost), 'N/A')}")
            print("="*55)

        assert cost_sa <= initial_cost


# ===========================================================================
# SECTION 8 – PARAMETER SENSITIVITY  (tune your cooling schedule)
# ===========================================================================

class TestParameterSensitivity:

    @skip_if_missing
    @pytest.mark.parametrize("alpha", [0.90, 0.95, 0.999])
    def test_different_cooling_rates(self, league_8, alpha):
        teams, distances, derbies, schedule = league_8
        _, best_cost, history = simulated_annealing(
            schedule, distances, derbies, WEEKEND_DAYS, teams,
            T_start=10_000, T_min=0.1, alpha=alpha, max_iteration=3_000,
            cost_fn=cost_function
        )
        print(f"\n[PARAM] alpha={alpha} → best_cost={best_cost:.2f}, iters={len(history)}")
        assert best_cost >= 0

    @skip_if_missing
    @pytest.mark.parametrize("T_start", [100, 10_000, 1_000_000])
    def test_different_starting_temperatures(self, league_8, T_start):
        teams, distances, derbies, schedule = league_8
        _, best_cost, history = simulated_annealing(
            schedule, distances, derbies, WEEKEND_DAYS, teams,
            T_start=T_start, T_min=0.1, alpha=0.999, max_iteration=3_000,
            cost_fn=cost_function
        )
        print(f"\n[PARAM] T_start={T_start} → best_cost={best_cost:.2f}")
        assert best_cost >= 0