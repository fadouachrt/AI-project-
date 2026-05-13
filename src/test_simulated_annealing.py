"""
test_simulated_annealing.py
============================
Complete test suite for simulated_annealing().
Modelled after the greedy test structure.

Run from the project ROOT:
    python src/test_simulated_annealing.py

Or from inside src/:
    python test_simulated_annealing.py
"""

import os
import sys
import math
import time
import random

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from models        import Team, Match, Round, Schedule
from schedule      import double_round_robin, assign_all_days
from data_loader   import load_all, load_derbies
from Minimize_total import cost_function, total_distance
from Soft_constraints import (Derbies_penalty, Rest_day_penalty,
                               successive_away_penalty)
from simulated_annealing import simulated_annealing
from neighbour     import generate_one_random_neighbor

# ── Constants ─────────────────────────────────────────────────────────────────
PENALTY     = 500
WEEKENDS    = {"Friday", "Saturday"}

# ── Helpers ───────────────────────────────────────────────────────────────────
def _find_data(candidates):
    return next((p for p in candidates if os.path.exists(p)), None)

def _section(title):
    print("\n" + "=" * 56)
    print(f"  {title}")
    print("=" * 56)

def _ok(label):   print(f"  ✓  {label}")
def _fail(label): print(f"  ✗  {label}")

def _check(condition, ok_msg, fail_msg):
    if condition:
        _ok(ok_msg)
    else:
        _fail(fail_msg)
    return condition

# ══════════════════════════════════════════════════════════════════════════════
# 0.  LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════
teams_path = _find_data(["data/teams.csv", "../data/teams.csv", "teams.csv"])
derby_path = _find_data(["data/derbies.csv", "../data/derbies.csv", "derbies.csv"])

if teams_path is None:
    print("ERROR: teams.csv not found. Run from project root.")
    raise SystemExit(1)

teams, dist_matrix = load_all(teams_path)
derbies = load_derbies(derby_path) if derby_path else set()

if not derby_path:
    print("WARNING: derbies.csv not found — derby penalty will be 0.\n")

print(f"Loaded {len(teams)} teams | {len(derbies)} derby pairs.\n")

# ── Build initial schedule ────────────────────────────────────────────────────
initial_schedule = assign_all_days(double_round_robin(teams))
initial_cost     = cost_function(initial_schedule, teams,
                                 dist_matrix, derbies, WEEKENDS, PENALTY)


# ══════════════════════════════════════════════════════════════════════════════
# 1.  COST FUNCTION SANITY — does it return different values for different schedules?
# ══════════════════════════════════════════════════════════════════════════════
_section("1. COST FUNCTION SANITY")

neighbor_sample = generate_one_random_neighbor(initial_schedule)
neighbor_cost   = cost_function(neighbor_sample, teams,
                                dist_matrix, derbies, WEEKENDS, PENALTY)

print(f"\n  Initial cost  : {initial_cost:>12,.1f}")
print(f"  Neighbor cost : {neighbor_cost:>12,.1f}")
print(f"  Difference    : {neighbor_cost - initial_cost:>+12,.1f}")

_check(initial_cost != neighbor_cost,
       "Cost changes between different schedules — cost function is responsive",
       "COST IS IDENTICAL for two different schedules — cost function may be broken")

# ── Cost component breakdown ──────────────────────────────────────────────────
print("\n── Cost breakdown on initial schedule ──")
dist_cost  = total_distance(initial_schedule, dist_matrix, teams)
rest_cost  = Rest_day_penalty(initial_schedule, teams, PENALTY)
derby_cost = Derbies_penalty(initial_schedule, derbies, WEEKENDS, PENALTY)
away_cost  = sum(successive_away_penalty(t, initial_schedule, PENALTY)
                 for t in teams)

print(f"  Travel distance   : {dist_cost:>10,.1f} km")
print(f"  Rest-day penalty  : {rest_cost:>10,.0f}")
print(f"  Derby penalty     : {derby_cost:>10,.0f}")
print(f"  Successive away   : {away_cost:>10,.0f}")
print(f"  ── Sum            : {dist_cost+rest_cost+derby_cost+away_cost:>10,.1f}")
print(f"  cost_function()   : {initial_cost:>10,.1f}")

