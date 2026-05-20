"""
sa_statistical_analysis.py
===========================
Statistical evaluation of 4 SA configurations over N_RUNS independent trials.

Produces:
  sa_analysis_raw.csv       — every individual run (for report appendix)
  sa_analysis_summary.csv   — one row per config (paste into report table)
  sa_analysis_report.txt    — formatted text ready to paste into report
  sa_learning_curves.png    — mean convergence + box-plot side by side
"""

import sys, os, time, csv, math, random
from copy      import deepcopy
from datetime  import timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

sys.path.insert(0, os.path.dirname(__file__))

from data_loader          import load_all, load_derbies
from schedule             import double_round_robin, assign_all_days
from simulated_annealing  import simulated_annealing
from Minimize_total       import cost_function,total_distance
from Soft_constraints import Rest_day_penalty,Derbies_penalty,successive_away_penalty

# ═══════════════════════════════════════════════════════════════════
#  CONFIG  — edit here only
# ═══════════════════════════════════════════════════════════════════

TEAMS_CSV   = "../data/teams.csv"
DERBIES_CSV = "../data/derbies.csv"
WEEKENDS    = {"Friday", "Saturday"}
PENALTY     = 500
N_RUNS      = 20       # independent trials per configuration

CONFIGS = {
    "A": {"T_start": 8_000,  "T_min": 0.1, "alpha": 0.9997,
          "max_iteration": 20_000, "reheat_every": 2_000, "reheat_factor": 2.0},
    "B": {"T_start": 8_000,  "T_min": 0.1, "alpha": 0.9994,
          "max_iteration": 20_000, "reheat_every": 2_000, "reheat_factor": 2.0},
    "C": {"T_start": 15_000, "T_min": 0.1, "alpha": 0.9997,
          "max_iteration": 30_000, "reheat_every": 4_000, "reheat_factor": 2.5},
    "D": {"T_start": 8_000,  "T_min": 0.1, "alpha": 0.9997,
          "max_iteration": 30_000, "reheat_every": 4_000, "reheat_factor": 2.0},
}

COLORS = {"A": "steelblue", "B": "orange", "C": "green", "D": "purple"}

OUT_RAW     = "sa_analysis_raw.csv"
OUT_SUMMARY = "sa_analysis_summary.csv"
OUT_REPORT  = "sa_analysis_report.txt"
OUT_PLOT    = "sa_learning_curves.png"

# ═══════════════════════════════════════════════════════════════════
#  STATISTICAL HELPERS
# ═══════════════════════════════════════════════════════════════════

def _mean(data):
    return sum(data) / len(data)

def _std(data):
    if len(data) < 2:
        return 0.0
    m = _mean(data)
    return math.sqrt(sum((x - m) ** 2 for x in data) / (len(data) - 1))

def last_improvement_iter(history):
    best, last = history[0], 0
    for i, c in enumerate(history):
        if c < best:
            best, last = c, i
    return last

def convergence_pct(history):
    initial, final = history[0], history[-1]
    if initial == final:
        return 100.0
    target = initial - 0.90 * (initial - final)
    idx = next((i for i, c in enumerate(history) if c <= target), len(history))
    return 100.0 * idx / len(history)

def still_improving(history):
    cut = int(0.8 * len(history))
    return history[cut] > history[-1]

# ═══════════════════════════════════════════════════════════════════
#  LOAD DATA
# ═══════════════════════════════════════════════════════════════════

print("\n" + "═" * 60)
print("  SA STATISTICAL ANALYSIS")
print("═" * 60)
print("\n  Loading data...")
teams, distances = load_all(TEAMS_CSV)
derbies          = load_derbies(DERBIES_CSV)
print(f"  {len(teams)} teams | {len(derbies)} derby pairs")

# run this in BOTH standalone and notebook
# paste both outputs so we can compare line by line

schedule = assign_all_days(double_round_robin(teams))

# print the first round to see if schedules are structurally different
print("=== FIRST ROUND ===")
for match in schedule.rounds[0].matches:
    print(f"  {match.home.name} vs {match.away.name} | {match.day}")

print(f"\nTotal rounds: {len(schedule.rounds)}")
print(f"Matches per round: {len(schedule.rounds[0].matches)}")

# print each cost component separately
travel = total_distance(schedule, distances, teams)
rest   = Rest_day_penalty(schedule, teams, 500)
derby  = Derbies_penalty(schedule, derbies, WEEKENDS, 500)
away   = sum(successive_away_penalty(t, schedule, 500) for t in teams)

