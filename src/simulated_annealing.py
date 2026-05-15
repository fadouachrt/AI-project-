import math
import random
from neighbour import generate_one_random_neighbor
from Minimize_total import cost_function
from models import Match, Schedule
from copy import deepcopy
from schedule import double_round_robin ,assign_all_days
from data_loader import load_all,build_distance_matrix
import csv
import time
import matplotlib.pyplot as plt

def load_derbies(file_path):
    derbies = set()

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            team_a = row["team_a"]
            team_b = row["team_b"]

            derbies.add(frozenset([team_a, team_b]))

    return derbies

def simulated_annealing(schedule ,distances ,derbies ,weekends,teams,T_start ,T_min ,alpha ,max_iteration, cost_fn=None, reheat_every=2000, reheat_factor=2.0):
    T = T_start
    current=deepcopy(schedule)
    current_cost = cost_fn(current,teams,distances,derbies,weekends)
    best = deepcopy(current)
    best_cost = cost_fn(best,teams,distances,derbies,weekends)
    no_improve_count = 0
    last_best = best_cost
    it=0
    history = [] #track improvment of cost
    while it < max_iteration and T > T_min:

        neighbor = generate_one_random_neighbor(current)
        neighbor_cost = cost_fn(neighbor,teams,distances,derbies,weekends)
        delta = neighbor_cost - current_cost
        if delta < 0:
            current = neighbor
            current_cost = neighbor_cost
        else:
            P = math.exp(-delta/T)
            r=random.random()
            if r< P:
                current = neighbor
                current_cost = neighbor_cost
            else:
                pass
        if current_cost<best_cost:
            best = deepcopy(current)
            best_cost = current_cost
        
        #implement reheat
        # if current_cost < last_best:
        #     last_best = current_cost
        #     no_improve_count = 0
        # else:
        #     no_improve_count += 1

        # if no_improve_count >= reheat_every:
        #     T = min(T * reheat_factor, T_start * 0.1)  # reheat but cap below T_start
        #     no_improve_count = 0
        
        
        if best_cost < last_best:          # track BEST, not current
            last_best = best_cost
            no_improve_count = 0
        else:
            no_improve_count += 1

        if no_improve_count >= reheat_every:
            T = min(T * reheat_factor, T_start * 0.5)  # cap at 50% not 10%
            no_improve_count = 0
            last_best = best_cost  
        T = T * alpha
        history.append(best_cost)
        it +=1    
    
    
    return best , best_cost , history    


def run_experiment(config_name, schedule, teams, distances, derbies, weekends, **sa_params):
    costs = []
    times = []
    
    # get initial cost ONCE (same starting point for all runs)
    initial_cost = cost_function(schedule, teams, distances, derbies, weekends)
    
    for run in range(3):
        sched_copy = deepcopy(schedule)
        
        start = time.time()
        _, best_cost, _ = simulated_annealing(
            schedule  = sched_copy,
            distances = distances,
            derbies   = derbies,
            weekends  = weekends,
            teams     = teams,
            cost_fn   = cost_function,
            **sa_params
        )
        elapsed = time.time() - start
        
        improvement = ((initial_cost - best_cost) / initial_cost) * 100  # ← %
        
        costs.append(best_cost)
        times.append(elapsed)
        print(f"  {config_name} run {run+1}: cost={best_cost:.0f}  improvement={improvement:.1f}%  time={elapsed:.2f}s")
    
    avg_cost       = sum(costs) / 3
    avg_time       = sum(times) / 3
    avg_improvement = ((initial_cost - avg_cost) / initial_cost) * 100
    
    print(f"  → Average: cost={avg_cost:.0f}  improvement={avg_improvement:.1f}%  time={avg_time:.2f}s\n")
    return avg_cost, avg_time, avg_improvement, initial_cost

#evaluate convergance

def plot_convergence(history, config_name, initial_cost):
    iterations = list(range(len(history)))
    
    plt.figure(figsize=(10, 5))
    plt.plot(iterations, history, color='steelblue', linewidth=1.2, label='Best cost')
    
    # add horizontal line for initial cost
    plt.axhline(y=initial_cost, color='red', linestyle='--', 
                linewidth=1, label=f'Initial cost: {initial_cost:.0f}')
    
    # add horizontal line for final best
    plt.axhline(y=history[-1], color='green', linestyle='--',
                linewidth=1, label=f'Final cost: {history[-1]:.0f}')
    
    plt.title(f'SA Convergence — {config_name}')
    plt.xlabel('Iteration')
    plt.ylabel('Best Cost')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'convergence_{config_name}.png', dpi=150)
    plt.show()
    print(f"Saved: convergence_{config_name}.png")