_check(abs((dist_cost + rest_cost + derby_cost + away_cost) - initial_cost) < 1,
       "Component sum matches cost_function() output",
       "Component sum does NOT match cost_function() — one penalty may be double-counted or missing")

_check(dist_cost > 0,
       f"Travel distance is non-zero ({dist_cost:,.1f} km)",
       "Travel distance is ZERO — total_distance() has a bug")

_check(rest_cost >= 0,
       f"Rest-day penalty is non-negative ({rest_cost:,.0f})",
       "Rest-day penalty is negative — bug in Rest_day_penalty()")

_check(derby_cost >= 0,
       f"Derby penalty is non-negative ({derby_cost:,.0f})",
       "Derby penalty is negative — bug in Derbies_penalty()")


# ══════════════════════════════════════════════════════════════════════════════
# 2.  NEIGHBOUR SANITY — does generate_one_random_neighbor() work correctly?
# ══════════════════════════════════════════════════════════════════════════════
_section("2. NEIGHBOUR SANITY")

print("\n  Generating 200 random neighbours and checking each one...\n")

teams_set          = {t.name for t in teams}
n_teams            = len(teams)
expected_per_round = n_teams // 2
different_count    = 0
invalid_count      = 0

for trial in range(200):
    nb = generate_one_random_neighbor(initial_schedule)

    # check 1 — every round still has the right number of matches
    for r in nb.rounds:
        if len(r.matches) != expected_per_round:
            invalid_count += 1
            break

    # check 2 — no team appears twice in one round
    for r in nb.rounds:
        seen = set()
        for m in r.matches:
            if m.home.name in seen or m.away.name in seen:
                invalid_count += 1
            seen.add(m.home.name)
            seen.add(m.away.name)

    # check 3 — neighbour is actually different from original
    original_sig = [(m.home.name, m.away.name, m.day)
                    for r in initial_schedule.rounds for m in r.matches]
    neighbour_sig = [(m.home.name, m.away.name, m.day)
                     for r in nb.rounds for m in r.matches]
    if original_sig != neighbour_sig:
        different_count += 1

_check(invalid_count == 0,
       f"All 200 neighbours are structurally valid (no duplicates, correct match count)",
       f"{invalid_count} invalid neighbours detected — neighbour function has a bug")

_check(different_count >= 180,
       f"{different_count}/200 neighbours differ from original (expected ≥ 180)",
       f"Only {different_count}/200 neighbours differ — neighbour function may be stuck")


# ══════════════════════════════════════════════════════════════════════════════
# 3.  ACCEPTANCE PROBABILITY — does math.exp behave as expected?
# ══════════════════════════════════════════════════════════════════════════════
_section("3. ACCEPTANCE PROBABILITY LOGIC")

print()
cases = [
    (  -200, 5000, "always accept (delta < 0)"),
    (   300, 5000, "high T  — should accept ~94% of the time"),
    (   300,  500, "medium T — should accept ~55% of the time"),
    (   300,   10, "low T   — should accept ~0.09% of the time"),
]

for delta, T, label in cases:
    if delta < 0:
        p = 1.0
    else:
        p = math.exp(-delta / T)
    print(f"  delta={delta:>5}, T={T:>5} → P={p:.4f}   ({label})")

_check(math.exp(-300 / 5000) > 0.9,
       "High temperature accepts bad moves freely (P > 0.9)",
       "High temperature acceptance is too low — check formula")

_check(math.exp(-300 / 10) < 0.01,
       "Low temperature almost never accepts bad moves (P < 0.01)",
       "Low temperature acceptance is too high — check formula")

# Empirical test: at high T, should accept most bad moves
random.seed(42)
accepts_high_T = sum(1 for _ in range(1000)
                     if random.random() < math.exp(-300 / 5000))