print(f"\n=== COST BREAKDOWN ===")
print(f"Travel : {travel:,.0f}")
print(f"Rest   : {rest:,.0f}")
print(f"Derby  : {derby:,.0f}")
print(f"Away   : {away:,.0f}")
print(f"Total  : {travel+rest+derby+away:,.0f}")

# print which days are being assigned
print(f"\n=== DAY DISTRIBUTION ===")
from collections import Counter
all_days = [m.day for r in schedule.rounds for m in r.matches]
for day, count in sorted(Counter(all_days).items()):
    print(f"  {day}: {count} matches")

# print team order
print(f"\n=== TEAM ORDER ===")
for i, t in enumerate(teams):
    print(f"  {i+1}. {t.name}")
    
initial_schedule = assign_all_days(double_round_robin(teams))
INITIAL_COST     = cost_function(
    initial_schedule, teams, distances, derbies, WEEKENDS, PENALTY)
print(f"  Initial cost : {INITIAL_COST:,.0f}")
print(f"  Configs      : {list(CONFIGS.keys())}")
print(f"  Runs each    : {N_RUNS}")
print(f"  Total runs   : {len(CONFIGS) * N_RUNS}\n")

# ═══════════════════════════════════════════════════════════════════
#  MAIN EXPERIMENT LOOP
# ═══════════════════════════════════════════════════════════════════

raw_rows      = []
all_costs     = {k: [] for k in CONFIGS}
all_times     = {k: [] for k in CONFIGS}
all_histories = {k: [] for k in CONFIGS}
all_last_impr = {k: [] for k in CONFIGS}
all_conv_pcts = {k: [] for k in CONFIGS}
all_still_imp = {k: [] for k in CONFIGS}

global_start = time.perf_counter()
total_runs   = len(CONFIGS) * N_RUNS
run_counter  = 0

for cfg, params in CONFIGS.items():
    print(f"  ── Config {cfg} ──")
    for run in range(1, N_RUNS + 1):
        run_counter += 1
        t0 = time.perf_counter()
        _, best_cost, history = simulated_annealing(
            schedule  = deepcopy(initial_schedule),
            distances = distances,
            derbies   = derbies,
            weekends  = WEEKENDS,
            teams     = teams,
            cost_fn   = cost_function,
            **params,
        )
        elapsed = time.perf_counter() - t0

        impr = 100.0 * (INITIAL_COST - best_cost) / INITIAL_COST
        li   = last_improvement_iter(history)
        cp   = convergence_pct(history)
        si   = still_improving(history)

        all_costs[cfg].append(best_cost)
        all_times[cfg].append(elapsed)
        all_histories[cfg].append(history)
        all_last_impr[cfg].append(li)
        all_conv_pcts[cfg].append(cp)
        all_still_imp[cfg].append(si)

        raw_rows.append({
            "config": cfg, "run": run,
            "best_cost": round(best_cost, 1),
            "improvement_pct": round(impr, 2),
            "runtime_s": round(elapsed, 2),
            "last_impr_iter": li,
            "conv_pct": round(cp, 1),
            "still_improving": int(si),
            **{k: v for k, v in params.items() if k != "T_min"},
        })

        done = time.perf_counter() - global_start
        eta  = timedelta(seconds=int(done / run_counter * (total_runs - run_counter)))
        print(f"    run {run:>2}/{N_RUNS}  cost={best_cost:>10,.0f}  "
              f"improv={impr:>5.1f}%  time={elapsed:>6.1f}s  ETA {eta}")
    print()

# ═══════════════════════════════════════════════════════════════════
#  AGGREGATE STATISTICS
# ═══════════════════════════════════════════════════════════════════

stats = {}
for cfg in CONFIGS:
    costs = all_costs[cfg]
    times = all_times[cfg]
    m, sd = _mean(costs), _std(costs)
    mn, mx = min(costs), max(costs)
    stats[cfg] = {
        "mean"          : m,
        "std_dev"       : sd,
        "min"           : mn,
        "max"           : mx,
        "cv"            : 100.0 * sd / m,
        "impr_pct"      : 100.0 * (INITIAL_COST - m) / INITIAL_COST,
        "avg_time"      : _mean(times),
        "avg_last_impr" : _mean(all_last_impr[cfg]),
        "avg_conv_pct"  : _mean(all_conv_pcts[cfg]),
        "pct_still_imp" : 100.0 * sum(all_still_imp[cfg]) / N_RUNS,
    }

cfg_names = list(CONFIGS.keys())