def plot_all_configs(all_histories, initial_cost):
    plt.figure(figsize=(12, 6))
    
    colors = ['steelblue', 'orange', 'green', 'purple']
    
    for (config_name, history), color in zip(all_histories.items(), colors):
        plt.plot(history, linewidth=1.2, label=config_name, color=color)
    
    plt.axhline(y=initial_cost, color='red', linestyle='--',
                linewidth=1.5, label=f'Initial: {initial_cost:.0f}')
    
    plt.title('SA Convergence — All Configurations Compared')
    plt.xlabel('Iteration')
    plt.ylabel('Best Cost')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('convergence_all_configs.png', dpi=150)
    plt.show()
    
def analyze_convergence(history, config_name):
    total_iter = len(history)
    initial    = history[0]
    final      = history[-1]
    improvement = ((initial - final) / initial) * 100
    
    # find at what iteration 90% of improvement was already achieved
    target = initial - 0.90 * (initial - final)
    convergence_iter = next(
        (i for i, cost in enumerate(history) if cost <= target),
        total_iter  # fallback if never reached
    )
    convergence_pct = (convergence_iter / total_iter) * 100
    
    # check if it's still improving in the last 20% of iterations
    last_20pct_start = int(0.8 * total_iter)
    improvement_in_last_20 = history[last_20pct_start] - history[-1]
    still_improving = improvement_in_last_20 > 0
    
    print(f"\n── Convergence Analysis: {config_name} ──")
    print(f"  Total iterations      : {total_iter}")
    print(f"  Initial cost          : {initial:.0f}")
    print(f"  Final cost            : {final:.0f}")
    print(f"  Total improvement     : {improvement:.1f}%")
    print(f"  90% of gain reached at: iteration {convergence_iter} ({convergence_pct:.0f}% through run)")
    print(f"  Still improving in last 20%: {'yes' if still_improving else 'no — plateaued'}")
    print(f"  Improvement in last 20%: {improvement_in_last_20:.0f}")
    
    return {
        "config": config_name,
        "final_cost": final,
        "improvement_pct": improvement,
        "convergence_iter": convergence_iter,
        "convergence_pct": convergence_pct,
        "plateaued": not still_improving
    }
 
 
 
# if __name__ == "__main__":

#     teamms, distances = load_all("../data/teams.csv")
#     WEEKEND_DAYS = {"Friday", "Saturday"}
#     derbie = load_derbies("../data/derbies.csv")
#     schedulle = double_round_robin(teamms)
#     shechdual = assign_all_days(schedulle)

#     initial_cost = cost_function(shechdual, teamms, distances, derbie, WEEKEND_DAYS)
#     print(f"Initial cost: {initial_cost:.0f}")

#     configs = [
#         ("A - baseline",  {"T_start": 8000, "alpha": 0.9997, "T_min": 0.1, "max_iteration": 20000, "reheat_every": 2000, "reheat_factor": 2.0}),
#         ("B - fast cool", {"T_start": 8000, "alpha": 0.9994,   "T_min": 0.1, "max_iteration": 20000, "reheat_every": 2000, "reheat_factor": 2.0}),
#         ("C - slow cool", {"T_start": 15000, "alpha": 0.9997, "T_min": 0.1, "max_iteration": 30000, "reheat_every": 4000, "reheat_factor": 2.5}),
#         ("D - cold start",{"T_start": 8000,  "alpha": 0.9997, "T_min": 0.1, "max_iteration": 30000, "reheat_every": 4000, "reheat_factor": 2.0}),
#     ]

#     all_histories    = {}
#     convergence_data = []

#     for name, params in configs:
#         sched_copy = deepcopy(shechdual)
#         _, best_cost, history = simulated_annealing(
#             schedule  = sched_copy,
#             distances = distances,
#             derbies   = derbie,
#             weekends  = WEEKEND_DAYS,
#             teams     = teamms,
#             cost_fn   = cost_function,
#             **params
#         )
#         all_histories[name] = history
        
#         # plot individual convergence
#         plot_convergence(history, name, initial_cost)
        
#         # numerical analysis
#         data = analyze_convergence(history, name)
#         convergence_data.append(data)

#     # plot all on one chart
#     plot_all_configs(all_histories, initial_cost)

#     # print convergence summary table
#     print("\n── Convergence Summary ──")
#     print(f"{'Config':<20} {'Final Cost':>12} {'Improvement':>13} {'90% gain at':>13} {'Plateaued?':>12}")
#     print("-" * 74)
#     for d in convergence_data:
#         print(f"{d['config']:<20} {d['final_cost']:>12.0f} "
#               f"{d['improvement_pct']:>12.1f}% "
#               f"{d['convergence_pct']:>12.0f}% "
#               f"{'yes' if d['plateaued'] else 'no':>12}")
     
