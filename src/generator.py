
from models import Match, Schedule


def generate_double_round_robin(teams):
    n = len(teams)
    if n % 2 != 0:
        raise ValueError(f"Need an even number of teams, got {n}")

    if n < 2:
        raise ValueError(f"Need at least 2 teams, got {n}")
    fixed = teams[0]
    rotating = list(teams[1:]) 

    first_leg = []
    for round_num in range(n - 1):
        round_matches = []
        if round_num % 2 == 0:
            round_matches.append(Match(home=fixed, away=rotating[0]))
        else:
            round_matches.append(Match(home=rotating[0], away=fixed))
        for i in range(1, len(rotating) // 2 + 1):
            team_a = rotating[i]           
            team_b = rotating[-(i)]        
            if i % 2 == 0:
                round_matches.append(Match(home=team_a, away=team_b))
            else:
                round_matches.append(Match(home=team_b, away=team_a))

        first_leg.append(round_matches)
        last = rotating.pop()
        rotating.insert(0, last)

    second_leg = []
    for round_matches in first_leg:
        mirrored_round = []
        for match in round_matches:
            mirrored_round.append(Match(home=match.away, away=match.home))
        second_leg.append(mirrored_round)
    all_rounds = first_leg + second_leg

    return Schedule(rounds=all_rounds, teams=list(teams))
