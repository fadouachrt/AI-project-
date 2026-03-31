from models import Match, Schedule

def check_one_match_per_round(schedule):
    for r in schedule.rounds:
        teams_seen = set()

        for match in r:
            t1 = match.home
            t2 = match.away
            if t1 in teams_seen or t2 in teams_seen:
                return False

            teams_seen.add(t1)
            teams_seen.add(t2)

    return True




def check_all_pairs_exactly_twice(schedule):
    pair_count = {}

    for r in schedule.rounds:
        for match in r:
            pair = match.pair()   
            pair_count[pair] = pair_count.get(pair, 0) + 1

    teams = schedule.teams

    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            pair = frozenset({teams[i], teams[j]})

            if pair_count.get(pair, 0) != 2:
                return False

    return True


def check_home_away_balance(schedule):
    home_count = {}
    away_count = {}

 # Count home and away matches for each team
    for r in schedule.rounds:
        for match in r:
            home = match.home
            away = match.away

            home_count[home] = home_count.get(home, 0) + 1
            away_count[away] = away_count.get(away, 0) + 1

    for team in schedule.teams:
        home = home_count.get(team, 0)
        away = away_count.get(team, 0)

        if abs(home - away) >= 1:
            return False

    return True



def is_valid(schedule):
    return (
        check_one_match_per_round(schedule) and
        check_all_pairs_exactly_twice(schedule) and
        check_home_away_balance(schedule)
    )


def csp_validate(schedule):
    violations =[]

    for round_index, r in enumerate(schedule.rounds, 1):
        teams_seen =set()
        for match in r :
            t1 = match.home
            t2 = match.away

            if t1 in teams_seen:
                violations.append(f"Round {round_index}: Team {t1} plays more than one match.")
            else:
                teams_seen.add(t1)

            if t2 in teams_seen:
                violations.append(f"Round {round_index}: Team {t2} plays more than one match.")
            else:
                teams_seen.add(t2)  

   
    pair_counts={}

    for r in schedule.rounds:
        for match in r: 
            pair=match.pair()
            pair_counts[pair] =pair_counts.get(pair,0)+1
    teams=schedule.teams 
    for i in range(len(teams)):
        for j in range(i+1,len(teams)):
            pair=frozenset({teams[i],teams[j]})
            count=pair_counts.get(pair,0)
            if count!=2 :
                violations.append(f"Pair {pair} plays {count} times instead of 2.")


    home_count ={}
    away_count ={}
    for r in schedule.rounds:
        for match in r:
            home_count[match.home] = home_count.get(match.home, 0) + 1
            away_count[match.away] = away_count.get(match.away, 0) + 1

    for team in schedule.teams:
        home = home_count.get(team, 0)
        away = away_count.get(team, 0)
        if abs(home - away) >= 1:
            violations.append(f"Team '{team}' has unbalanced home/away: it plays  {home} home vs {away} away")

    return violations        
