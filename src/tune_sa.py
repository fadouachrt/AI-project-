"""
tune_sa.py
==========
Grid-search over SA parameters and rank every combination by best_cost.

HOW TO RUN
----------
From inside your src/ folder:
    python tune_sa.py

Or from the project root:
    python src/tune_sa.py

WHAT IT DOES
------------
1. Loads real data (teams + derbies).
2. Builds a fresh initial schedule for every single trial
   (so each combination starts from the same position).
3. Runs SA once per combination (runs = 1 by default — fast mode).
   Set RUNS_PER_COMBO = 3 for a statistically stable result
   (takes ~3× longer but the ranking will be reliable).
4. Prints a live table as it goes so you see progress immediately.
5. At the end prints a full ranked summary and saves results to
   sa_tuning_results.csv next to this file.

EDIT THE GRID
-------------
Change the lists inside GRID below. Every combination of every
value is tested (cartesian product). If you want to test only
a few specific configs, set MANUAL_CONFIGS instead (see bottom
of GRID section).

ESTIMATED RUNTIME
-----------------
  Each SA run at max_iteration=30 000 takes ~45–75 seconds.
  Total = combinations × RUNS_PER_COMBO × ~60s.
  With the default grid (54 combinations, 1 run each) ≈ 54 min.
  With RUNS_PER_COMBO=3 ≈ 2.7 hours.
  Reduce the grid or lower max_iteration to speed up.
"""

import sys
import os
import csv
import time
import itertools
import math
import statistics

sys.path.insert(0, os.path.dirname(__file__))

from data_loader         import load_all, load_derbies
from schedule            import double_round_robin, assign_all_days
from simulated_annealing import simulated_annealing
from Minimize_total      import cost_function, total_distance
from Soft_constraints    import (Rest_day_penalty, Derbies_penalty,
                                  successive_away_penalty)

# ═══════════════════════════════════════════════════════════════════
#  PATHS  (relative to this file — adjust if needed)
# ═══════════════════════════════════════════════════════════════════

TEAMS_CSV   = "../data/teams.csv"
DERBIES_CSV = "../data/derbies.csv"
WEEKENDS    = {"Friday", "Saturday"}
PENALTY     = 500
OUTPUT_CSV  = os.path.join(os.path.dirname(__file__), "sa_tuning_results.csv")

# ═══════════════════════════════════════════════════════════════════
#  TUNING SETTINGS
# ═══════════════════════════════════════════════════════════════════

# How many times to run SA per parameter combination.
# 1 = fast but noisy.   3 = slow but reliable ranking.
RUNS_PER_COMBO = 1

# ═══════════════════════════════════════════════════════════════════
#  PARAMETER GRID
#  Every list entry below is one value to try for that parameter.
#  All combinations are tested (cartesian product).
#  Total combinations = product of all list lengths.
# ═══════════════════════════════════════════════════════════════════

GRID = {
    # ── Temperature ───────────────────────────────────────────
    # How hot SA starts. Higher = more random-walk early.
    # Below ~8000 SA is too cold at the start; above ~20000 wastes
    # the first few thousand iterations on a pure random walk.
    "T_start": [8_000, 10_000, 15_000],

    # ── Cooling rate ──────────────────────────────────────────
    # How fast T drops each iteration.
    # Lower alpha = faster cooling = fewer real iterations.
    # Formula: freezes at iteration ln(T_min/T_start) / ln(alpha)
    #   alpha=0.9994, T_start=10000, T_min=0.1 → freezes at ~24 000
    #   alpha=0.9996, T_start=10000, T_min=0.1 → freezes at ~36 000
    #   alpha=0.9997, T_start=10000, T_min=0.1 → freezes at ~45 000
    #   alpha=0.9998, T_start=10000, T_min=0.1 → freezes at ~68 000
    # Choose so freeze point ≈ 80–90% of max_iteration.
    "alpha": [0.9994, 0.9996, 0.9997],

    # ── Iteration budget ──────────────────────────────────────
    # Total moves SA is allowed to make.
    # Increase only if you have time; each extra 10k ≈ +15 seconds.
    "max_iteration": [20_000, 30_000],

    # ── Reheating: window ─────────────────────────────────────
    # How many iterations without a best-improvement before SA
    # raises T again. Smaller = more aggressive reheating.
    "reheat_every": [2_000, 3_000, 4_000],

    # ── Reheating: strength ───────────────────────────────────
    # Multiply T by this when reheating fires.
    # 2.0 = double the current temperature.
    # 2.5 = stronger kick, helps escape deeper local optima.
    "reheat_factor": [2.0, 2.5],

    # ── T_min (leave this alone unless you have a reason) ─────
    # SA stops when T drops below T_min.
    # 0.1 is almost always the right value — lowering it just adds
    # near-frozen iterations that accept nothing useful.
    "T_min": [0.1],
}

