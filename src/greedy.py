import random
import time
import copy
import os
import sys
from Minimize_total import cost_function,total_distance;
from models   import Team, Match, Round, Schedule
from schedule import double_round_robin,assign_all_days;
from data_loader import load_all, load_derbies
from Soft_constraints import Rest_day_penalty,Derbies_penalty,successive_away_penalty;
DAY_OFFSET = {
    "Friday": 0,
    "Saturday": 1,
    "Sunday": 2,
    "Wednesday": 3,
    "Thursday": 4,
}

REST_MIN = 6
PENALTY = 500
WEEKENDS = {"Friday", "Saturday"}





def _incremental_travel(round_obj: Round,
                        positions: dict,
                        distances: dict) -> float:
    """
    Compute extra travel if this round is played next.
    """

    total = 0.0

    for match in round_obj.matches:
        if match is None:
            continue

        from_city = positions.get(match.away.name, match.away.name)
        to_city = match.home.name

        total += distances.get(from_city, {}).get(to_city, 0.0)

    return total



def _apply_positions(round_obj: Round,
                     positions: dict) -> dict:
    """
    Update team locations after a round.
    """

    updated = dict(positions)

    for match in round_obj.matches:
        if match is None:
            continue

        updated[match.away.name] = match.home.name
        updated[match.home.name] = match.home.name

    return updated



def _sequence_travel(order: list,
                     rounds: list,
                     distances: dict,
                     teams: list) -> float:
    """
    Compute full travel cost for a round ordering.
    """

    positions = {t.name: t.name for t in teams}
    total = 0.0

    for idx in order:
        total += _incremental_travel(rounds[idx], positions, distances)
        positions = _apply_positions(rounds[idx], positions)

    return total





def _greedy_round_order(schedule: Schedule,
                        distances: dict) -> list:
    """
    Greedy round ordering + 2-opt refinement.
    Returns ordered list of round indices.
    """

    rounds = schedule.rounds
    remaining = list(range(len(rounds)))

    ordered = []

    positions = {t.name: t.name for t in schedule.teams}

    # -----------------------------
    # Phase A: Greedy Construction
    # -----------------------------

    while remaining:

        best_idx = min(
            remaining,
            key=lambda i: _incremental_travel(
                rounds[i],
                positions,
                distances,
            )
        )

        ordered.append(best_idx)

        positions = _apply_positions(
            rounds[best_idx],
            positions,
        )

        remaining.remove(best_idx)

    # -----------------------------
    # Phase B: 2-opt Refinement
    # -----------------------------

    improved = True

    best_cost = _sequence_travel(
        ordered,
        rounds,
        distances,
        schedule.teams,
    )

    while improved:

        improved = False

        for i in range(len(ordered) - 1):

            for j in range(i + 2, len(ordered)):

                candidate = (
                    ordered[:i]
                    + ordered[i:j + 1][::-1]
                    + ordered[j + 1:]
                )

                candidate_cost = _sequence_travel(
                    candidate,
                    rounds,
                    distances,
                    schedule.teams,
                )

                if candidate_cost < best_cost - 1e-6:
                    ordered = candidate
                    best_cost = candidate_cost
                    improved = True

    return ordered



def _apply_round_order(schedule: Schedule,
                       order: list) -> Schedule:
    """
    Rebuild schedule using optimized round order.
    Reindexes rounds correctly.
    """

    new_schedule = copy.deepcopy(schedule)

    old_rounds = schedule.rounds

    for new_position, old_position in enumerate(order):

        new_round = Round(round_index=new_position)

        new_round.matches = copy.deepcopy(
            old_rounds[old_position].matches
        )

        new_schedule.rounds[new_position] = new_round

    return new_schedule



def _greedy_assign_days(schedule: Schedule,
                        derbies: set,
                        weekends: set,
                        penalty: int) -> Schedule:
    """
    Assign match days while minimizing penalties.
    """

    new_schedule = copy.deepcopy(schedule)

    last_absolute_day = {}
    away_streak = {}

    for round_obj in new_schedule.rounds:

        matches = round_obj.matches
        days = list(round_obj.days)

        if not matches:
            continue

        def absolute_day(day_label: str) -> int:
            return (
                round_obj.round_index * 7
                + DAY_OFFSET.get(day_label, 2)
            )

        def penalty_score(match: Match,
                          day_label: str) -> float:

            score = 0.0

            current_day = absolute_day(day_label)

            # Rest-day penalty
            for team in (match.home, match.away):

                previous_day = last_absolute_day.get(team.name)

                if previous_day is not None:

                    if (current_day - previous_day) < REST_MIN:
                        score += penalty

            # Consecutive away penalty
            streak = away_streak.get(match.away.name, 0)

            if streak >= 2:
                score += penalty

            # Derby weekend preference
            pair = frozenset([
                match.home.name,
                match.away.name,
            ])

            if pair in derbies and day_label not in weekends:
                score += penalty

            return score

        def is_derby(match: Match) -> bool:
            return frozenset([
                match.home.name,
                match.away.name,
            ]) in derbies

        derby_matches = [m for m in matches if is_derby(m)]
        regular_matches = [m for m in matches if not is_derby(m)]

        used_days = []

        def choose_best_day(match: Match,
                            prefer_weekend: bool) -> str:

            weekend_days = [
                d for d in days
                if d in weekends and d not in used_days
            ]

            non_weekend_days = [
                d for d in days
                if d not in weekends and d not in used_days
            ]

            available_days = [
                d for d in days
                if d not in used_days
            ]

            if prefer_weekend:
                pool = weekend_days + non_weekend_days
            else:
                pool = non_weekend_days + weekend_days

            if not pool:
                pool = available_days if available_days else days

            best_day = min(
                pool,
                key=lambda d: penalty_score(match, d)
            )

            used_days.append(best_day)

            return best_day

        assignment = {}

        # Derbies first
        for match in derby_matches:
            assignment[id(match)] = choose_best_day(
                match,
                prefer_weekend=True,
            )

        for match in regular_matches:
            assignment[id(match)] = choose_best_day(
                match,
                prefer_weekend=False,
            )

        # Apply assignments
        for match in matches:

            selected_day = assignment.get(id(match), days[0])

            match.day = selected_day

            current_day = absolute_day(selected_day)

            last_absolute_day[match.home.name] = current_day
            last_absolute_day[match.away.name] = current_day

            away_streak[match.away.name] = (
                away_streak.get(match.away.name, 0) + 1
            )

            away_streak[match.home.name] = 0

    return new_schedule



