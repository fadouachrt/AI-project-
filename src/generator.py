"""
Canonical Schedule Generator — Circle Method.

Generates a valid double round-robin schedule where every team
plays every other team exactly twice (once home, once away).
"""

from engine.models import Match, Schedule


def generate_double_round_robin(teams):
    """
    Generate a double round-robin schedule using the Circle Method.

    Algorithm:
        1. Fix teams[0] in place.
        2. Rotate the remaining teams each round.
        3. Pair by "folding": fixed vs first, then ends fold inward.
        4. After N-1 rounds (first leg), mirror all matches (swap home/away)
           to produce the second leg.

    Args:
        teams: List of team names (must have even length).

    Returns:
        Schedule object with 2*(N-1) rounds.
    """
    n = len(teams)

    # We need an even number of teams
    if n % 2 != 0:
        raise ValueError(f"Need an even number of teams, got {n}")

    if n < 2:
        raise ValueError(f"Need at least 2 teams, got {n}")

    # Step 1: Fix the first team, put the rest in a rotating list
    fixed = teams[0]
    rotating = list(teams[1:])  # copy so we don't modify the original

    first_leg = []

    # Step 2: Generate N-1 rounds for the first leg
    for round_num in range(n - 1):
        round_matches = []

        # --- Pair the fixed team with the first rotating team ---
        # Alternate home/away for the fixed team each round
        if round_num % 2 == 0:
            round_matches.append(Match(home=fixed, away=rotating[0]))
        else:
            round_matches.append(Match(home=rotating[0], away=fixed))

        # --- Fold: pair remaining teams from the outside in ---
        # rotating[1] pairs with rotating[-1]
        # rotating[2] pairs with rotating[-2]
        # ... and so on until they meet in the middle
        for i in range(1, len(rotating) // 2 + 1):
            team_a = rotating[i]             # from the left
            team_b = rotating[-(i)]          # from the right (mirror)
            # Alternate who is home
            if i % 2 == 0:
                round_matches.append(Match(home=team_a, away=team_b))
            else:
                round_matches.append(Match(home=team_b, away=team_a))

        first_leg.append(round_matches)

        # Step 3: Rotate the list — last element moves to the front
        # [a, b, c, d, e] → [e, a, b, c, d]
        last = rotating.pop()
        rotating.insert(0, last)

    # Step 4: Create second leg — mirror all matches (swap home ↔ away)
    second_leg = []
    for round_matches in first_leg:
        mirrored_round = []
        for match in round_matches:
            mirrored_round.append(Match(home=match.away, away=match.home))
        second_leg.append(mirrored_round)

    # Combine both legs
    all_rounds = first_leg + second_leg

    return Schedule(rounds=all_rounds, teams=list(teams))