# ───────────────────────────────────────────────────────────────────
# MANUAL CONFIGS (optional override)
# ───────────────────────────────────────────────────────────────────
# If you only want to test specific hand-picked configurations instead
# of the full grid, put them here and set USE_MANUAL = True.
# Each entry is a dict with all 6 keys.
USE_MANUAL = False

MANUAL_CONFIGS = [
    {"T_start": 10_000, "alpha": 0.9994, "max_iteration": 20_000,
     "reheat_every": 2_000, "reheat_factor": 2.0, "T_min": 0.1},

    {"T_start": 10_000, "alpha": 0.99975, "max_iteration": 50_000,
     "reheat_every": 3_000, "reheat_factor": 2.5, "T_min": 0.1},

    {"T_start": 15_000, "alpha": 0.9997, "max_iteration": 30_000,
     "reheat_every": 4_000, "reheat_factor": 2.0, "T_min": 0.1},
]


# ═══════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════

def freeze_iteration(T_start, T_min, alpha):
    """Iteration at which T drops to T_min with geometric cooling."""
    if alpha >= 1.0:
        return float("inf")
    return math.log(T_min / T_start) / math.log(alpha)


def get_violations(schedule):
    rest  = Rest_day_penalty(schedule, teams, PENALTY) // PENALTY
    derby = Derbies_penalty(schedule, derbies, WEEKENDS, PENALTY) // PENALTY
    away  = sum(
        successive_away_penalty(t, schedule, PENALTY) // PENALTY
        for t in teams
    )
    return int(rest), int(derby), int(away)


def separator(char="─", width=90):
    print(char * width)


def print_live_row(rank, combo_id, params, best_cost, runtime, rest_v, derby_v, away_v):
    """Print one result line immediately after a combo finishes."""
    freeze = freeze_iteration(params["T_start"], params["T_min"], params["alpha"])
    utilisation = min(freeze / params["max_iteration"] * 100, 100)
    print(
        f"  #{rank:<3} combo={combo_id:<4} "
        f"cost={best_cost:>10,.1f}  "
        f"t={runtime:>6.1f}s  "
        f"rest={rest_v:>3} derby={derby_v:>2} away={away_v:>2}  "
        f"α={params['alpha']}  T0={params['T_start']:>6}  "
        f"iters={params['max_iteration']:>6}  "
        f"reh=({params['reheat_every']},{params['reheat_factor']})  "
        f"util={utilisation:.0f}%"
    )


# ═══════════════════════════════════════════════════════════════════
#  LOAD DATA
# ═══════════════════════════════════════════════════════════════════

print("\n" + "═" * 90)
print("  SA PARAMETER TUNING")
print("═" * 90)
print(f"\n  Loading data from {TEAMS_CSV} ...")

teams, distances = load_all(TEAMS_CSV)
derbies          = load_derbies(DERBIES_CSV)

print(f"  {len(teams)} teams | {len(derbies)} derby pairs")

# Build one reference schedule to measure initial cost
_ref = assign_all_days(double_round_robin(teams))
initial_cost = cost_function(_ref, teams, distances, derbies, WEEKENDS, PENALTY)
print(f"  Initial schedule cost: {initial_cost:,.1f}")

# ═══════════════════════════════════════════════════════════════════
#  BUILD COMBO LIST
# ═══════════════════════════════════════════════════════════════════

if USE_MANUAL:
    combos = MANUAL_CONFIGS
    print(f"\n  Mode: MANUAL ({len(combos)} hand-picked configurations)")
else:
    keys   = list(GRID.keys())
    values = list(GRID.values())
    combos = [dict(zip(keys, v)) for v in itertools.product(*values)]
    print(f"\n  Mode: GRID SEARCH")
    print(f"  Grid shape: " +
          " × ".join(f"{k}({len(v)})" for k, v in GRID.items()))
    print(f"  Total combinations: {len(combos)}")

total_runs = len(combos) * RUNS_PER_COMBO
freeze_ok  = [
    c for c in combos
    if freeze_iteration(c["T_start"], c["T_min"], c["alpha"]) <= c["max_iteration"]
]
freeze_warn = len(combos) - len(freeze_ok)

print(f"  Runs per combo: {RUNS_PER_COMBO}   →   Total SA runs: {total_runs}")
if freeze_warn:
    print(f"  ⚠  {freeze_warn} combo(s) freeze before max_iteration "
          f"(wasted iterations at end)")
est_secs = total_runs * 60  # rough estimate: 60s per run
print(f"  Estimated runtime: ~{est_secs // 60} min  "
      f"(based on ~60s per run — adjust if your machine is faster)")

