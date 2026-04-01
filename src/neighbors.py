"""
Neighbor Functions for Local Search.

Three types of moves that produce a slightly modified (neighbor) schedule:
  1. swap_matches_in_round — swap two matches within the same round
  2. swap_rounds           — swap the positions of two entire rounds
  3. swap_home_away         flip home/away for a match (and its mirror)

Each function takes a schedule, applies ONE small change, and returns
a NEW schedule (the original is not modified).
Only uses loops, random, and copy — no AI logic.
"""

import random
import copy
from models import Match, Schedule


def _deep_copy_schedule(schedule):
    """Create a deep copy of a schedule so we don't modify the original."""
    new_rounds = []
    for round_matches in schedule.rounds:
        new_round = []
        for match in round_matches:
            new_round.append(Match(home=match.home, away=match.away))
        new_rounds.append(new_round)
    return Schedule(rounds=new_rounds, teams=list(schedule.teams))


# =========================================================
# MOVE 1: Swap two teams between two matches in one round
# =========================================================
def swap_matches_in_round(schedule):
    """
    Pick a random round. Pick two random matches in that round.
    Swap the away teams between them.

    Before:
        Match A:  X 🏠 vs Y       Match B:  W 🏠 vs Z
    After:
        Match A:  X 🏠 vs Z       Match B:  W 🏠 vs Y

    This changes who travels where, which can reduce total travel.
    The round remains valid (each team still plays exactly once).

    Returns:
        (new_schedule, description_of_move)
    """
    new_schedule = _deep_copy_schedule(schedule)

    # Pick a random round
    round_idx = random.randint(0, len(new_schedule.rounds) - 1)
    round_matches = new_schedule.rounds[round_idx]

    # Need at least 2 matches to swap
    if len(round_matches) < 2:
        return new_schedule, "No swap possible (round has < 2 matches)"

    # Pick two different random matches
    idx_a, idx_b = random.sample(range(len(round_matches)), 2)
    match_a = round_matches[idx_a]
    match_b = round_matches[idx_b]

    # Swap the away teams
    match_a.away, match_b.away = match_b.away, match_a.away

    description = (
        f"Round {round_idx + 1}: "
        f"swapped away teams between match {idx_a + 1} and match {idx_b + 1}"
    )

    return new_schedule, description


# =========================================================
# MOVE 2: Swap two entire rounds
# =========================================================
def swap_rounds(schedule):
    """
    Pick two random rounds and swap their positions in the calendar.

    Before:
        Round 3: [A vs B, C vs D]     Round 7: [E vs F, G vs H]
    After:
        Round 3: [E vs F, G vs H]     Round 7: [A vs B, C vs D]

    This changes the ORDER in which matches happen, affecting
    the travel sequence for every team.

    Returns:
        (new_schedule, description_of_move)
    """
    new_schedule = _deep_copy_schedule(schedule)

    # Need at least 2 rounds to swap
    if len(new_schedule.rounds) < 2:
        return new_schedule, "No swap possible (< 2 rounds)"

    # Pick two different random rounds
    idx_a, idx_b = random.sample(range(len(new_schedule.rounds)), 2)

    # Swap the entire rounds
    new_schedule.rounds[idx_a], new_schedule.rounds[idx_b] = (
        new_schedule.rounds[idx_b], new_schedule.rounds[idx_a]
    )

    description = f"Swapped Round {idx_a + 1} ↔ Round {idx_b + 1}"

    return new_schedule, description


# =========================================================
# MOVE 3: Swap home/away for one match + its mirror
# =========================================================
def swap_home_away(schedule):
    """
    Pick a random match. Flip its home/away assignment.
    Then find the mirror match (the same pair in the other leg)
    and flip that too, to keep the double round-robin valid.

    Before:
        Round 2:   A 🏠 vs B      (A hosts B)
        Round 17:  B 🏠 vs A      (B hosts A — the mirror)
    After:
        Round 2:   B 🏠 vs A      (B hosts A)
        Round 17:  A 🏠 vs B      (A hosts B)

    This changes which stadium is used, affecting travel distances.

    Returns:
        (new_schedule, description_of_move)
    """
    new_schedule = _deep_copy_schedule(schedule)

    # Pick a random round and a random match
    round_idx = random.randint(0, len(new_schedule.rounds) - 1)
    match_idx = random.randint(0, len(new_schedule.rounds[round_idx]) - 1)

    target_match = new_schedule.rounds[round_idx][match_idx]
    original_home = target_match.home
    original_away = target_match.away

    # Flip this match
    target_match.home, target_match.away = target_match.away, target_match.home

    # Find and flip the mirror match (same pair, opposite home/away)
    # The mirror is the match where original_away hosts original_home
    mirror_found = False
    for r_idx, round_matches in enumerate(new_schedule.rounds):
        if r_idx == round_idx:
            continue  # skip the round we already changed
        for match in round_matches:
            if match.home == original_away and match.away == original_home:
                # This is the mirror  flip it too
                match.home, match.away = match.away, match.home
                mirror_found = True
                break
        if mirror_found:
            break

    description = (
        f"Round {round_idx + 1}: flipped {original_home} 🏠 vs {original_away} "
        f"→ {original_away} 🏠 vs {original_home}"
    )
    if mirror_found:
        description += f" (+ mirror in Round {r_idx + 1})"

    return new_schedule, description


# =========================================================
# RANDOM NEIGHBOR: Pick one of the three moves at random
# =========================================================
def random_neighbor(schedule):
    """
    Apply a random move to produce a neighbor schedule.

    Picks one of the three move types with equal probability.

    Returns:
        (new_schedule, description_of_move)
    """
    moves = [swap_matches_in_round, swap_rounds, swap_home_away]
    chosen_move = random.choice(moves)
    return chosen_move(schedule)
