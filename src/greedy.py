"""
greedy.py
=========
Author : Fadoua  (Data + Greedy — Project 4)

Strategy — Two-Phase Greedy
---------------------------
A pure pair-picking greedy cannot guarantee valid perfect matchings every
round in a Double Round-Robin.  The correct greedy for sports scheduling:

  Phase 1 — Structure (Circle Method)
      Generate all (n-1)*2 valid rounds.  Every round is a perfect
      matching — each team appears exactly once.  Hard constraints are
      satisfied by construction.

  Phase 2 — Order (Greedy)
      Starting with all teams at home, greedily choose WHICH round to
      schedule next, always picking the round that adds the least total
      away-travel cost.  Tie-break: prefer rounds that give fewer
      additional consecutive-away streaks.

  Phase 3 — Day labels
      Within each chosen round, assign day labels (Fri / Sat / Sun)
      cycling in order.  SA / HC will optimise these labels later.

This is the standard greedy construction for the Traveling Tournament
Problem (TTP) and directly matches the project spec requirement:
"Greedy Search — always picking the match/round that adds the least
travel distance."

Dependencies
------------
  data_loader.py  →  load_all()  /  build_distance_matrix()
"""

import random
import time
from itertools import permutations


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

VALID_DAYS = ["Friday", "Saturday", "Sunday"]


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1  —  Circle Method (internal, used to seed the greedy)
# ─────────────────────────────────────────────────────────────────────────────