accepts_low_T  = sum(1 for _ in range(1000)
                     if random.random() < math.exp(-300 / 10))

_check(accepts_high_T > 900,
       f"Empirical: {accepts_high_T}/1000 bad moves accepted at T=5000 (expected >900)",
       f"Empirical: only {accepts_high_T}/1000 accepted at T=5000 — too low")

_check(accepts_low_T < 10,
       f"Empirical: {accepts_low_T}/1000 bad moves accepted at T=10 (expected <10)",
       f"Empirical: {accepts_low_T}/1000 accepted at T=10 — too high")


# ══════════════════════════════════════════════════════════════════════════════
# 4.  COOLING SCHEDULE — does temperature cool correctly?
# ══════════════════════════════════════════════════════════════════════════════
_section("4. COOLING SCHEDULE")

T       = 10000.0
alpha   = 0.995
T_min   = 0.1
steps   = 0

while T > T_min:
    T = T * alpha
    steps += 1

print(f"\n  T_start={10000}, alpha={alpha}, T_min={T_min}")
print(f"  Total cooling steps : {steps:,}")
print(f"  Final T             : {T:.6f}")

_check(9000 < steps < 30000,
       f"Cooling takes {steps:,} steps — reasonable for SA",
       f"Cooling takes {steps:,} steps — may be too few or too many")

_check(T <= T_min,
       "Temperature correctly reaches T_min",
       "Temperature did not reach T_min — check cooling loop condition")

# Show temperature at key milestones
T = 10000.0
print(f"\n  Temperature milestones:")
for milestone in [500, 1000, 5000, 10000, 15000]:
    T_at = 10000.0 * (alpha ** milestone)
    print(f"    Step {milestone:>6,}  →  T = {T_at:>10.4f}")


# ══════════════════════════════════════════════════════════════════════════════
# 5.  RUN SA — does it actually improve the cost?
# ══════════════════════════════════════════════════════════════════════════════
_section("5. SA IMPROVEMENT TEST (20 000 iterations)")

print(f"\n  Initial cost : {initial_cost:>12,.1f}")
print("  Running SA... (this may take 30–60 seconds)\n")

t0 = time.time()

best_schedule, best_cost, history = simulated_annealing(
    schedule      = initial_schedule,
    distances     = dist_matrix,
    derbies       = derbies,
    weekends      = WEEKENDS,
    teams         = teams,
    T_start       = 10000,
    T_min         = 0.1,
    alpha         = 0.9994,
    max_iteration = 20000,
    cost_fn       = cost_function
)

elapsed = time.time() - t0

print(f"  SA runtime   : {elapsed:.1f}s")
print(f"  Initial cost : {initial_cost:>12,.1f}")
print(f"  Best cost    : {best_cost:>12,.1f}")
improvement = initial_cost - best_cost
pct         = (improvement / initial_cost * 100) if initial_cost > 0 else 0
print(f"  Improvement  : {improvement:>+12,.1f}  ({pct:.1f}%)")

_check(best_cost < initial_cost,
       f"SA improved the schedule by {improvement:,.1f} ({pct:.1f}%)",
       f"SA did NOT improve the cost — best_cost ({best_cost:,.1f}) >= initial_cost ({initial_cost:,.1f})")

_check(best_cost > 0,
       "Best cost is positive (non-trivial solution)",
       "Best cost is 0 or negative — something is wrong")


# ══════════════════════════════════════════════════════════════════════════════
# 6.  HISTORY LOG — is it correctly recorded?
# ══════════════════════════════════════════════════════════════════════════════
_section("6. HISTORY LOG")

print(f"\n  History length : {len(history)}")
print(f"  history[0]     : {history[0]:,.1f}   (first iteration cost)")
print(f"  history[-1]    : {history[-1]:,.1f}   (last iteration cost)")
print(f"  min(history)   : {min(history):,.1f}   (best cost ever seen in loop)")

_check(len(history) == 20000,
       f"History has exactly 20 000 entries (one per iteration)",
       f"History has {len(history)} entries — expected 20 000")