# ═══════════════════════════════════════════════════════════════════
#  WRITE CSV FILES
# ═══════════════════════════════════════════════════════════════════

raw_fields = ["config", "run", "best_cost", "improvement_pct", "runtime_s",
              "last_impr_iter", "conv_pct", "still_improving",
              "T_start", "alpha", "max_iteration", "reheat_every", "reheat_factor"]
with open(OUT_RAW, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=raw_fields)
    w.writeheader()
    w.writerows(raw_rows)

sum_fields = ["config", "mean", "std_dev", "min", "max", "cv_pct",
              "improvement_pct", "avg_time_s",
              "avg_last_impr_iter", "avg_conv_pct", "pct_still_improving"]
with open(OUT_SUMMARY, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=sum_fields)
    w.writeheader()
    for cfg, s in stats.items():
        w.writerow({
            "config"              : cfg,
            "mean"                : round(s["mean"], 1),
            "std_dev"             : round(s["std_dev"], 1),
            "min"                 : round(s["min"], 1),
            "max"                 : round(s["max"], 1),
            "cv_pct"              : round(s["cv"], 2),
            "improvement_pct"     : round(s["impr_pct"], 2),
            "avg_time_s"          : round(s["avg_time"], 2),
            "avg_last_impr_iter"  : round(s["avg_last_impr"]),
            "avg_conv_pct"        : round(s["avg_conv_pct"], 1),
            "pct_still_improving" : round(s["pct_still_imp"], 1),
        })

# ═══════════════════════════════════════════════════════════════════
#  TEXT REPORT
# ═══════════════════════════════════════════════════════════════════

W  = 78
HL = "═" * W
SL = "─" * W
lines = []
def p(s=""): lines.append(s)

p(HL)
p("  SIMULATED ANNEALING — STATISTICAL PERFORMANCE ANALYSIS")
p(f"  {N_RUNS} independent runs per configuration | Initial cost: {INITIAL_COST:,.0f}")
p(HL)

# Table 1
p()
p("  TABLE 1 — AGGREGATE STATISTICS")
p(SL)
p(f"  {'Config':<8} {'Mean':>10} {'Std Dev':>10} {'Min':>10} {'Max':>10}"
  f" {'CV%':>6} {'Improv%':>8} {'Time(s)':>9}")
p(SL)
for cfg in cfg_names:
    s = stats[cfg]
    p(f"  {cfg:<8} {s['mean']:>10,.0f} {s['std_dev']:>10,.0f} "
      f"{s['min']:>10,.0f} {s['max']:>10,.0f} "
      f"{s['cv']:>5.1f}% {s['impr_pct']:>7.1f}% {s['avg_time']:>9.2f}")
p()
p("  CV% = Coefficient of Variation = StdDev / Mean × 100.")
p("  Lower CV% = more consistent across random seeds.")

# Table 2
p()
p("  TABLE 2 — CONVERGENCE BEHAVIOUR (averages over all runs)")
p(SL)
p(f"  {'Config':<8} {'Avg last impr iter':>20} {'90% gain at iter%':>19}"
  f" {'Still impr last 20% (%)':>24}")
p(SL)
for cfg in cfg_names:
    s = stats[cfg]
    p(f"  {cfg:<8} {s['avg_last_impr']:>20,.0f} {s['avg_conv_pct']:>18.0f}%"
      f" {s['pct_still_imp']:>23.0f}%")
p()
p("  'Avg last impr iter' = average iteration of the final improvement.")
p("  '90% gain at iter%'  = how far through the run before 90% of gain is locked in.")
p("  'Still impr last 20%'= % of runs still finding improvements in the last 20%.")

# Recommendation
ranked_cfgs = sorted(cfg_names, key=lambda c: stats[c]["mean"])
best        = ranked_cfgs[0]
most_stable = min(cfg_names, key=lambda c: stats[c]["cv"])
p()
p("  RECOMMENDATION")
p(SL)
p(f"  Best mean cost   → Config {best}  "
  f"(mean={stats[best]['mean']:,.0f}, CV={stats[best]['cv']:.1f}%)")
p(f"  Most consistent  → Config {most_stable}  "
  f"(CV={stats[most_stable]['cv']:.1f}%)")
p(f"  Best single run  → {min(stats[c]['min'] for c in cfg_names):,.0f}")
p()
p("  Recommended parameters:")
for k, v in CONFIGS[best].items():
    if k != "T_min":
        p(f"    {k:<20} = {v}")
p()
p(HL)

report_text = "\n".join(lines)
print("\n" + report_text + "\n")
with open(OUT_REPORT, "w", encoding="utf-8") as f:
    f.write(report_text + "\n")

