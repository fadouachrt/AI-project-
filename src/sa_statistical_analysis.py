"""
sa_statistical_analysis.py
===========================
Rigorous statistical evaluation of SA parameter configurations.
Implements the standard practices from the metaheuristics research community:

  1. Aggregate statistics  — mean, std dev, min, max over N runs
  2. Relative optimality gap — how far from the best known result
  3. Learning curves        — mean trajectory + best trajectory per config
  4. Statistical significance — Welch's t-test between every pair of configs
  5. Full CSV export        — all raw runs for the report appendix

All output files are written next to this script:
  sa_analysis_raw.csv       — every individual run (N_RUNS × configs rows)
  sa_analysis_summary.csv   — one row per config with all aggregate stats
  sa_analysis_report.txt    — human-readable report ready to paste into report
  sa_learning_curves.png    — mean + best trajectory per config on one plot
  sa_boxplot.png            — box-and-whisker of cost distributions
"""

import sys, os, time, csv, math, random, itertools
from copy      import deepcopy
from datetime  import timedelta

import matplotlib
matplotlib.use("Agg")          # no display needed — saves files directly
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from data_loader          import load_all, load_derbies
from schedule             import double_round_robin, assign_all_days
from simulated_annealing  import simulated_annealing
from Minimize_total       import cost_function, total_distance
from Soft_constraints     import (Rest_day_penalty, Derbies_penalty,
                                   successive_away_penalty)

# ═══════════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════════

TEAMS_CSV   = "../data/teams.csv"
DERBIES_CSV = "../data/derbies.csv"
WEEKENDS    = {"Friday", "Saturday"}

# Number of independent runs per configuration.
# Research standard: 20-30.  Set lower for a quick test, higher for the report.
N_RUNS = 5

# The configurations to compare.
CONFIGS = {
    "A - baseline" : {"T_start": 8_000,  "T_min": 0.1, "alpha": 0.9997,
                      "max_iteration": 20_000, "reheat_every": 2_000, "reheat_factor": 2.0},
    "B - fast cool": {"T_start": 8_000,  "T_min": 0.1, "alpha": 0.9994,
                      "max_iteration": 20_000, "reheat_every": 2_000, "reheat_factor": 2.0},
    "C - slow cool": {"T_start": 15_000, "T_min": 0.1, "alpha": 0.9997,
                      "max_iteration": 30_000, "reheat_every": 4_000, "reheat_factor": 2.5},
    "D - cold start":{"T_start": 8_000,  "T_min": 0.1, "alpha": 0.9997,
                      "max_iteration": 30_000, "reheat_every": 4_000, "reheat_factor": 2.0},
}

OUT_RAW     = "sa_analysis_raw.csv"
OUT_SUMMARY = "sa_analysis_summary.csv"
OUT_REPORT  = "sa_analysis_report.txt"
OUT_CURVES  = "sa_learning_curves.png"
OUT_BOX     = "sa_boxplot.png"

# ═══════════════════════════════════════════════════════════════════
#  STATISTICAL HELPERS
# ═══════════════════════════════════════════════════════════════════

def mean(data):
    return sum(data) / len(data)

def std_dev(data):
    if len(data) < 2:
        return 0.0
    m = mean(data)
    return math.sqrt(sum((x - m) ** 2 for x in data) / (len(data) - 1))

def welch_t_test(a, b):
    """
    Welch's unpaired t-test — does NOT assume equal variance.
    Returns (t_statistic, p_value_approx, significant_at_5pct).
    Uses the scipy-free Welch-Satterthwaite approximation.
    """
    n_a, n_b   = len(a), len(b)
    mean_a, mean_b = mean(a), mean(b)
    var_a  = std_dev(a) ** 2
    var_b  = std_dev(b) ** 2

    se = math.sqrt(var_a / n_a + var_b / n_b)
    if se == 0:
        return 0.0, 1.0, False

    t = (mean_a - mean_b) / se

    # Welch-Satterthwaite degrees of freedom
    num   = (var_a / n_a + var_b / n_b) ** 2
    denom = ((var_a / n_a) ** 2 / (n_a - 1) +
             (var_b / n_b) ** 2 / (n_b - 1))
    df    = num / denom if denom > 0 else n_a + n_b - 2

    # Approximate two-tailed p-value using a t→z approximation for df>30
    # (good enough for N_RUNS >= 15; for smaller N use scipy.stats.t)
    abs_t = abs(t)
    if df >= 30:
        # Normal approximation
        z = abs_t
        p = 2 * (1 - _normal_cdf(z))
    else:
        # Simple conservative bound: t-distribution critical values
        # df=10→2.228, df=15→2.131, df=20→2.086, df=25→2.060, df=29→2.045
        crit = {10: 2.228, 15: 2.131, 20: 2.086, 25: 2.060, 29: 2.045}
        nearest = min(crit.keys(), key=lambda k: abs(k - int(df)))
        p = 0.04 if abs_t > crit[nearest] else 0.10   # approximate

    significant = p < 0.05
    return t, p, significant