_check(history[-1] <= history[0],
       "Last history entry ≤ first entry (SA improved or stayed equal)",
       "Last history entry > first entry — best tracking may be broken")

_check(abs(min(history) - best_cost) < 1,
       f"min(history) matches best_cost — best tracking is correct",
       f"min(history)={min(history):,.1f} != best_cost={best_cost:,.1f} — best tracking has a bug")

# Check convergence trend — first quarter avg vs last quarter avg
q = len(history) // 4
first_q_avg = sum(history[:q]) / q
last_q_avg  = sum(history[3*q:]) / q
print(f"\n  First-quarter avg cost : {first_q_avg:>12,.1f}")
print(f"  Last-quarter  avg cost : {last_q_avg:>12,.1f}")

_check(last_q_avg <= first_q_avg,
       "Cost trend is downward (last-quarter avg ≤ first-quarter avg)",
       "Cost trend is UPWARD — SA is not improving over time")


# ══════════════════════════════════════════════════════════════════════════════
# 7.  OUTPUT SCHEDULE VALIDITY — hard constraints on the best schedule
# ══════════════════════════════════════════════════════════════════════════════
_section("7. HARD CONSTRAINTS ON BEST SCHEDULE")

n          = len(teams)
exp_rounds = (n - 1) * 2

print(f"\n── Structure ──")

_check(best_schedule.total_rounds() == exp_rounds,
       f"Correct number of rounds: {best_schedule.total_rounds()} == {exp_rounds}",
       f"Wrong round count: got {best_schedule.total_rounds()}, expected {exp_rounds}")

