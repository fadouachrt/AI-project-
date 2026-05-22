import random
import time
import copy
import os
import sys

from Minimize_total import cost_function, total_distance
from models import Team, Match, Round, Schedule
from schedule import double_round_robin, assign_all_days
from data_loader import load_all, load_derbies
from Soft_constraints import Rest_day_penalty, Derbies_penalty, successive_away_penalty

DAY_OFFSET = {
    "Friday": 0, "Saturday": 1, "Sunday": 2,
    "Wednesday": 3, "Thursday": 4,
}
REST_MIN = 6
PENALTY  = 500
WEEKENDS = {"Friday", "Saturday"}
STREAK_WEIGHT = 3000

# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------

def _round_travel_cost(round_obj: Round,
                       prev_location: dict,
                       dist_matrix: dict) -> float:
    total = 0.0
    for match in round_obj.matches:
        if match is None:
            continue
        origin = prev_location.get(match.away.name, match.away.name)
        total += dist_matrix.get(origin, {}).get(match.home.name, 0.0)
    return total

def _apply_positions(round_obj: Round, positions: dict) -> dict:
    """Update team locations after a round. Returns new positions dict."""
    updated = dict(positions)          # start from current positions
    for match in round_obj.matches:
        if match is None:
            continue
        # after the match, both teams are at the home city
        updated[match.away.name] = match.home.name
        updated[match.home.name] = match.home.name
    return updated

def _away_streak(team_name: str, ordered_so_far: list) -> int:
    """Count consecutive away games for team_name at the tail of ordered_so_far."""
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

def _round_score(round_obj: Round,
                 ordered_so_far: list,
                 prev_location: dict,
                 dist_matrix: dict) -> float:
    km = _round_travel_cost(round_obj, prev_location, dist_matrix)
    # count how many teams in this round would extend an existing away streak to ≥ 3
    streak_violations = sum(
        1
        for m in round_obj.matches
        if m is not None and _away_streak(m.away.name, ordered_so_far) >= 2
    )
    return km + STREAK_WEIGHT * streak_violations

def _sequence_score(order: list,
                    rounds: list,
                    dist_matrix: dict,
                    teams: list) -> float:
    positions = {t.name: t.name for t in teams}
    ordered_rounds = []
    total = 0.0
    for idx in order:
        r = rounds[idx]
        total += _round_score(r, ordered_rounds, positions, dist_matrix)
        positions = _apply_positions(r, positions)
        ordered_rounds.append(r)
    return total

# ----------------------------------------------------------------------
# phase 2 — round ordering with 2-opt (streak‑aware)
# ----------------------------------------------------------------------

def _greedy_round_order(schedule: Schedule,
                        dist_matrix: dict,
                        teams: list,
                        derbies: set,
                        weekends: set,
                        cost_fn,
                        history: list) -> list:
    rounds = schedule.rounds
    remaining = list(range(len(rounds)))
    ordered = []          # indices in order
    ordered_rounds = []   # Round objects in order
    positions = {t.name: t.name for t in schedule.teams}

    # Phase A: greedy construction
    while remaining:
        best_idx = min(
            remaining,
            key=lambda i: _round_score(rounds[i], ordered_rounds, positions, dist_matrix)
        )
        ordered.append(best_idx)
        ordered_rounds.append(rounds[best_idx])
        positions = _apply_positions(rounds[best_idx], positions)
        remaining.remove(best_idx)

        # record partial cost (for history)
        partial = Schedule(
            rounds=[copy.deepcopy(rounds[i]) for i in ordered],
            teams=schedule.teams
        )
        assign_all_days(partial)
        history.append(round(cost_fn(partial, teams, dist_matrix, derbies, weekends), 2))

    # Phase B: 2‑opt refinement
    best_cost = _sequence_score(ordered, rounds, dist_matrix, schedule.teams)
    improved = True
    while improved:
        improved = False
        for i in range(len(ordered) - 1):
            for j in range(i + 2, len(ordered)):
                candidate = ordered[:i] + ordered[i:j+1][::-1] + ordered[j+1:]
                candidate_cost = _sequence_score(candidate, rounds, dist_matrix, schedule.teams)
                if candidate_cost < best_cost - 1e-6:
                    ordered = candidate
                    best_cost = candidate_cost
                    improved = True
    return ordered

