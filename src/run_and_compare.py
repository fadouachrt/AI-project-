"""
run_and_compare.py
==================
Runs Greedy, Hill Climbing, and Simulated Annealing,
then prints a clean side-by-side comparison.

Change parameters in the CONFIG section below.
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from data_loader        import load_all, load_derbies
from schedule           import double_round_robin, assign_all_days
from greedy             import greedy_schedule, compute_total_travel
from Hill_Climbing      import hill_climbing
from simulated_annealing import simulated_annealing
from Minimize_total     import cost_function, total_distance
from Soft_constraints   import Rest_day_penalty, Derbies_penalty, successive_away_penalty

# ═══════════════════════════════════════════════════════════════════
#  CONFIG — edit parameters here
# ═══════════════════════════════════════════════════════════════════

TEAMS_CSV   = "../data/teams.csv"
DERBIES_CSV = "../data/derbies.csv"
WEEKENDS    = {"Friday", "Saturday"}
PENALTY     = 500

GREEDY_PARAMS = {
    "seed": 42,
}

HC_PARAMS = {
    "strategy"      : "stochastic",   # "first_choice" or "stochastic"
    "max_restarts"  : 5,
    "max_iterations": 150,
    "max_tries"     : 80,               # first_choice only
    "n_samples"     : 50,               # stochastic only
    "max_sideways"  : 10,
    "tabu_size"     : 20,
}

SA_PARAMS = {
    "T_start"      : 15000,
    "T_min"        : 0.1,
    "alpha"        : 0.9997,
    "max_iteration": 30000,
    "reheat_every" : 4000,
    "reheat_factor": 2.0,
}

# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════

W = 72   # print width

def line(char="─"):
    print(char * W)

def header(text):
    print()
    print("═" * W)
    print(f"  {text}")
    print("═" * W)

def row(label, *vals, width=18):
    label_str = f"  {label:<26}"
    val_strs  = "".join(f"{str(v):>{width}}" for v in vals)
    print(label_str + val_strs)

def fmt(v):
    if isinstance(v, float):
        return f"{v:,.1f}"
    return str(v)

def get_penalties(schedule):
    rest  = Rest_day_penalty(schedule, teams, PENALTY)
    derby = Derbies_penalty(schedule, derbies, WEEKENDS, PENALTY)
    away  = sum(successive_away_penalty(t, schedule, PENALTY) for t in teams)
    return rest, derby, away

# ═══════════════════════════════════════════════════════════════════
#  LOAD DATA
# ═══════════════════════════════════════════════════════════════════

print(f"\n  Loading data...")
teams, distances = load_all(TEAMS_CSV)
derbies = load_derbies(DERBIES_CSV)
print(f"  {len(teams)} teams  |  {len(derbies)} derby pairs")

initial_schedule = assign_all_days(double_round_robin(teams))
initial_cost     = cost_function(initial_schedule, teams, distances, derbies, WEEKENDS, PENALTY)

# ═══════════════════════════════════════════════════════════════════
#  RUN ALGORITHMS
# ═══════════════════════════════════════════════════════════════════

print("\n  Running algorithms...\n")

# ── Greedy ──────────────────────────────────────────────────────────
print("  [1/3] Greedy...", end=" ", flush=True)
t0 = time.perf_counter()
g_sched, g_travel, g_history = greedy_schedule(teams, distances, **GREEDY_PARAMS)
g_time = time.perf_counter() - t0
g_cost = cost_function(g_sched, teams, distances, derbies, WEEKENDS, PENALTY)
g_rest, g_derby, g_away = get_penalties(g_sched)
print(f"done  ({g_time:.3f}s)")

# ── Hill Climbing ───────────────────────────────────────────────────
print("  [2/3] Hill Climbing...", end=" ", flush=True)
t0 = time.perf_counter()
hc_sched, hc_cost, hc_history = hill_climbing(
    schedule   = initial_schedule,
    distances  = distances,
    derbies    = derbies,
    weekends   = WEEKENDS,
    teams      = teams,
    cost_fn    = cost_function,
    verbose    = False,
    **HC_PARAMS,
)
hc_time = time.perf_counter() - t0
hc_rest, hc_derby, hc_away = get_penalties(hc_sched)
hc_dist = total_distance(hc_sched, distances, teams)
print(f"done  ({hc_time:.3f}s)")

# ── Simulated Annealing ─────────────────────────────────────────────
print("  [3/3] Simulated Annealing...", end=" ", flush=True)
t0 = time.perf_counter()
sa_sched, sa_cost, sa_history = simulated_annealing(
    schedule  = initial_schedule,
    distances = distances,
    derbies   = derbies,
    weekends  = WEEKENDS,
    teams     = teams,
    cost_fn   = cost_function,
    **SA_PARAMS,
)
sa_time = time.perf_counter() - t0
sa_rest, sa_derby, sa_away = get_penalties(sa_sched)
sa_dist = total_distance(sa_sched, distances, teams)
print(f"done  ({sa_time:.3f}s)")

# ═══════════════════════════════════════════════════════════════════
#  PARAMETERS USED
# ═══════════════════════════════════════════════════════════════════

header("PARAMETERS USED")

print(f"\n  {'Greedy'}")
for k, v in GREEDY_PARAMS.items():
    print(f"    {k:<20} = {v}")

print(f"\n  {'Hill Climbing'}")
for k, v in HC_PARAMS.items():
    print(f"    {k:<20} = {v}")

print(f"\n  {'Simulated Annealing'}")
for k, v in SA_PARAMS.items():
    print(f"    {k:<20} = {v}")

print(f"\n  Shared")
print(f"    {'penalty':<20} = {PENALTY}")
print(f"    {'weekends':<20} = {sorted(WEEKENDS)}")

# ═══════════════════════════════════════════════════════════════════
#  SIDE-BY-SIDE RESULTS
# ═══════════════════════════════════════════════════════════════════

header("SIDE-BY-SIDE RESULTS")

COL = 16
print()
print(f"  {'':26}{'Greedy':>{COL}}{'Hill Climbing':>{COL}}{'Simul. Anneal.':>{COL}}")
line()

print(f"\n  — Cost Breakdown —")
row("Total cost",        fmt(g_cost),           fmt(hc_cost),   fmt(sa_cost))
row("Travel distance",   fmt(compute_total_travel(g_sched, distances)),
                                                fmt(hc_dist),   fmt(sa_dist))
row("Rest-day penalty",  fmt(g_rest),           fmt(hc_rest),   fmt(sa_rest))
row("Derby penalty",     fmt(g_derby),          fmt(hc_derby),  fmt(sa_derby))
row("Successive away",   fmt(g_away),           fmt(hc_away),   fmt(sa_away))

line()
print(f"\n  — Violations (at {PENALTY}/each) —")
row("Rest-day",          int(g_rest//PENALTY),  int(hc_rest//PENALTY),  int(sa_rest//PENALTY))
row("Derby",             int(g_derby//PENALTY), int(hc_derby//PENALTY), int(sa_derby//PENALTY))
row("Successive away",   int(g_away//PENALTY),  int(hc_away//PENALTY),  int(sa_away//PENALTY))

line()
print(f"\n  — Performance —")
row("Runtime (s)",       f"{g_time:.3f}",       f"{hc_time:.3f}",       f"{sa_time:.3f}")
row("Iterations / steps",len(g_history),        len(hc_history),        len(sa_history))

if g_history:
    row("Initial cost (greedy)", fmt(g_history[0]), "", "")
if hc_history:
    row("HC start → end",  "", f"{fmt(initial_cost)} → {fmt(hc_cost)}", "")
if sa_history:
    row("SA start → end",  "", "", f"{fmt(sa_history[0])} → {fmt(sa_cost)}")

line()

# ═══════════════════════════════════════════════════════════════════
#  RANKING & VERDICT
# ═══════════════════════════════════════════════════════════════════

header("RANKING")

results = [
    ("Greedy",             g_cost,  g_time),
    ("Hill Climbing",      hc_cost, hc_time),
    ("Simulated Annealing",sa_cost, sa_time),
]
ranked = sorted(results, key=lambda x: x[1])

medals = ["🥇", "🥈", "🥉"]
print()
for i, (name, cost, rt) in enumerate(ranked):
    improvement = 100 * (initial_cost - cost) / initial_cost if initial_cost else 0
    print(f"  {medals[i]}  {name:<22}  cost={fmt(cost)}   "
          f"time={rt:.3f}s   improved {improvement:.1f}% vs initial")

print()
winner = ranked[0][0]
cost_gap_1_2 = ranked[1][1] - ranked[0][1]
cost_gap_1_3 = ranked[2][1] - ranked[0][1]
print(f"  ★  Winner: {winner}")
print(f"     {ranked[0][0]} beats {ranked[1][0]} by {fmt(cost_gap_1_2)} cost units")
print(f"     {ranked[0][0]} beats {ranked[2][0]} by {fmt(cost_gap_1_3)} cost units")

# penalty champion
pen_totals = [
    ("Greedy",             g_rest + g_derby + g_away),
    ("Hill Climbing",      hc_rest + hc_derby + hc_away),
    ("Simulated Annealing",sa_rest + sa_derby + sa_away),
]
pen_ranked = sorted(pen_totals, key=lambda x: x[1])
print(f"\n  Lowest total penalty  → {pen_ranked[0][0]}  ({fmt(pen_ranked[0][1])})")

fastest = min(results, key=lambda x: x[2])
print(f"  Fastest               → {fastest[0]}  ({fastest[2]:.3f}s)")
print()
line("═")
print()