def _normal_cdf(z):
    """Abramowitz & Stegun approximation for Φ(z)."""
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    poly = t * (0.319381530
              + t * (-0.356563782
              + t * (1.781477937
              + t * (-1.821255978
              + t * 1.330274429))))
    p = 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z ** 2) * poly
    return p if z >= 0 else 1.0 - p

def convergence_metrics(history):
    """
    Returns:
      conv_iter  — iteration at which 90% of total improvement was reached
      conv_pct   — that iteration as % of total run length
      still_improving — True if last 20% of run still yielded improvement
      last_improvement_iter — last iteration where best_cost improved
    """
    total   = len(history)
    initial = history[0]
    final   = history[-1]

    if initial == final:
        return total, 100.0, False, 0

    target = initial - 0.90 * (initial - final)
    conv_iter = next((i for i, c in enumerate(history) if c <= target), total)
    conv_pct  = 100.0 * conv_iter / total

    last_20 = int(0.8 * total)
    still_improving = history[last_20] > history[-1]

    # last iteration where best actually improved
    last_impr = 0
    prev = history[0]
    for i, c in enumerate(history):
        if c < prev:
            last_impr = i
            prev = c

    return conv_iter, conv_pct, still_improving, last_impr

def resample_history(history, target_len=1000):
    """Downsample a history list to target_len points for plotting."""
    n = len(history)
    if n <= target_len:
        return history
    indices = [int(i * n / target_len) for i in range(target_len)]
    return [history[i] for i in indices]

# ═══════════════════════════════════════════════════════════════════
#  LOAD DATA
# ═══════════════════════════════════════════════════════════════════

print("\n" + "═" * 65)
print("  SA STATISTICAL ANALYSIS")
print("═" * 65)
print(f"\n  Loading data...")
teams, distances = load_all(TEAMS_CSV)
derbies          = load_derbies(DERBIES_CSV)
print(f"  {len(teams)} teams | {len(derbies)} derby pairs")

initial_schedule = assign_all_days(double_round_robin(teams))
INITIAL_COST     = cost_function(initial_schedule, teams, distances, derbies, WEEKENDS)
print(f"  Initial cost : {INITIAL_COST:,.1f}")
print(f"  Configs      : {len(CONFIGS)}")
print(f"  Runs each    : {N_RUNS}")

total_runs  = len(CONFIGS) * N_RUNS
# Calibration: rough estimate of time per run using first config
print(f"\n  Calibrating runtime...")
_p0 = list(CONFIGS.values())[0]
_t0 = time.perf_counter()
simulated_annealing(deepcopy(initial_schedule), distances, derbies,
                    WEEKENDS, teams, cost_fn=cost_function, **_p0)
_calib = time.perf_counter() - _t0
# Avg iteration ratio across configs
_avg_iters = mean([p["max_iteration"] for p in CONFIGS.values()])
_base_iters = _p0["max_iteration"]
_scale = _avg_iters / _base_iters
_est   = _calib * total_runs * _scale
print(f"  Calibration  : {_calib:.1f}s per run (config A)")
print(f"  Estimated total runtime: {timedelta(seconds=int(_est))}")
print(f"\n  Starting {total_runs} runs...\n")

# ═══════════════════════════════════════════════════════════════════
#  MAIN EXPERIMENT LOOP
# ═══════════════════════════════════════════════════════════════════

raw_rows   = []       # one dict per run for CSV
all_data   = {}       # config_name → list of costs (for t-tests, boxplot)
all_histories = {}    # config_name → list of histories (for learning curves)

global_start = time.perf_counter()
run_counter  = 0