if __name__ == "__main__":

    teamms, distances = load_all("../data/teams.csv")
    WEEKEND_DAYS = {"Friday", "Saturday"}
    derbie = load_derbies("../data/derbies.csv")
    schedulle = double_round_robin(teamms)
    shechdual = assign_all_days(schedulle)

    initial_cost = cost_function(shechdual, teamms, distances, derbie, WEEKEND_DAYS)
    print(f"Initial cost: {initial_cost:.0f}\n")

    configs = [
        ("A - baseline",  {"T_start": 8000,  "alpha": 0.9995, "T_min": 0.1, "max_iteration": 20000, "reheat_every": 2000, "reheat_factor": 2.0}),
        ("B - fast cool", {"T_start": 8000,  "alpha": 0.9994, "T_min": 0.1, "max_iteration": 20000, "reheat_every": 2000, "reheat_factor": 2.0}),
        ("C - slow cool", {"T_start": 15000, "alpha": 0.9997, "T_min": 0.1, "max_iteration": 30000, "reheat_every": 4000, "reheat_factor": 2.5}),
        ("D - cold start",{"T_start": 8000,  "alpha": 0.9997, "T_min": 0.1, "max_iteration": 30000, "reheat_every": 4000, "reheat_factor": 2.0}),
    ]

    RUNS = 3
    all_summary = {}  # for final table
    all_histories_per_config = {}  # for convergence plot

    for name, params in configs:
        print(f"{'='*55}")
        print(f"  Config: {name}")
        print(f"{'='*55}")

        costs       = []
        times       = []
        conv_pcts   = []
        still_imprs = []
        all_runs_histories = []

        for run in range(RUNS):
            sched_copy = deepcopy(shechdual)

            start = time.time()
            _, best_cost, history = simulated_annealing(
                schedule  = sched_copy,
                distances = distances,
                derbies   = derbie,
                weekends  = WEEKEND_DAYS,
                teams     = teamms,
                cost_fn   = cost_function,
                **params
            )
            elapsed = time.time() - start

            improvement = ((initial_cost - best_cost) / initial_cost) * 100

            # ── convergence metrics for this run ──
            total_iter = len(history)
            final_cost = history[-1]
            target     = history[0] - 0.90 * (history[0] - final_cost)
            conv_iter  = next(
                (i for i, c in enumerate(history) if c <= target),
                total_iter
            )
            conv_pct = (conv_iter / total_iter) * 100

            last_20_start   = int(0.8 * total_iter)
            improv_last_20  = history[last_20_start] - history[-1]
            still_improving = improv_last_20 > 0

            costs.append(best_cost)
            times.append(elapsed)
            conv_pcts.append(conv_pct)
            still_imprs.append(still_improving)
            all_runs_histories.append(history)

            print(f"  Run {run+1}: cost={best_cost:.0f}  "
                  f"improvement={improvement:.1f}%  "
                  f"time={elapsed:.1f}s  "
                  f"90%gain@{conv_pct:.0f}%  "
                  f"still_improving={'yes' if still_improving else 'NO'}")

        # ── averages ──
        avg_cost    = sum(costs) / RUNS
        avg_time    = sum(times) / RUNS
        avg_imp     = ((initial_cost - avg_cost) / initial_cost) * 100
        avg_conv    = sum(conv_pcts) / RUNS
        min_cost    = min(costs)
        max_cost    = max(costs)
        variance    = max_cost - min_cost
        all_improving = all(still_imprs)

        print(f"\n  → Avg cost     : {avg_cost:.0f}")
        print(f"  → Avg improve  : {avg_imp:.1f}%")
        print(f"  → Avg time     : {avg_time:.1f}s")
        print(f"  → Avg 90% gain : {avg_conv:.0f}% through run")
        print(f"  → Cost range   : {min_cost:.0f} – {max_cost:.0f}  (variance={variance:.0f})")
        print(f"  → Still improving in last 20%: {'all runs yes' if all_improving else 'some runs plateaued'}\n")

        all_summary[name] = {
            "avg_cost"  : avg_cost,
            "avg_imp"   : avg_imp,
            "avg_time"  : avg_time,
            "avg_conv"  : avg_conv,
            "min_cost"  : min_cost,
            "max_cost"  : max_cost,
            "variance"  : variance,
            "all_improving": all_improving,
        }

        # keep the best run's history for the convergence plot
        best_run_idx = costs.index(min(costs))
        all_histories_per_config[name] = all_runs_histories[best_run_idx]

    # ══════════════════════════════════════════════════
    #  FINAL SUMMARY TABLE
    # ══════════════════════════════════════════════════
    print(f"\n{'='*90}")
    print("  FINAL SUMMARY TABLE")
    print(f"{'='*90}")
    print(f"  {'Config':<18} {'Avg Cost':>10} {'Improv':>8} {'Time(s)':>9} "
          f"{'90%gain@':>9} {'Min cost':>10} {'Max cost':>10} {'Variance':>10}")
    print(f"  {'-'*88}")
    for name, r in all_summary.items():
        print(f"  {name:<18} {r['avg_cost']:>10.0f} {r['avg_imp']:>7.1f}% "
              f"{r['avg_time']:>9.1f} {r['avg_conv']:>8.0f}% "
              f"{r['min_cost']:>10.0f} {r['max_cost']:>10.0f} "
              f"{r['variance']:>10.0f}")

    best_config = min(all_summary, key=lambda k: all_summary[k]["avg_cost"])
    print(f"\n  → Best configuration: {best_config} "
          f"(avg_cost={all_summary[best_config]['avg_cost']:.0f}, "
          f"improvement={all_summary[best_config]['avg_imp']:.1f}%)")

    # ══════════════════════════════════════════════════
    #  CONVERGENCE PLOT — best run of each config
    # ══════════════════════════════════════════════════
    plt.figure(figsize=(13, 6))
    colors = ['steelblue', 'orange', 'green', 'purple']

    for (name, history), color in zip(all_histories_per_config.items(), colors):
        plt.plot(history, linewidth=1.3, label=name, color=color)

    plt.axhline(y=initial_cost, color='red', linestyle='--',
                linewidth=1.5, label=f'Initial: {initial_cost:.0f}')

    plt.title('SA Convergence — All Configurations (best run each)')
    plt.xlabel('Iteration')
    plt.ylabel('Best Cost')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('convergence_final.png', dpi=150)
    plt.show()
    print("\nSaved: convergence_final.png")   
        
           