_check(best_schedule.total_matches() == exp_rounds * (n // 2),
       f"Correct total matches: {best_schedule.total_matches()}",
       f"Wrong match count: {best_schedule.total_matches()}")

print(f"\n── Per-round checks ──")
wrong_match_count = 0
duplicate_team    = 0

for r in best_schedule.rounds:
    if len(r.matches) != n // 2:
        wrong_match_count += 1
    seen = set()
    for m in r.matches:
        if m.home.name in seen or m.away.name in seen:
            duplicate_team += 1
        seen.add(m.home.name)
        seen.add(m.away.name)

_check(wrong_match_count == 0,
       f"All rounds have exactly {n//2} matches",
       f"{wrong_match_count} rounds have wrong number of matches")

_check(duplicate_team == 0,
       "No team appears twice in the same round",
       f"{duplicate_team} rounds have a team appearing twice")

print(f"\n── Pair counts (each pair should appear exactly twice) ──")
pair_count = {}
for r in best_schedule.rounds:
    for m in r.matches:
        key = frozenset([m.home.name, m.away.name])
        pair_count[key] = pair_count.get(key, 0) + 1

wrong_pairs = [(p, c) for p, c in pair_count.items() if c != 2]

_check(len(wrong_pairs) == 0,
       f"All {len(pair_count)} pairs appear exactly twice (Double Round-Robin)",
       f"{len(wrong_pairs)} pairs appear the wrong number of times:")

if wrong_pairs:
    for pair, count in wrong_pairs[:5]:
        names = list(pair)
        print(f"    ✗  {names[0]} vs {names[1]}  →  appears {count} times")

print(f"\n── All matches have a day assigned ──")
missing_day = sum(1 for r in best_schedule.rounds
                  for m in r.matches if m.day is None)
_check(missing_day == 0,
       "Every match has a day assigned",
       f"{missing_day} matches have no day assigned")


# ══════════════════════════════════════════════════════════════════════════════
# 8.  SOFT CONSTRAINTS ON BEST SCHEDULE
# ══════════════════════════════════════════════════════════════════════════════
_section("8. SOFT CONSTRAINTS ON BEST SCHEDULE")

rest_best   = Rest_day_penalty(best_schedule, teams, PENALTY)
derby_best  = Derbies_penalty(best_schedule, derbies, WEEKENDS, PENALTY)
away_best   = sum(successive_away_penalty(t, best_schedule, PENALTY) for t in teams)
dist_best   = total_distance(best_schedule, dist_matrix, teams)

rest_init   = Rest_day_penalty(initial_schedule, teams, PENALTY)
derby_init  = Derbies_penalty(initial_schedule, derbies, WEEKENDS, PENALTY)
away_init   = sum(successive_away_penalty(t, initial_schedule, PENALTY) for t in teams)
dist_init   = total_distance(initial_schedule, dist_matrix, teams)

print(f"\n{'Penalty':<28} {'Initial':>12} {'After SA':>12} {'Change':>12}")
print(f"{'─'*28} {'─'*12} {'─'*12} {'─'*12}")
print(f"{'Travel distance (km)':<28} {dist_init:>12,.1f} {dist_best:>12,.1f} {dist_best-dist_init:>+12,.1f}")
print(f"{'Rest-day penalty':<28} {rest_init:>12,.0f} {rest_best:>12,.0f} {rest_best-rest_init:>+12,.0f}")
print(f"{'Derby penalty':<28} {derby_init:>12,.0f} {derby_best:>12,.0f} {derby_best-derby_init:>+12,.0f}")
print(f"{'Successive away penalty':<28} {away_init:>12,.0f} {away_best:>12,.0f} {away_best-away_init:>+12,.0f}")

# Derby violations detail
print(f"\n── Derby violations after SA ──")
derby_violations_after = 0
for r in best_schedule.rounds:
    for m in r.matches:
        pair = frozenset([m.home.name, m.away.name])
        if pair in derbies and m.day not in WEEKENDS:
            derby_violations_after += 1
            print(f"    ✗ {m.home.name} vs {m.away.name}  on {m.day}")

if derby_violations_after == 0:
    _ok("No derby violations remaining after SA ✓")
else:
    print(f"  {derby_violations_after} derby violation(s) remain")

# Successive away violations detail
print(f"\n── Successive away violations after SA ──")
any_away = False
for team in teams:
    p = successive_away_penalty(team, best_schedule, PENALTY)
    if p:
        print(f"    ✗ {team.name:<22} penalty = {p:,.0f}")
        any_away = True
if not any_away:
    _ok("No successive away violations ✓")


# ══════════════════════════════════════════════════════════════════════════════
# 9.  RANDOMNESS CHECK — two runs give different results
# ══════════════════════════════════════════════════════════════════════════════
_section("9. RANDOMNESS CHECK")

print("\n  Running SA a second time with a different random seed...")

random.seed(99)
_, cost_run2, _ = simulated_annealing(
    schedule      = initial_schedule,
    distances     = dist_matrix,
    derbies       = derbies,
    weekends      = WEEKENDS,
    teams         = teams,
    T_start       = 10000,
    T_min         = 0.1,
    alpha         = 0.995,
    max_iteration = 5000,          # shorter for speed
    cost_fn       = cost_function
)

print(f"  Run 1 best cost (20 000 it) : {best_cost:>12,.1f}")
print(f"  Run 2 best cost (5 000 it)  : {cost_run2:>12,.1f}")

_check(best_cost != cost_run2,
       "Two runs produce different costs — randomness is working",
       "Two runs produce identical costs — random calls may not be reached")

_check(best_cost <= cost_run2,
       "Longer run (20 000) found equal or better result than shorter (5 000)",
       "Shorter run found better result — may be a best-tracking bug")


# ══════════════════════════════════════════════════════════════════════════════
# 10.  FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
_section("10. SUMMARY")

print(f"""
  Initial cost    : {initial_cost:>12,.1f}
  Best cost (SA)  : {best_cost:>12,.1f}
  Improvement     : {initial_cost - best_cost:>+12,.1f}  ({pct:.1f}%)
  SA runtime      : {elapsed:.1f}s
  Rounds          : {best_schedule.total_rounds()}
  Matches         : {best_schedule.total_matches()}
  History entries : {len(history)}
""")

print("  If all checks above show ✓ — your SA is working correctly.")
print("  Any ✗ tells you exactly which component to fix.\n")