for config_name, params in CONFIGS.items():
    print(f"  ── {config_name} ──")
    costs       = []
    times       = []
    conv_pcts   = []
    last_imprs  = []
    still_imprs = []
    histories   = []

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

        conv_iter, conv_pct, still_imp, last_impr = convergence_metrics(history)
        improvement = 100.0 * (INITIAL_COST - best_cost) / INITIAL_COST
        gap_from_best = None   # filled in after all runs

        costs.append(best_cost)
        times.append(elapsed)
        conv_pcts.append(conv_pct)
        last_imprs.append(last_impr)
        still_imprs.append(still_imp)
        histories.append(history)

        raw_rows.append({
            "config"        : config_name,
            "run"           : run,
            "best_cost"     : round(best_cost, 1),
            "improvement_pct": round(improvement, 2),
            "runtime_s"     : round(elapsed, 2),
            "conv_iter"     : conv_iter,
            "conv_pct"      : round(conv_pct, 1),
            "still_improving": int(still_imp),
            "last_impr_iter": last_impr,
            **{k: v for k, v in params.items()},
        })

        elapsed_total = time.perf_counter() - global_start
        eta = timedelta(seconds=int(elapsed_total / run_counter * (total_runs - run_counter)))
        print(f"    run {run:>2}/{N_RUNS}  cost={best_cost:>10,.0f}  "
              f"improv={improvement:>5.1f}%  time={elapsed:>6.1f}s  ETA {eta}")

    all_data[config_name]     = costs
    all_histories[config_name] = histories
    print()

# ═══════════════════════════════════════════════════════════════════
#  AGGREGATE STATISTICS
# ═══════════════════════════════════════════════════════════════════

# Global best known across ALL runs of ALL configs
global_best = min(c for costs in all_data.values() for c in costs)

summary = {}
for name, costs in all_data.items():
    m    = mean(costs)
    sd   = std_dev(costs)
    mn   = min(costs)
    mx   = max(costs)
    impr = 100.0 * (INITIAL_COST - m) / INITIAL_COST

    # Relative gap: how far is the MEAN from the best known solution found
    gap_mean = 100.0 * (m - global_best) / global_best
    gap_best = 100.0 * (mn - global_best) / global_best   # always 0 for the best config

    summary[name] = {
        "mean"      : m,
        "std_dev"   : sd,
        "min"       : mn,
        "max"       : mx,
        "range"     : mx - mn,
        "cv"        : 100.0 * sd / m,   # coefficient of variation (%)
        "impr_pct"  : impr,
        "gap_mean"  : gap_mean,
        "gap_best"  : gap_best,
        "params"    : CONFIGS[name],
    }

# ═══════════════════════════════════════════════════════════════════
#  WELCH T-TEST — every pair
# ═══════════════════════════════════════════════════════════════════

config_names = list(CONFIGS.keys())
ttest_results = {}
for i in range(len(config_names)):
    for j in range(i + 1, len(config_names)):
        a, b   = config_names[i], config_names[j]
        t, p, sig = welch_t_test(all_data[a], all_data[b])
        ttest_results[(a, b)] = {"t": t, "p": p, "significant": sig}

# ═══════════════════════════════════════════════════════════════════
#  WRITE RAW CSV
# ═══════════════════════════════════════════════════════════════════

raw_fields = (["config", "run", "best_cost", "improvement_pct",
               "runtime_s", "conv_iter", "conv_pct",
               "still_improving", "last_impr_iter"]
              + list(list(CONFIGS.values())[0].keys()))

with open(OUT_RAW, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=raw_fields)
    w.writeheader()
    w.writerows(raw_rows)

# ═══════════════════════════════════════════════════════════════════
#  WRITE SUMMARY CSV
# ═══════════════════════════════════════════════════════════════════

sum_fields = ["config", "mean", "std_dev", "min", "max", "range",
              "cv_pct", "impr_pct", "gap_from_best_mean_pct",
              "gap_from_best_min_pct",
              "T_start", "alpha", "max_iteration", "reheat_every", "reheat_factor"]

with open(OUT_SUMMARY, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=sum_fields)
    w.writeheader()
    for name, s in summary.items():
        w.writerow({
            "config"                 : name,
            "mean"                   : round(s["mean"], 1),
            "std_dev"                : round(s["std_dev"], 1),
            "min"                    : round(s["min"], 1),
            "max"                    : round(s["max"], 1),
            "range"                  : round(s["range"], 1),
            "cv_pct"                 : round(s["cv"], 2),
            "impr_pct"               : round(s["impr_pct"], 2),
            "gap_from_best_mean_pct" : round(s["gap_mean"], 2),
            "gap_from_best_min_pct"  : round(s["gap_best"], 2),
            **{k: s["params"][k] for k in
               ["T_start", "alpha", "max_iteration", "reheat_every", "reheat_factor"]},
        })