# ═══════════════════════════════════════════════════════════════════
#  COLUMN WIDTHS NOTE
# ═══════════════════════════════════════════════════════════════════

print(f"""
  Columns:
    cost   — best total cost found (lower = better)
    t      — wall-clock seconds for this run
    rest   — rest-day violations remaining
    derby  — derby violations remaining
    away   — successive-away violations remaining
    α      — cooling rate
    T0     — starting temperature
    iters  — max_iteration
    reh    — (reheat_every, reheat_factor)
    util   — how much of the iteration budget was "warm" (< 100% means
             SA froze before max_iteration was reached — wasted budget)
""")

separator("═")
print(f"  LIVE RESULTS (printed as each combo finishes)")
separator()

# ═══════════════════════════════════════════════════════════════════
#  RUN ALL COMBINATIONS
# ═══════════════════════════════════════════════════════════════════

all_results = []   # list of dicts, one per combo (averaged over RUNS_PER_COMBO)

total_wall_start = time.perf_counter()

for combo_idx, params in enumerate(combos, start=1):

    run_costs    = []
    run_times    = []
    run_rest     = []
    run_derby    = []
    run_away     = []
    best_sched_overall = None
    best_cost_overall  = float("inf")

    for run in range(RUNS_PER_COMBO):

        # Fresh schedule for every single run
        fresh_schedule = assign_all_days(double_round_robin(teams))

        t0 = time.perf_counter()
        sched, cost, history = simulated_annealing(
            schedule      = fresh_schedule,
            distances     = distances,
            derbies       = derbies,
            weekends      = WEEKENDS,
            teams         = teams,
            cost_fn       = cost_function,
            T_start       = params["T_start"],
            T_min         = params["T_min"],
            alpha         = params["alpha"],
            max_iteration = params["max_iteration"],
            reheat_every  = params["reheat_every"],
            reheat_factor = params["reheat_factor"],
        )
        elapsed = time.perf_counter() - t0

        rest_v, derby_v, away_v = get_violations(sched)

        run_costs.append(cost)
        run_times.append(elapsed)
        run_rest.append(rest_v)
        run_derby.append(derby_v)
        run_away.append(away_v)

        if cost < best_cost_overall:
            best_cost_overall  = cost
            best_sched_overall = sched

    # Aggregate across runs
    avg_cost  = statistics.mean(run_costs)
    avg_time  = statistics.mean(run_times)
    avg_rest  = statistics.mean(run_rest)
    avg_derby = statistics.mean(run_derby)
    avg_away  = statistics.mean(run_away)
    min_cost  = min(run_costs)
    std_cost  = statistics.stdev(run_costs) if RUNS_PER_COMBO > 1 else 0.0

    freeze = freeze_iteration(params["T_start"], params["T_min"], params["alpha"])
    utilisation = min(freeze / params["max_iteration"] * 100, 100)

    result = {
        "combo_id"     : combo_idx,
        "T_start"      : params["T_start"],
        "alpha"        : params["alpha"],
        "max_iteration": params["max_iteration"],
        "reheat_every" : params["reheat_every"],
        "reheat_factor": params["reheat_factor"],
        "T_min"        : params["T_min"],
        "avg_cost"     : avg_cost,
        "min_cost"     : min_cost,
        "std_cost"     : std_cost,
        "avg_time_s"   : avg_time,
        "avg_rest_v"   : avg_rest,
        "avg_derby_v"  : avg_derby,
        "avg_away_v"   : avg_away,
        "freeze_iter"  : freeze,
        "utilisation_pct": utilisation,
        "improvement_pct": (initial_cost - avg_cost) / initial_cost * 100,
    }
    all_results.append(result)

    # Print live — sorted so far (don't re-sort the whole list each time,
    # just show where this combo ranks among results seen so far)
    current_rank = sorted(all_results, key=lambda r: r["avg_cost"])
    rank_now = next(i + 1 for i, r in enumerate(current_rank)
                    if r["combo_id"] == combo_idx)

    print_live_row(
        rank_now, combo_idx, params,
        avg_cost, avg_time,
        round(avg_rest), round(avg_derby), round(avg_away)
    )

total_wall = time.perf_counter() - total_wall_start

# ═══════════════════════════════════════════════════════════════════
#  FINAL RANKED TABLE
# ═══════════════════════════════════════════════════════════════════

ranked = sorted(all_results, key=lambda r: r["avg_cost"])

separator("═")
print(f"\n  FINAL RANKINGS  (sorted by avg cost over {RUNS_PER_COMBO} run(s) each)")
separator()

