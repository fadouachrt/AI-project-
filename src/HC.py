import time
import random
from collections import deque
from copy import deepcopy

from neighbour import generate_one_random_neighbor
from schedule import double_round_robin, assign_all_days
from Minimize_total import cost_function, total_distance
from Soft_constraints import Rest_day_penalty, Derbies_penalty, successive_away_penalty


# ── Diagnostic helper ────────────────────────────────────────────────────────

def print_solution_details(schedule, teams, distances, derbies, weekends,
                           penalty=500, label=""):
    dist  = total_distance(schedule, distances, teams)
    rest  = Rest_day_penalty(schedule, teams, penalty)
    derby = Derbies_penalty(schedule, derbies, weekends, penalty)

    away_total = 0
    away_violations = []
    for team in teams:
        v = successive_away_penalty(team, schedule, penalty)
        if v > 0:
            away_violations.append((team.name, v // penalty, v))
            away_total += v

    total = dist + rest + derby + away_total

    title = f"  {label}  " if label else "  Schedule Details  "
    print("\n" + "═" * 52)
    print(f"{title:^52}")
    print("═" * 52)
    print(f"  {'Total travel distance':<30} {dist:>10,.1f} km")
    print("─" * 52)
    print(f"  {'Rest day violations':<30} {rest // penalty:>10}  ×{penalty}")
    print(f"  {'  → penalty cost':<30} {rest:>10,.0f}")
    print("─" * 52)
    print(f"  {'Derby not on weekend':<30} {derby // penalty:>10}  ×{penalty}")
    print(f"  {'  → penalty cost':<30} {derby:>10,.0f}")
    print("─" * 52)
    if away_violations:
        print(f"  Successive away (≥3) violations:")
        for name, count, cost in away_violations:
            print(f"    {name:<26} {count:>2} violation(s)  +{cost:,.0f}")
        print(f"  {'  → penalty cost':<30} {away_total:>10,.0f}")
    else:
        print(f"  {'Successive away violations':<30} {'none':>10}")
    print("═" * 52)
    print(f"  {'GRAND TOTAL COST':<30} {total:>10,.1f}")
    print("═" * 52 + "\n")

    return {
        "distance"        : dist,
        "rest_violations" : rest  // penalty,
        "rest_penalty"    : rest,
        "derby_violations": derby // penalty,
        "derby_penalty"   : derby,
        "away_violations" : len(away_violations),
        "away_penalty"    : away_total,
        "total"           : total,
    }


# ── Tabu helpers ──────────────────────────────────────────────────────────────

def _schedule_fingerprint(schedule) -> tuple:
    return tuple(
        m.ordered_pair()
        for r in schedule.rounds
        for m in r.matches
    )


def _best_sideways(candidates, distances, teams, tabu):
    best_nb, best_dist = None, float("inf")
    for nb, _cost in candidates:
        fp = _schedule_fingerprint(nb)
        if fp in tabu:
            continue
        d = total_distance(nb, distances, teams)
        if d < best_dist:
            best_nb, best_dist = nb, d
    return best_nb  # None if every candidate was tabu


# ── Stochastic step ───────────────────────────────────────────────────────────

def _stochastic_step(current, current_cost, cost_fn, teams, distances, derbies, weekends,
                     n_samples=50, tabu=None):
    """Sample `n_samples` random neighbours, accept the best improving one.
    Falls back to the best non-tabu sideways move when no improvement exists.
    """
    if tabu is None:
        tabu = set()

    improving           = []
    sideways_candidates = []
    for _ in range(n_samples):
        nb = generate_one_random_neighbor(current)
        c  = cost_fn(nb, teams, distances, derbies, weekends)
        if c < current_cost:
            improving.append((nb, c))
        elif c == current_cost:
            sideways_candidates.append((nb, c))

    if improving:
        best = min(improving, key=lambda x: x[1])
        return best[0], best[1], "improved"

    chosen = _best_sideways(sideways_candidates, distances, teams, tabu)
    if chosen is not None:
        return chosen, current_cost, "sideways"

    return current, current_cost, "stuck"


# ── Random-restart helper ─────────────────────────────────────────────────────

def _random_restart_schedule(teams):
    shuffled = list(teams)
    random.shuffle(shuffled)
    return assign_all_days(double_round_robin(shuffled))


# ── Main entry point ──────────────────────────────────────────────────────────

def hill_climbing(
    schedule,
    distances,
    derbies,
    weekends,
    teams,
    penalty        = 500,
    max_restarts   = 5,
    max_iterations = 200,
    n_samples      = 50,   # neighbours sampled per step
    max_sideways   = 10,   # max consecutive sideways moves before restart
    tabu_size      = 20,   # sliding-window tabu size
    cost_fn        = None,
    verbose        = True,
):
    if cost_fn is None:
        cost_fn = cost_function

    best      = deepcopy(schedule)
    best_cost = cost_fn(best, teams, distances, derbies, weekends)
    history   = []
    global_step = 0

    for restart in range(max_restarts + 1):
        current = (
            deepcopy(schedule) if restart == 0
            else _random_restart_schedule(teams)
        )
        current_cost  = cost_fn(current, teams, distances, derbies, weekends)
        sideways_used = 0

        # FIFO tabu window: deque for ordered eviction, set for O(1) lookup
        tabu_q = deque(maxlen=tabu_size)
        tabu_s = set()

        if verbose:
            tag = "initial" if restart == 0 else f"restart {restart}"
            print(f"\n  ── stochastic  {tag}  (start cost={current_cost:,.1f})")

        for it in range(max_iterations):
            next_s, next_cost, status = _stochastic_step(
                current, current_cost,
                cost_fn, teams, distances, derbies, weekends,
                n_samples=n_samples, tabu=tabu_s,
            )

            if status == "improved":
                sideways_used = 0
                fp = _schedule_fingerprint(current)
                if fp not in tabu_s:
                    if len(tabu_q) == tabu_size:
                        tabu_s.discard(tabu_q[0])
                    tabu_q.append(fp)
                    tabu_s.add(fp)

                current      = next_s
                current_cost = next_cost
                global_step += 1

                if current_cost < best_cost:
                    best      = deepcopy(current)
                    best_cost = current_cost

                history.append(best_cost)

                if verbose:
                    print(f"    step {global_step:>4}  cost={best_cost:,.1f}")

            elif status == "sideways":
                sideways_used += 1
                if sideways_used > max_sideways:
                    if verbose:
                        print(f"    sideways limit ({max_sideways}) reached after "
                              f"{it + 1} steps — triggering restart")
                    break

                fp = _schedule_fingerprint(current)
                if fp not in tabu_s:
                    if len(tabu_q) == tabu_size:
                        tabu_s.discard(tabu_q[0])
                    tabu_q.append(fp)
                    tabu_s.add(fp)

                current      = next_s
                current_cost = next_cost
                global_step += 1
                history.append(best_cost)

                if verbose:
                    print(f"    step {global_step:>4}  [sideways {sideways_used}/{max_sideways}]"
                          f"  cost={current_cost:,.1f}")

            else:  # "stuck"
                if verbose:
                    print(f"    truly stuck after {it + 1} steps — triggering restart")
                break

    return best, best_cost, history


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os, sys
    from data_loader import load_all
    from simulated_annealing import load_derbies

    _candidates = ["data/teams.csv", "../data/teams.csv", "teams.csv"]
    _teams_csv  = next((p for p in _candidates if os.path.exists(p)), None)
    if _teams_csv is None:
        print("ERROR: teams.csv not found.")
        sys.exit(1)

    teams, distances = load_all(_teams_csv)
    WEEKEND_DAYS = {"Friday", "Saturday"}
    derbies = load_derbies("../data/derbies.csv")

    initial = assign_all_days(double_round_robin(teams))
    initial.print_schedule()
    print_solution_details(initial, teams, distances, derbies, WEEKEND_DAYS,
                           label="INITIAL SCHEDULE")

    start = time.time()
    best, best_cost, history = hill_climbing(
        schedule       = initial,
        distances      = distances,
        derbies        = derbies,
        weekends       = WEEKEND_DAYS,
        teams          = teams,
        max_restarts   = 5,
        max_iterations = 200,
        max_sideways   = 10,
        cost_fn        = cost_function,
        verbose        = True,
    )
    end = time.time()

    print_solution_details(best, teams, distances, derbies, WEEKEND_DAYS,
                           label="BEST — STOCHASTIC")
    print(f"Running time: {end - start:.2f}s")