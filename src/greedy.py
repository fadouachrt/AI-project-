import random
import time
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models   import Team, Match, Round, Schedule
from schedule import double_round_robin, assign_all_days


def _round_travel_cost(round_obj: Round,
                       prev_location: dict,
                       dist_matrix: dict) -> float:

    total = 0.0
    for match in round_obj.matches:
        origin = prev_location.get(match.away.name, match.away.name)
        total += dist_matrix[origin][match.home.name]
    return total


def _away_streak(team_name: str, ordered_so_far: list) -> int:
    streak = 0
    for r in reversed(ordered_so_far):
        is_home = any(m.home.name == team_name for m in r.matches)
        is_away = any(m.away.name == team_name for m in r.matches)
        if is_home:
            return streak
        if is_away:
            streak += 1
        else:
            break
    return streak


def _greedy_order(schedule: Schedule, dist_matrix: dict) -> Schedule:
    remaining     = list(schedule.rounds)
    ordered       = []
    prev_location = {t.name: t.name for t in schedule.teams}

    while remaining:
        scores = []
        for i, r in enumerate(remaining):
            km     = _round_travel_cost(r, prev_location, dist_matrix)
            streak = sum(_away_streak(m.away.name, ordered) for m in r.matches)
            scores.append((km, streak, i))

        scores.sort(key=lambda x: (x[0], x[1]))
        best_round             = remaining.pop(scores[0][2])
        best_round.round_index = len(ordered)
        ordered.append(best_round)

        for match in best_round.matches:
            prev_location[match.away.name] = match.home.name
            prev_location[match.home.name] = match.home.name

    return Schedule(rounds=ordered, teams=schedule.teams)



def greedy_schedule(teams: list,
                    dist_matrix: dict,
                    seed: int = 42,
                    verbose: bool = False) -> Schedule:
    random.seed(seed)
    t0 = time.time()

    raw      = double_round_robin(teams)
    ordered  = _greedy_order(raw, dist_matrix)
    schedule = assign_all_days(ordered)

    if verbose:
        km      = compute_total_travel(schedule, dist_matrix)
        elapsed = time.time() - t0
        print(f"[greedy] rounds={schedule.total_rounds()} | "
              f"travel={km:,.1f} km | time={elapsed:.4f}s")

    return schedule


def compute_total_travel(schedule: Schedule, dist_matrix: dict) -> float:
    prev  = {t.name: t.name for t in schedule.teams}
    total = 0.0

    for r in schedule.rounds:
        for match in r.matches:
            total += dist_matrix[prev.get(match.away.name,
                                          match.away.name)][match.home.name]
        for match in r.matches:
            prev[match.away.name] = match.home.name
            prev[match.home.name] = match.home.name

    return round(total, 2)


def validate_schedule(schedule: Schedule) -> dict:
    teams = [t.name for t in schedule.teams]
    n     = len(teams)
    issues = {
        "wrong_round_count"          : 0,
        "wrong_matches_per_round"    : 0,
        "team_appears_twice_in_round": 0,
        "pair_not_exactly_once"      : 0,
    }

    if schedule.total_rounds() != (n - 1) * 2:
        issues["wrong_round_count"] = abs(schedule.total_rounds() - (n - 1) * 2)

    pair_count = {}
    for r in schedule.rounds:
        if len(r.matches) != n // 2:
            issues["wrong_matches_per_round"] += 1
        seen = set()
        for m in r.matches:
            if m.home.name in seen or m.away.name in seen:
                issues["team_appears_twice_in_round"] += 1
            seen.add(m.home.name)
            seen.add(m.away.name)
            key = (m.home.name, m.away.name)
            pair_count[key] = pair_count.get(key, 0) + 1

    for t1 in teams:
        for t2 in teams:
            if t1 != t2 and pair_count.get((t1, t2), 0) != 1:
                issues["pair_not_exactly_once"] += 1

    return issues


# test by claude
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(__file__))
    from data_loader import load_all, DERBIES, WEEKEND

    candidates = ["data/teams.csv", "../data/teams.csv", "teams.csv"]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if path is None:
        print("ERROR: teams.csv not found.")
        raise SystemExit(1)

    # ── Load ───────────────────────────────────────────────────────
    teams, dist_matrix, flat_matrix = load_all(path)
    print(f"Loaded {len(teams)} teams.\n")

    # ── Run greedy ─────────────────────────────────────────────────
    schedule = greedy_schedule(teams, dist_matrix, seed=42, verbose=True)

    # ── Fadoua's internal validation ──────────────────────────────
    issues = validate_schedule(schedule)
    print("\n=== Internal Validation ===")
    for name, count in issues.items():
        print(f"  {'✓' if count == 0 else '✗'}  {name:<40}: {count}")

    # ── Sally's authoritative validation ──────────────────────────
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from constraints import is_valid, csp_validate
        print("\n=== Sally's is_valid() ===")
        print(f"  {'✓ VALID' if is_valid(schedule) else '✗ INVALID'}")

        violations = csp_validate(schedule)
        if not violations:
            print("csp_validate: no violations ✓")
        else:
            print(f"  csp_validate: {len(violations)} violation(s):")
            for v in violations:
                print(f"    - {v}")
    except ImportError:
        print("\n  (constraints.py not found — skipping Sally's validation)")

    # ── Douaa's cost_function compatibility ───────────────────────
    print("\n=== flat_matrix format (for Douaa's cost_function) ===")
    print(f"  flat_matrix[('MC Alger', 'MC Oran')] = "
          f"{flat_matrix[('MC Alger', 'MC Oran')]:.1f} km")
    print(f"  DERBIES  = {DERBIES}")
    print(f"  WEEKEND  = {WEEKEND}")

    # ── Summary ────────────────────────────────────────────────────
    km = compute_total_travel(schedule, dist_matrix)
    print(f"\n=== Final Summary ===")
    print(f"  Rounds   : {schedule.total_rounds()}")
    print(f"  Matches  : {schedule.total_matches()}")
    print(f"  Total km : {km:,.1f}")