# if __name__ == "__main__":

#     teamms, distances = load_all("../data/teams.csv")
#     WEEKEND_DAYS = {"Friday", "Saturday"}
#     derbie = load_derbies("../data/derbies.csv")
#     schedulle = double_round_robin(teamms)
#     shechdual = assign_all_days(schedulle)

#     initial_cost = cost_function(shechdual, teamms, distances, derbie, WEEKEND_DAYS)
#     print(f"Initial cost (before any algorithm): {initial_cost:.0f}\n")

#     configs = [
#         ("A - baseline",  {"T_start": 8000, "alpha": 0.9997, "T_min": 0.1, "max_iteration": 20000, "reheat_every": 2000, "reheat_factor": 2.0}),
#         ("B - fast cool", {"T_start": 8000, "alpha": 0.9994,   "T_min": 0.1, "max_iteration": 20000, "reheat_every": 2000, "reheat_factor": 2.0}),
#         ("C - slow cool", {"T_start": 15000, "alpha": 0.9997, "T_min": 0.1, "max_iteration": 30000, "reheat_every": 4000, "reheat_factor": 2.5}),
#         ("D - cold start",{"T_start": 8000,  "alpha": 0.9997, "T_min": 0.1, "max_iteration": 30000, "reheat_every": 4000, "reheat_factor": 2.0}),
#     ]

#     results = {}
#     for name, params in configs:
#         print(f"Running config {name}...")
#         avg_cost, avg_time, avg_imp, _ = run_experiment(
#             name, shechdual, teamms, distances, derbie, WEEKEND_DAYS, **params
#         )
#         results[name] = (avg_cost, avg_time, avg_imp)

#     # ── Summary Table ──
#     print("\n── Summary Table ──")
#     print(f"{'Config':<20} {'Avg Cost':>12} {'Improvement':>13} {'Avg Time (s)':>14}")
#     print("-" * 62)
#     for name, (cost, t, imp) in results.items():
#         print(f"{name:<20} {cost:>12.0f} {imp:>12.1f}% {t:>14.2f}")
    
#     # highlight the best config
#     best_config = min(results, key=lambda k: results[k][0])
#     print(f"\n→ Best configuration: {best_config} "
#           f"(cost={results[best_config][0]:.0f}, "
#           f"improvement={results[best_config][2]:.1f}%)")


# if __name__ == "__main__":

#     teamms , distances = load_all("../data/teams.csv")
#     WEEKEND_DAYS = {"Friday", "Saturday"}
#     derbie= load_derbies("../data/derbies.csv")
    
#     schedulle = double_round_robin(teamms)
#     shechdual = assign_all_days(schedulle)
#     print(cost_function(shechdual,teamms,distances,derbie,WEEKEND_DAYS))
    
#     best, best_cost, history = simulated_annealing(
#         schedule = shechdual,
#         distances = distances,
#         derbies = derbie,
#         weekends = WEEKEND_DAYS,
#         teams = teamms,
#         T_start = 15000,
#         T_min = 0.1,
#         alpha = 0.9997,
#         reheat_every  = 2_000,
#         reheat_factor = 2.0,
#         max_iteration = 20000,
#         cost_fn=cost_function
#     )
#     print(f"\nBest schedule found (cost={best_cost}):")
  
    
    

