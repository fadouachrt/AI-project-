"""
test_sa.py  —  run this file directly to test simulated_annealing()
Place it inside the src/ folder, then run:
    python test_sa.py
No CSV files needed. No teammates' code needed.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))  # make sure src/ is on the path

import math, random, copy
from simulated_annealing import simulated_annealing
from models import Match, Round, Schedule
from neighbour import generate_one_random_neighbor


# ─────────────────────────────────────────────
#  1.  TINY SELF-CONTAINED DATA  (4 teams)
# ─────────────────────────────────────────────

TEAMS = ["A", "B", "C", "D"]

# distances[away][home] = km the away team travels
DISTANCES = {
    "A": {"A": 0,   "B": 100, "C": 200, "D": 300},
    "B": {"A": 100, "B": 0,   "C": 150, "D": 250},
    "C": {"A": 200, "B": 150, "C": 0,   "D": 350},
    "D": {"A": 300, "B": 250, "C": 350, "D": 0  },
}

# A vs B is a derby
DERBIES = {frozenset(["A", "B"])}

WEEKENDS = ["Friday", "Saturday"]

DAYS = ["Friday", "Saturday", "Sunday"]

# ─────────────────────────────────────────────
#  2.  BUILD A VALID 4-TEAM DRR SCHEDULE
#      (hardcoded so we don't need schedule.py)
# ─────────────────────────────────────────────

def build_test_schedule():
    """
    4-team double round-robin. Every pair meets exactly twice.
    6 rounds total. Each match gets a day from DAYS (cycling).
    """
    raw = [
        # first leg
        [("A","B"), ("C","D")],
        [("A","C"), ("D","B")],
        [("A","D"), ("B","C")],
        # second leg (home/away flipped)
        [("B","A"), ("D","C")],
        [("C","A"), ("B","D")],
        [("D","A"), ("C","B")],
    ]
    rounds = []
    day_cycle = ["Friday", "Saturday", "Sunday"]
    for r_idx, matchups in enumerate(raw):
        round_obj = Round(round_index=r_idx)
        round_obj.third_day = "Sunday"
        round_obj.days = ["Friday", "Saturday", "Sunday"]
        for m_idx, (home, away) in enumerate(matchups):
            day = day_cycle[m_idx % len(day_cycle)]
            round_obj.matches.append(Match(home=home, away=away, day=day))
        rounds.append(round_obj)
    return Schedule(rounds=rounds, teams=TEAMS)

# ─────────────────────────────────────────────
#  3.  SELF-CONTAINED COST FUNCTION
#      (no dependency on fixed_version.py)
# ─────────────────────────────────────────────

MATCH_DAYS = {
    "Monday":0,"Tuesday":1,"Wednesday":2,"Thursday":3,
    "Friday":4,"Saturday":5,"Sunday":6
}

def cost_function(schedule, teams, distances, derbies, weekends, penalty=500):
    total = 0

    # travel distance: away team travels to home stadium
    for r in schedule.rounds:
        for m in r.matches:
            total += distances[m.away][m.home]

    # derby penalty: derby not on a weekend day
    for r in schedule.rounds:
        for m in r.matches:
            if frozenset([m.home, m.away]) in derbies:
                if m.day not in weekends:
                    total += penalty

    # rest penalty: less than 2 days between consecutive matches for same team
    for team in teams:
        played_days = []
        for r in schedule.rounds:
            for m in r.matches:
                if m.home == team or m.away == team:
                    played_days.append(MATCH_DAYS.get(m.day, 0))
        for i in range(len(played_days) - 1):
            gap = played_days[i+1] - played_days[i]
            if gap % 7 < 2:
                total += penalty

    return total

# ─────────────────────────────────────────────
#  4.  RUN THE TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  Simulated Annealing — isolated test")
    print("=" * 50)

    schedule = build_test_schedule()
    initial_cost = cost_function(schedule, TEAMS, DISTANCES, DERBIES, WEEKENDS)
    print(f"\nInitial schedule cost : {initial_cost}")
    print("\nInitial schedule:")
    schedule.print_schedule()

    print("\nRunning SA...")
    best, best_cost, history = simulated_annealing(
        schedule      = schedule,
        distances     = DISTANCES,
        derbies       = DERBIES,
        weekends      = WEEKENDS,
        teams         = TEAMS,
        T_start       = 5000,
        T_min         = 0.2,
        alpha         = 0.80,
        max_iteration = 5000,   
        cost_fn=cost_function
    )

    print(f"\nBest cost found : {best_cost}")
    print(f"Improvement     : {initial_cost - best_cost} ({100*(initial_cost-best_cost)/initial_cost:.1f}%)")
    print(f"Iterations ran  : {len(history)}")
    print("\nBest schedule:")
    best.print_schedule()

    # basic sanity checks
    print("\n--- Sanity checks ---")
    n = len(TEAMS)
    expected_rounds = 2 * (n - 1)
    assert len(best.rounds) == expected_rounds, f"Expected {expected_rounds} rounds, got {len(best.rounds)}"
    print(f"[OK] Round count = {expected_rounds}")

    pair_count = {}
    for r in best.rounds:
        for m in r.matches:
            key = tuple(sorted([m.home, m.away]))
            pair_count[key] = pair_count.get(key, 0) + 1
    for pair, count in pair_count.items():
        assert count == 2, f"Pair {pair} appears {count} times, expected 2"
    print(f"[OK] Every pair meets exactly twice")

    for r in best.rounds:
        teams_in_round = []
        for m in r.matches:
            teams_in_round += [m.home, m.away]
        assert len(teams_in_round) == len(set(teams_in_round)), f"Round {r.round_index} has a team playing twice"
    print(f"[OK] No team plays twice in the same round")

    assert best_cost <= initial_cost, "SA returned a worse schedule than the initial one!"
    print(f"[OK] SA improved or matched the initial cost")

    print("\nAll checks passed. Your SA is working correctly.")