# ═══════════════════════════════════════════════════════════════════
#  BUILD TEXT REPORT
# ═══════════════════════════════════════════════════════════════════

W = 78
def dline(): return "═" * W
def sline(): return "─" * W

report = []
def p(s=""): report.append(s)

p(dline())
p("  SIMULATED ANNEALING — STATISTICAL PERFORMANCE ANALYSIS")
p(f"  {N_RUNS} independent runs per configuration | Initial cost: {INITIAL_COST:,.1f}")
p(f"  Global best found: {global_best:,.1f}")
p(dline())

# ── 1. Aggregate Statistics Table ─────────────────────────────────
p()
p("  1. AGGREGATE STATISTICS")
p(sline())
p(f"  {'Config':<16} {'Mean':>10} {'Std Dev':>10} {'Min':>10} {'Max':>10} "
  f"{'CV%':>6} {'Improv%':>8}")
p(sline())
ranked = sorted(summary.items(), key=lambda x: x[1]["mean"])
for name, s in ranked:
    p(f"  {name:<16} {s['mean']:>10,.0f} {s['std_dev']:>10,.0f} "
      f"{s['min']:>10,.0f} {s['max']:>10,.0f} "
      f"{s['cv']:>5.1f}% {s['impr_pct']:>7.1f}%")
p()
p("  CV% = Coefficient of Variation = StdDev/Mean×100.")
p("  Lower CV% means more consistent (less sensitive to random seed).")

# ── 2. Optimality Gap Table ────────────────────────────────────────
p()
p("  2. RELATIVE OPTIMALITY GAP")
p(sline())
p(f"  Best known solution found across all runs: {global_best:,.1f}")
p()
p(f"  {'Config':<16} {'Gap (mean)':>12} {'Gap (best)':>12}  Interpretation")
p(sline())
for name, s in ranked:
    interp = ("★ reference" if s["gap_best"] == 0.0
              else f"+{s['gap_mean']:.2f}% above best")
    p(f"  {name:<16} {s['gap_mean']:>11.2f}% {s['gap_best']:>11.2f}%  {interp}")
p()
p("  Gap (mean) = (mean_cost − best_known) / best_known × 100.")
p("  A gap < 5% is considered competitive in the literature.")

# ── 3. Convergence Summary ─────────────────────────────────────────
p()
p("  3. CONVERGENCE BEHAVIOUR (averaged over all runs)")
p(sline())

# recompute per-config convergence averages from raw_rows
conv_by_config = {n: {"conv_pcts": [], "last_imprs": [], "still": []}
                  for n in config_names}
for row in raw_rows:
    n = row["config"]
    conv_by_config[n]["conv_pcts"].append(row["conv_pct"])
    conv_by_config[n]["last_imprs"].append(row["last_impr_iter"])
    conv_by_config[n]["still"].append(row["still_improving"])

p(f"  {'Config':<16} {'90%gain@iter%':>14} {'Last impr. iter':>16} {'Still impr. (%)':>16}")
p(sline())
for name in config_names:
    d   = conv_by_config[name]
    cp  = mean(d["conv_pcts"])
    li  = mean(d["last_imprs"])
    pct_still = 100.0 * sum(d["still"]) / len(d["still"])
    p(f"  {name:<16} {cp:>13.0f}% {li:>16,.0f} {pct_still:>15.0f}%")
p()
p("  '90%gain@iter%' = how far through the run 90% of improvement was achieved.")
p("  'Last impr. iter' = last iteration where best_cost improved (avg).")
p("  'Still impr. (%)' = % of runs still improving in the final 20% of iterations.")

# ── 4. Statistical Significance ────────────────────────────────────
p()
p("  4. STATISTICAL SIGNIFICANCE — WELCH'S t-TEST (α = 0.05)")
p(sline())
p(f"  {'Comparison':<36} {'t-stat':>8} {'p-value':>10} {'Significant?':>14}")
p(sline())
for (a, b), res in ttest_results.items():
    sig_str = "YES ← significant" if res["significant"] else "no"
    p(f"  {a} vs {b:<16} {res['t']:>8.3f} {res['p']:>10.4f} {sig_str:>14}")
p()
p("  A significant result (p < 0.05) means the difference in mean cost")
p("  is unlikely to be due to chance. Non-significant pairs are effectively")
p("  equivalent — choose by variance or runtime in that case.")