def compute_total_travel(schedule: Schedule,
                         dist_matrix: dict) -> float:
    """
    Compatibility wrapper.
    """

    return round(
        total_distance(
            schedule,
            dist_matrix,
            schedule.teams,
        ),
        2,
    )



def validate_schedule(schedule: Schedule) -> dict:
    """
    Basic schedule validation.
    """

    teams = [t.name for t in schedule.teams]

    n = len(teams)

    issues = {
        "wrong_round_count": 0,
        "wrong_matches_per_round": 0,
        "team_appears_twice_in_round": 0,
        "pair_not_exactly_once": 0,
    }

    if schedule.total_rounds() != (n - 1) * 2:
        issues["wrong_round_count"] = abs(
            schedule.total_rounds() - ((n - 1) * 2)
        )

    pair_count = {}

    for round_obj in schedule.rounds:

        if len(round_obj.matches) != n // 2:
            issues["wrong_matches_per_round"] += 1

        seen = set()

        for match in round_obj.matches:

            if (
                match.home.name in seen
                or match.away.name in seen
            ):
                issues["team_appears_twice_in_round"] += 1

            seen.add(match.home.name)
            seen.add(match.away.name)

            key = (match.home.name, match.away.name)

            pair_count[key] = pair_count.get(key, 0) + 1

    for t1 in teams:
        for t2 in teams:

            if t1 == t2:
                continue

            if pair_count.get((t1, t2), 0) != 1:
                issues["pair_not_exactly_once"] += 1

    return issues



def greedy_schedule(schedule,
                    weekends,
                    derbies,
                    teams: list,
                    dist_matrix: dict,
                    seed: int = 42,
                    verbose: bool = False) -> tuple:
    """
    Compatible advanced greedy scheduler.

    Keeps the SAME interface as the old version
    so teammates' code does not break.
    """

    random.seed(seed)

    t0 = time.time()

    history = []

    # -------------------------------------------------------------------
    # Phase 1: Base Double Round Robin
    # -------------------------------------------------------------------

    base_cost = cost_function(
        schedule,
        teams,
        dist_matrix,
        derbies,
        weekends,
    )

    history.append(base_cost)

    # -------------------------------------------------------------------
    # Phase 2: Greedy Round Ordering
    # -------------------------------------------------------------------

    optimized_order = _greedy_round_order(
        schedule,
        dist_matrix,
    )

    ordered_schedule = _apply_round_order(
        schedule,
        optimized_order,
    )

    ordered_cost = cost_function(
        ordered_schedule,
        teams,
        dist_matrix,
        derbies,
        weekends,
    )

    history.append(ordered_cost)

    # -------------------------------------------------------------------
    # Phase 3: Smart Day Assignment
    # -------------------------------------------------------------------

    final_schedule = _greedy_assign_days(
        ordered_schedule,
        derbies,
        WEEKENDS,
        PENALTY,
    )

    best_cost = cost_function(
        final_schedule,
        teams,
        dist_matrix,
        derbies,
        WEEKENDS,
        PENALTY,
    )

    history.append(best_cost)

    # -------------------------------------------------------------------
    # Verbose Mode
    # -------------------------------------------------------------------

    if verbose:

        elapsed = time.time() - t0

        print(
            f"[greedy] rounds={final_schedule.total_rounds()} | "
            f"travel={best_cost:,.1f} | "
            f"time={elapsed:.4f}s"
        )

    return final_schedule, best_cost, history





if __name__ == "__main__":

    from data_loader import load_all, load_derbies

    print("=" * 60)
    print("ADVANCED GREEDY SCHEDULER")
    print("=" * 60)


    team_candidates = [
        "data/teams.csv",
        "../data/teams.csv",
        "teams.csv",
    ]

    derby_candidates = [
        "data/derbies.csv",
        "../data/derbies.csv",
        "derbies.csv",
    ]

    teams_path = next(
        (p for p in team_candidates if os.path.exists(p)),
        None,
    )

    derby_path = next(
        (p for p in derby_candidates if os.path.exists(p)),
        None,
    )

    if teams_path is None:
        print("ERROR: teams.csv not found")
        raise SystemExit(1)

    teams, dist_matrix = load_all(teams_path)

    derbies = load_derbies(derby_path) if derby_path else set()

    print(f"Loaded {len(teams)} teams")
    print(f"Loaded {len(derbies)} derby pairs")


    schedule, best_cost, history = greedy_schedule(
        teams,
        dist_matrix,
        seed=42,
        verbose=True,
    )

    print("\nHistory:")

    for i, value in enumerate(history):
        print(f"  Step {i + 1}: {value:,.1f}")

    print("\nFinal Cost:")
    print(f"  {best_cost:,.1f}")

    print("\nValidation:")

    issues = validate_schedule(schedule)

    for name, value in issues.items():
        status = "✓" if value == 0 else "✗"
        print(f"  {status} {name}: {value}")

    print("\nDone.")