def _circle_method(teams: list) -> list:
    """
    Generate all (n-1)*2 valid rounds for a Double Round-Robin via the
    Circle Method.

    The algorithm fixes one team and rotates the remaining n-1 teams to
    produce n-1 rounds (first leg).  The second leg is produced by
    swapping home/away in every match.

    Parameters
    ----------
    teams : list of n team names (n must be even)

    Returns
    -------
    list of (n-1)*2 rounds; each round = list of (home, away) tuples.
    """
    n = len(teams)
    if n % 2 != 0:
        raise ValueError("Number of teams must be even.")

    fixed    = teams[0]
    rotating = list(teams[1:])          # n-1 teams, rotate each round
    n_rounds = n - 1                    # rounds per leg

    first_leg  = []
    second_leg = []

    for r in range(n_rounds):
        circle = [fixed] + rotating     # length n

        pairs = []
        for i in range(n // 2):
            home = circle[i]
            away = circle[n - 1 - i]
            # Alternate to balance home/away advantage
            if (r + i) % 2 == 0:
                pairs.append((home, away))
            else:
                pairs.append((away, home))

        first_leg.append(pairs)
        second_leg.append([(a, h) for h, a in pairs])   # flip legs

        # Rotate: move last element of rotating to front
        rotating = [rotating[-1]] + rotating[:-1]

    return first_leg + second_leg


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2  —  Greedy round ordering
# ─────────────────────────────────────────────────────────────────────────────

def _round_cost(round_matches: list,
                prev_location:  dict,
                dist_matrix:    dict) -> float:
    """
    Total km all away teams travel if this round is scheduled next.

    For every (home, away) in the round:
        cost += dist[ prev_location[away] ][ home ]

    Home teams stay put → 0 added cost.
    """
    total = 0.0
    for home, away in round_matches:
        origin = prev_location.get(away, away)
        total += dist_matrix[origin][home]
    return total


def _away_streak(team: str, ordered_so_far: list) -> int:
    """
    Consecutive away matches for 'team' at the end of ordered_so_far
    (used as tie-break).
    """
    count = 0
    for rnd in reversed(ordered_so_far):
        found_home = any(h == team for h, a in rnd)
        found_away = any(a == team for h, a in rnd)
        if found_home:
            return count
        if found_away:
            count += 1
        else:
            break
    return count


def _greedy_order(all_rounds:   list,
                  teams:         list,
                  dist_matrix:   dict) -> list:
    """
    Greedily order the pre-generated rounds by travel cost.

    At each step: score every remaining round by total away-travel cost.
    Tie-break: prefer the round that minimises additional away streaks.

    Parameters
    ----------
    all_rounds   : list of (n-1)*2 rounds (output of _circle_method)
    teams        : list of all team names
    dist_matrix  : 2-D distance dict

    Returns
    -------
    list of rounds in greedy order (same structure, no day labels)
    """
    remaining     = list(all_rounds)
    ordered       = []
    prev_location = {t: t for t in teams}   # all teams start at home

    while remaining:
        scored = []
        for i, rnd in enumerate(remaining):
            km      = _round_cost(rnd, prev_location, dist_matrix)
            streak  = sum(_away_streak(a, ordered) for _, a in rnd)
            scored.append((km, streak, i))

        scored.sort(key=lambda x: (x[0], x[1]))
        best_i   = scored[0][2]
        best_rnd = remaining.pop(best_i)
        ordered.append(best_rnd)

        # Update locations after this round
        for home, away in best_rnd:
            prev_location[away] = home
            prev_location[home] = home

    return ordered


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3  —  Add day labels
# ─────────────────────────────────────────────────────────────────────────────

def _add_day_labels(ordered_rounds: list) -> list:
    """
    Cycle Friday → Saturday → Sunday across matches within each round.

    Returns
    -------
    list of rounds; each match is now (home, away, day).
    """
    result = []
    for rnd in ordered_rounds:
        labeled = [
            (h, a, VALID_DAYS[i % len(VALID_DAYS)])
            for i, (h, a) in enumerate(rnd)
        ]
        result.append(labeled)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def greedy_schedule(teams:       list,
                    dist_matrix: dict,
                    seed:        int  = 42,
                    verbose:     bool = False) -> list:
    """
    Build a complete Double Round-Robin schedule using a greedy strategy.

    Parameters
    ----------
    teams       : list of team name strings (even length)
    dist_matrix : output of build_distance_matrix()
    seed        : random seed (reproducibility)
    verbose     : print progress if True

    Returns
    -------
    list of (n-1)*2 rounds
        schedule[r] = [(home, away, day), ...]   — n/2 tuples per round
    """
    random.seed(seed)
    start = time.time()

    if verbose:
        print("  [Phase 1] Generating valid rounds via Circle Method ...")
    all_rounds = _circle_method(teams)

    if verbose:
        print(f"    → {len(all_rounds)} rounds, {len(all_rounds[0])} matches each")
        print("  [Phase 2] Greedy ordering by minimum travel distance ...")
    ordered = _greedy_order(all_rounds, teams, dist_matrix)

    if verbose:
        print("  [Phase 3] Assigning day labels (Fri / Sat / Sun) ...")
    schedule = _add_day_labels(ordered)

    if verbose:
        elapsed  = time.time() - start
        total_km = compute_total_travel(schedule, dist_matrix)
        print(f"\n  Completed in {elapsed:.3f}s")
        print(f"  Total travel distance: {total_km:,.1f} km")

    return schedule


def compute_total_travel(schedule: list, dist_matrix: dict) -> float:
    """
    Total km traveled by all teams over the full season.

    Each away team travels from their previous location (wherever they
    were after the previous round) to the current home stadium.

    Returns
    -------
    float  total season km
    """
    all_teams = set()
    for rnd in schedule:
        for h, a, d in rnd:
            all_teams.add(h)
            all_teams.add(a)

    prev  = {t: t for t in all_teams}
    total = 0.0
    for rnd in schedule:
        for h, a, d in rnd:
            total += dist_matrix[prev.get(a, a)][h]
        for h, a, d in rnd:
            prev[a] = h
            prev[h] = h

    return round(total, 2)


def quick_validate(schedule: list, teams: list) -> dict:
    """
    Quick sanity checks.  Returns counts of issues found.
    All values should be 0 for a valid schedule.
    Full validation is done by Sally's constraints.py.
    """
    n        = len(teams)
    n_rounds = (n - 1) * 2
    issues   = {
        "wrong_round_count":        0,
        "wrong_match_count":        0,
        "duplicate_team_in_round":  0,
        "pair_count_errors":        0,
    }

    if len(schedule) != n_rounds:
        issues["wrong_round_count"] = abs(len(schedule) - n_rounds)

    pair_count = {}
    for rnd in schedule:
        if len(rnd) != n // 2:
            issues["wrong_match_count"] += 1
        seen = set()
        for h, a, d in rnd:
            if h in seen or a in seen:
                issues["duplicate_team_in_round"] += 1
            seen.add(h)
            seen.add(a)
            pair_count[(h, a)] = pair_count.get((h, a), 0) + 1

    for t1, t2 in permutations(teams, 2):
        if pair_count.get((t1, t2), 0) != 1:
            issues["pair_count_errors"] += 1

    return issues


# ─────────────────────────────────────────────────────────────────────────────
# Run directly for testing
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.dirname(__file__))
    from data_loader import load_all

    csv_candidates = ["data/teams.csv", "../data/teams.csv", "teams.csv"]
    csv_path = next((p for p in csv_candidates if os.path.exists(p)), None)
    if csv_path is None:
        print("ERROR: teams.csv not found.")
        sys.exit(1)

    print(f"Loading teams from {csv_path} ...")
    teams_dict, dist_matrix = load_all(csv_path)
    teams_list = list(teams_dict.keys())
    print(f"  {len(teams_list)} teams loaded.\n")

    schedule = greedy_schedule(teams_list, dist_matrix, seed=42, verbose=True)

    print("\nRunning quick validation ...")
    issues = quick_validate(schedule, teams_list)
    if all(v == 0 for v in issues.values()):
        print("  ✓ All checks passed — schedule is valid.")
    else:
        for k, v in issues.items():
            if v > 0:
                print(f"  ✗ {k}: {v}")

    total_km = compute_total_travel(schedule, dist_matrix)
    print(f"\n{'='*55}")
    print(f"  Rounds          : {len(schedule)}")
    print(f"  Matches/round   : {len(schedule[0])}")
    print(f"  Total travel km : {total_km:,.1f}")
    print(f"{'='*55}")

    print("\nFirst 3 rounds:")
    for r, rnd in enumerate(schedule[:3]):
        print(f"\n  Round {r+1}:")
        for h, a, d in rnd:
            print(f"    {h:<26} vs  {a:<26} [{d}]")