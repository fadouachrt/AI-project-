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


def _greedy_order(schedule: Schedule, dist_matrix: dict) -> tuple:
    remaining     = list(schedule.rounds)
    ordered       = []
    prev_location = {t.name: t.name for t in schedule.teams}
    cumulative_km = 0.0
    history       = []          # cumulative cost after each round is placed

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

        # accumulate travel for this round and record it
        cumulative_km += _round_travel_cost(best_round, prev_location, dist_matrix)
        history.append(round(cumulative_km, 2))

        for match in best_round.matches:
            prev_location[match.away.name] = match.home.name
            prev_location[match.home.name] = match.home.name

    return Schedule(rounds=ordered, teams=schedule.teams), history



def greedy_schedule(teams: list,
                    dist_matrix: dict,
                    seed: int = 42,
                    verbose: bool = False) -> tuple:
    
    random.seed(seed)
    t0 = time.time()

    raw                = double_round_robin(teams)
    ordered, history   = _greedy_order(raw, dist_matrix)   # unpack tuple
    schedule           = assign_all_days(ordered)
    best_cost          = compute_total_travel(schedule, dist_matrix)

    if verbose:
        elapsed = time.time() - t0
        print(f"[greedy] rounds={schedule.total_rounds()} | "
              f"travel={best_cost:,.1f} km | time={elapsed:.4f}s")

    return schedule, best_cost, history


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


#test by claude
if __name__ == "__main__":

    sys.path.insert(0, os.path.dirname(__file__))
    from data_loader import load_all, load_derbies
    from Soft_constraints import Derbies_penalty, Rest_day_penalty, successive_away_penalty
    PENALTY    = 500
    WEEKENDS   = {"Friday", "Saturday"}
    # ── Load ───────────────────────────────────────────────────────
    team_candidates   = ["data/teams.csv",   "../data/teams.csv",   "teams.csv"]
    derby_candidates  = ["data/derbies.csv",  "../data/derbies.csv",  "derbies.csv"]
    teams_path  = next((p for p in team_candidates  if os.path.exists(p)), None)
    derby_path  = next((p for p in derby_candidates if os.path.exists(p)), None)
    if teams_path is None:
        print("ERROR: teams.csv not found."); raise SystemExit(1)
    teams, dist_matrix = load_all(teams_path)
    derbies = load_derbies(derby_path) if derby_path else set()
    if not derby_path:
        print("WARNING: derbies.csv not found — derby penalty will be 0.\n")
    print(f"Loaded {len(teams)} teams, {len(derbies)} derby pairs.\n")

    # ── Run greedy (returns tuple) ─────────────────────────
    schedule, best_cost, history = greedy_schedule(teams, dist_matrix,

                                                   seed=42, verbose=True)
    # ══════════════════════════════════════════════════════════════
    # 1. HARD CONSTRAINT VALIDATION
    # ══════════════════════════════════════════════════════════════

    print("\n" + "="*52)
    print("  HARD CONSTRAINTS")
    print("="*52)
    issues = validate_schedule(schedule)
    print("\n── Internal checks ──")
    for name, count in issues.items():
        print(f"  {'✓' if count == 0 else '✗'}  {name:<40}: {count}")

    try:
        from constraints import is_valid, csp_validate
        print("\n── Authoritative check (constraints.py) ──")
        print(f"  is_valid() → {'✓ VALID' if is_valid(schedule) else '✗ INVALID'}")
        violations = csp_validate(schedule)
        if violations:

            for v in violations:

                print(f"    ✗ {v}")

        else:

            print("  csp_validate() → no violations ✓")

    except ImportError:

        print("  (constraints.py not found — skipping)")

    # ══════════════════════════════════════════════════════════════

    # 2. SOFT CONSTRAINT BREAKDOWN

    # ══════════════════════════════════════════════════════════════

    print("\n" + "="*52)

    print("  SOFT CONSTRAINTS  (penalty per violation =", PENALTY, ")")

    print("="*52)



    # ── 2a. Rest-day penalty ───────────────────────────────────────

    rest_total = Rest_day_penalty(schedule, teams, penalty=PENALTY)

    rest_violations = rest_total // PENALTY

    print(f"\n── Rest-day penalty (< 6 days between consecutive matches) ──")

    print(f"  Total penalty : {rest_total:>8,.0f}")

    print(f"  Violations    : {rest_violations:>8}")



    # Per-team breakdown

    match_days_map = {"Friday":0,"Saturday":1,"Sunday":2,"Wednesday":3,"Thursday":4}

    for team in teams:

        team_days = []

        for r in schedule.rounds:

            for m in r.matches:

                if m.home.name == team.name or m.away.name == team.name:

                    team_days.append(m.day)

        bad = sum(

            1 for i in range(len(team_days)-1)

            if (7 - match_days_map[team_days[i]] + match_days_map[team_days[i+1]]) < 6

        )

        if bad:

            print(f"    ✗ {team.name:<20} {bad} violation(s)")



    # ── 2b. Derby penalty ─────────────────────────────────────────

    derby_total = Derbies_penalty(schedule, derbies, WEEKENDS, penalty=PENALTY)

    derby_violations = derby_total // PENALTY

    print(f"\n── Derby penalty (derby match not on a weekend) ──")

    print(f"  Total penalty : {derby_total:>8,.0f}")

    print(f"  Violations    : {derby_violations:>8}")



    for r in schedule.rounds:

        for m in r.matches:

            pair = frozenset([m.home.name, m.away.name])

            if pair in derbies and m.day not in WEEKENDS:

                print(f"    ✗ {m.home.name} vs {m.away.name}  scheduled on {m.day}")



    # ── 2c. Successive away penalty ───────────────────────────────

    print(f"\n── Successive away penalty (≥ 3 consecutive away games) ──")

    succ_total = 0

    for team in teams:

        p = successive_away_penalty(team, schedule, penalty=PENALTY)

        succ_total += p

        if p:

            print(f"    ✗ {team.name:<20} penalty = {p}")

    if succ_total == 0:

        print("  No violations ✓")

    print(f"  Total penalty : {succ_total:>8,.0f}")



    # ══════════════════════════════════════════════════════════════

    # 3. COST SUMMARY

    # ══════════════════════════════════════════════════════════════

    travel_km  = compute_total_travel(schedule, dist_matrix)

    total_cost = travel_km + rest_total + derby_total



    print("\n" + "="*52)

    print("  COST SUMMARY")

    print("="*52)

    print(f"  Travel distance   : {travel_km:>10,.1f} km")

    print(f"  Rest-day penalty  : {rest_total:>10,.0f}")

    print(f"  Derby penalty     : {derby_total:>10,.0f}")

    print(f"  Successive away   : {succ_total:>10,.0f}  (info only)")

    print(f"  {'─'*38}")

    print(f"  Total cost        : {total_cost:>10,.1f}")

    print(f"\n  Rounds  : {schedule.total_rounds()}")

    print(f"  Matches : {schedule.total_matches()}")

    print(f"  History : {len(history)} entries "

          f"(first={history[0]:,.1f}  last={history[-1]:,.1f})")