# ═══════════════════════════════════════════════════════════════════
#  PLOT — left: mean learning curves (x = actual iterations)
#         right: box-plot of final cost distributions
# ═══════════════════════════════════════════════════════════════════

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle(
    f"SA Configuration Comparison — {N_RUNS} independent runs each   "
    f"|   Initial cost = {INITIAL_COST:,.0f}",
    fontsize=12, fontweight="bold"
)

# ── Left: mean + best convergence per config, x = actual iteration ─
for cfg, histories in all_histories.items():
    color   = COLORS[cfg]
    min_len = min(len(h) for h in histories)

    mean_curve = [_mean([h[i] for h in histories]) for i in range(min_len)]
    best_curve = [min(h[i]   for h in histories)   for i in range(min_len)]

    step   = max(1, min_len // 600)
    iters  = list(range(0, min_len, step))
    mean_d = mean_curve[::step]
    best_d = best_curve[::step]

    ax1.plot(iters, mean_d, color=color, linewidth=2.0,
             label=f"Config {cfg} (mean)")
    ax1.plot(iters, best_d, color=color, linewidth=0.8,
             linestyle="--", alpha=0.5)

ax1.axhline(y=INITIAL_COST, color="red", linestyle=":", linewidth=1.2,
            label=f"Initial cost")

# stagnation reference lines matching your report text
for xmark, lbl in [(17_000, "~17k\n(A,B plateau)"),
                   (27_500, "~27.5k\n(C,D plateau)")]:
    ax1.axvline(x=xmark, color="gray", linestyle="--", linewidth=1.0, alpha=0.65)
    ypos = ax1.get_ylim()[0] if ax1.get_ylim()[0] > 100_000 else INITIAL_COST * 0.54
    ax1.text(xmark + 300, INITIAL_COST * 0.535, lbl,
             fontsize=7.5, color="dimgray", va="bottom")

ax1.set_xlabel("Iteration", fontsize=11)
ax1.set_ylabel("Best cost (lower = better)", fontsize=11)
ax1.set_title("Mean convergence curves\n"
              "solid = mean across runs  |  dashed = best run", fontsize=10)
ax1.legend(fontsize=8, ncol=2)
ax1.grid(True, alpha=0.25)
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

# ── Right: box-plot + jittered individual run points ───────────────
positions = list(range(len(cfg_names)))
bp_data   = [all_costs[c] for c in cfg_names]

bp = ax2.boxplot(bp_data, positions=positions, widths=0.45,
                 patch_artist=True,
                 medianprops=dict(color="black", linewidth=2.2),
                 whiskerprops=dict(linewidth=1.2),
                 capprops=dict(linewidth=1.2),
                 flierprops=dict(marker="x", markersize=5, markeredgecolor="gray"))

for patch, cfg in zip(bp["boxes"], cfg_names):
    patch.set_facecolor(COLORS[cfg])
    patch.set_alpha(0.65)

for i, cfg in enumerate(cfg_names):
    xs = [i + random.uniform(-0.13, 0.13) for _ in all_costs[cfg]]
    ax2.scatter(xs, all_costs[cfg], s=22, color=COLORS[cfg], zorder=4, alpha=0.85)

ax2.set_xticks(positions)
ax2.set_xticklabels(
    [f"Config {c}\nCV={stats[c]['cv']:.1f}%" for c in cfg_names],
    fontsize=9
)
ax2.set_ylabel("Final cost (lower = better)", fontsize=11)
ax2.set_title(f"Cost distribution across {N_RUNS} runs\n"
              "Dots = individual runs  |  Line = median", fontsize=10)
ax2.grid(True, alpha=0.25, axis="y")
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

patches = [mpatches.Patch(facecolor=COLORS[c], alpha=0.7, label=f"Config {c}")
           for c in cfg_names]
ax2.legend(handles=patches, fontsize=9, loc="upper right")

plt.tight_layout()
plt.savefig(OUT_PLOT, dpi=150, bbox_inches="tight")
print(f"  Plot saved → {OUT_PLOT}")

# ═══════════════════════════════════════════════════════════════════
#  DONE
# ═══════════════════════════════════════════════════════════════════

total_elapsed = time.perf_counter() - global_start
print(f"\n  {OUT_RAW}")
print(f"  {OUT_SUMMARY}")
print(f"  {OUT_REPORT}")
print(f"  {OUT_PLOT}")
print(f"\n  Total runtime: {timedelta(seconds=int(total_elapsed))}\n")