def _apply_round_order(schedule: Schedule, order: list) -> Schedule:
    new_schedule = copy.deepcopy(schedule)
    old_rounds = schedule.rounds
    for new_pos, old_pos in enumerate(order):
        new_round = Round(round_index=new_pos)
        new_round.matches = copy.deepcopy(old_rounds[old_pos].matches)
        new_schedule.rounds[new_pos] = new_round
    return new_schedule

# ----------------------------------------------------------------------
# phase 3 — penalty‑aware day assignment
# ----------------------------------------------------------------------

def _greedy_assign_days(schedule: Schedule,
                        derbies: set,
                        weekends: set,
                        penalty: int) -> Schedule:
    new_schedule = copy.deepcopy(schedule)
    last_absolute_day = {}
    away_streak_count = {}

    for round_obj in new_schedule.rounds:
        matches = round_obj.matches
        days = list(round_obj.days)
        if not matches:
            continue

        def absolute_day(day_label: str) -> int:
            return round_obj.round_index * 7 + DAY_OFFSET.get(day_label, 2)

        def penalty_score(match: Match, day_label: str) -> float:
            score = 0.0
            current_day = absolute_day(day_label)
            for team in (match.home, match.away):
                prev = last_absolute_day.get(team.name)
                if prev is not None and (current_day - prev) < REST_MIN:
                    score += penalty
            if away_streak_count.get(match.away.name, 0) >= 2:
                score += penalty
            pair = frozenset([match.home.name, match.away.name])
            if pair in derbies and day_label not in weekends:
                score += penalty
            return score

        derby_matches = [m for m in matches if frozenset([m.home.name, m.away.name]) in derbies]
        regular_matches = [m for m in matches if frozenset([m.home.name, m.away.name]) not in derbies]
        used_days = []

        def choose_best_day(match: Match, prefer_weekend: bool) -> str:
            weekend_days = [d for d in days if d in weekends and d not in used_days]
            non_weekend_days = [d for d in days if d not in weekends and d not in used_days]
            pool = (weekend_days + non_weekend_days) if prefer_weekend else (non_weekend_days + weekend_days)
            if not pool:
                pool = [d for d in days if d not in used_days] or days
            best_day = min(pool, key=lambda d: penalty_score(match, d))
            used_days.append(best_day)
            return best_day

        assignment = {}
        for match in derby_matches:
            assignment[id(match)] = choose_best_day(match, prefer_weekend=True)
        for match in regular_matches:
            assignment[id(match)] = choose_best_day(match, prefer_weekend=False)

        for match in matches:
            selected_day = assignment.get(id(match), days[0])
            match.day = selected_day
            current_day = absolute_day(selected_day)
            last_absolute_day[match.home.name] = current_day
            last_absolute_day[match.away.name] = current_day
            away_streak_count[match.away.name] = away_streak_count.get(match.away.name, 0) + 1
            away_streak_count[match.home.name] = 0

    return new_schedule

# ----------------------------------------------------------------------
# main greedy_schedule entry point (matches the signature expected by runner)
# ----------------------------------------------------------------------

def greedy_schedule(schedule: Schedule,
                    derbies: set,
                    weekends: set,
                    teams: list,
                    dist_matrix: dict,
                    seed: int = 42,
                    verbose: bool = False,
                    cost_fn=None) -> tuple:
    """
    Returns (schedule, best_cost, history) — same signature as SA.
    """
    if cost_fn is None:
        cost_fn = cost_function

    random.seed(seed)
    t0 = time.time()
    history = []

    # Phase 1: already have a schedule (double round‑robin with days assigned)
    base = assign_all_days(double_round_robin(teams))

    # Phase 2: streak‑aware round ordering (history filled inside)
    order = _greedy_round_order(base, dist_matrix, teams, derbies, weekends, cost_fn, history)
    ordered_schedule = _apply_round_order(base, order)

    # Phase 3: penalty‑aware day assignment
    final_schedule = _greedy_assign_days(ordered_schedule, derbies, weekends, PENALTY)
    best_cost = cost_fn(final_schedule, teams, dist_matrix, derbies, weekends)

    # overwrite last history point with true final cost
    if history:
        history[-1] = round(best_cost, 2)

    if verbose:
        elapsed = time.time() - t0
        print(f"[greedy] rounds={final_schedule.total_rounds()} | "
              f"travel={best_cost:,.1f} | time={elapsed:.4f}s")

    return final_schedule, best_cost, history