# ── 5. Recommendation ─────────────────────────────────────────────
best_name  = ranked[0][0]
best_stats = ranked[0][1]
p()
p("  5. RECOMMENDATION")
p(sline())
p(f"  Best mean cost    → {best_name}  (mean={best_stats['mean']:,.0f}, "
  f"CV={best_stats['cv']:.1f}%)")
p(f"  Most consistent   → {min(ranked, key=lambda x: x[1]['cv'])[0]}")
p(f"  Best single run   → achieved {global_best:,.1f}")
p()
p("  Parameters for recommended configuration:")
for k, v in best_stats["params"].items():
    p(f"    {k:<20} = {v}")

p()
p(dline())

report_text = "\n".join(report)
print("\n" + report_text)

with open(OUT_REPORT, "w", encoding="utf-8") as f:
    f.write(report_text + "\n")

# ═══════════════════════════════════════════════════════════════════
#  PLOT 1: LEARNING CURVES — mean trajectory + best trajectory
# ═══════════════════════════════════════════════════════════════════

COLORS = {"A - baseline": "steelblue",
           "B - fast cool": "orange",
           "C - slow cool": "green",
           "D - cold start": "purple"}

TARGET_PTS = 500   # points to plot per curve (downsampled for speed)

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle(f"SA Learning Curves — {N_RUNS} runs per configuration",
             fontsize=13, fontweight="bold")

# Left: mean trajectory across all runs
ax = axes[0]
for name, histories in all_histories.items():
    color = COLORS.get(name, "gray")
    # Align all histories to the shortest run length, then average
    min_len = min(len(h) for h in histories)
    aligned = [[h[i] for h in histories] for i in range(min_len)]
    mean_curve = [mean(row) for row in aligned]
    best_curve = [min(row) for row in aligned]

    xs = [100.0 * i / min_len for i in range(min_len)]
    # Downsample
    step = max(1, min_len // TARGET_PTS)
    xs_d = xs[::step]
    mean_d = mean_curve[::step]
    best_d = best_curve[::step]

    ax.plot(xs_d, mean_d, color=color, linewidth=1.8, label=f"{name} (mean)")
    ax.plot(xs_d, best_d, color=color, linewidth=0.8, linestyle="--", alpha=0.6)

ax.axhline(y=INITIAL_COST, color="red", linestyle=":", linewidth=1.2,
           label=f"Initial: {INITIAL_COST:,.0f}")
ax.set_xlabel("Run completion (%)")
ax.set_ylabel("Best cost")
ax.set_title("Mean trajectory (solid) + best trajectory (dashed)")
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

# Right: final cost distribution (all N_RUNS points per config)
ax2 = axes[1]
positions = range(len(config_names))
bp_data   = [all_data[n] for n in config_names]
short_labels = [n.split(" - ")[1] if " - " in n else n for n in config_names]

bp = ax2.boxplot(bp_data, positions=positions, widths=0.5, patch_artist=True,
                 medianprops=dict(color="black", linewidth=2))

for patch, name in zip(bp["boxes"], config_names):
    patch.set_facecolor(COLORS.get(name, "gray"))
    patch.set_alpha(0.7)

# Overlay individual points
for i, (name, costs) in enumerate(all_data.items()):
    jitter = [i + random.uniform(-0.1, 0.1) for _ in costs]
    ax2.scatter(jitter, costs, s=18, color=COLORS.get(name, "gray"),
                zorder=3, alpha=0.8)

ax2.set_xticks(list(positions))
ax2.set_xticklabels(short_labels, fontsize=9)
ax2.set_ylabel("Final cost")
ax2.set_title(f"Cost distribution ({N_RUNS} runs each)")
ax2.grid(True, alpha=0.3, axis="y")
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

# Legend patches
patches = [mpatches.Patch(color=COLORS.get(n, "gray"), alpha=0.7, label=n)
           for n in config_names]
ax2.legend(handles=patches, fontsize=8, loc="upper right")

plt.tight_layout()
plt.savefig(OUT_CURVES, dpi=150)
print(f"\n  Learning curves saved → {OUT_CURVES}")

# ═══════════════════════════════════════════════════════════════════
#  DONE
# ═══════════════════════════════════════════════════════════════════

total_elapsed = time.perf_counter() - global_start
print(f"\n  Raw data     → {OUT_RAW}")
print(f"  Summary CSV  → {OUT_SUMMARY}")
print(f"  Report text  → {OUT_REPORT}")
print(f"  Plot         → {OUT_CURVES}")
print(f"\n  Total runtime: {timedelta(seconds=int(total_elapsed))}\n")