print(f"  {'Rank':<5} {'combo':>6} {'avg_cost':>11} {'min_cost':>11} "
      f"{'std':>8} {'improv%':>8} {'rest':>5} {'derby':>6} {'away':>5} "
      f"{'α':>8} {'T0':>7} {'iters':>7} {'reh_e':>6} {'reh_f':>6} "
      f"{'util%':>6} {'time':>7}")
separator()

for rank, r in enumerate(ranked, start=1):
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "   ")
    print(
        f"  {medal} {rank:<3} "
        f"{r['combo_id']:>6} "
        f"{r['avg_cost']:>11,.1f} "
        f"{r['min_cost']:>11,.1f} "
        f"{r['std_cost']:>8,.1f} "
        f"{r['improvement_pct']:>7.1f}% "
        f"{r['avg_rest_v']:>5.1f} "
        f"{r['avg_derby_v']:>6.1f} "
        f"{r['avg_away_v']:>5.1f} "
        f"{r['alpha']:>8} "
        f"{r['T_start']:>7} "
        f"{r['max_iteration']:>7} "
        f"{r['reheat_every']:>6} "
        f"{r['reheat_factor']:>6} "
        f"{r['utilisation_pct']:>6.0f}% "
        f"{r['avg_time_s']:>6.1f}s"
    )

separator()

# ═══════════════════════════════════════════════════════════════════
#  ANALYSIS: WHICH PARAMETER MATTERS MOST?
# ═══════════════════════════════════════════════════════════════════

print(f"\n{'═' * 90}")
print("  PARAMETER IMPACT ANALYSIS")
print(f"{'═' * 90}")
print("  Average cost for each value of each parameter:\n")

param_keys = ["T_start", "alpha", "max_iteration", "reheat_every", "reheat_factor"]

for key in param_keys:
    values_seen = sorted(set(r[key] for r in all_results))
    print(f"  {key}:")
    rows_by_val = []
    for val in values_seen:
        subset = [r["avg_cost"] for r in all_results if r[key] == val]
        avg    = statistics.mean(subset)
        best   = min(subset)
        rows_by_val.append((val, avg, best, len(subset)))

    # Sort by avg cost (best first)
    rows_by_val.sort(key=lambda x: x[1])
    for val, avg, best, n in rows_by_val:
        bar_len = max(0, int((initial_cost - avg) / initial_cost * 40))
        bar     = "█" * bar_len
        print(f"    {str(val):>10}  avg={avg:>10,.1f}  best={best:>10,.1f}  "
              f"n={n:>3}  {bar}")
    print()

# ═══════════════════════════════════════════════════════════════════
#  TOP 3 RECOMMENDED CONFIGS
# ═══════════════════════════════════════════════════════════════════

print(f"{'═' * 90}")
print("  TOP 3 RECOMMENDED CONFIGURATIONS")
print(f"{'═' * 90}\n")

for rank, r in enumerate(ranked[:3], start=1):
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}[rank]
    print(f"  {medal}  Rank {rank}  —  avg cost = {r['avg_cost']:,.1f}  "
          f"({r['improvement_pct']:.1f}% improvement)")
    print(f"     SA_PARAMS = {{")
    print(f"         'T_start'      : {r['T_start']},")
    print(f"         'T_min'        : {r['T_min']},")
    print(f"         'alpha'        : {r['alpha']},")
    print(f"         'max_iteration': {r['max_iteration']},")
    print(f"         'reheat_every' : {r['reheat_every']},")
    print(f"         'reheat_factor': {r['reheat_factor']},")
    print(f"     }}")
    if r["utilisation_pct"] < 85:
        freeze = int(r["freeze_iter"])
        wasted = r["max_iteration"] - freeze
        print(f"     ⚠  SA freezes at iteration ~{freeze:,}, "
              f"wasting ~{wasted:,} cold iterations.")
        print(f"        Consider raising alpha or lowering max_iteration.")
    print()

# ═══════════════════════════════════════════════════════════════════
#  SAVE CSV
# ═══════════════════════════════════════════════════════════════════

fieldnames = [
    "rank", "combo_id", "T_start", "alpha", "max_iteration",
    "reheat_every", "reheat_factor", "T_min",
    "avg_cost", "min_cost", "std_cost", "improvement_pct",
    "avg_rest_v", "avg_derby_v", "avg_away_v",
    "freeze_iter", "utilisation_pct", "avg_time_s",
]

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for rank, r in enumerate(ranked, start=1):
        writer.writerow({"rank": rank, **{k: r[k] for k in fieldnames[1:]}})

print(f"\n  Results saved to: {OUTPUT_CSV}")
print(f"  Total wall-clock time: {total_wall/60:.1f} min\n")
print(f"{'═' * 90}\n")
