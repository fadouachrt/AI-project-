from models import Match, Schedule, Round

def check_one_match_per_round(schedule):
    for r in schedule.rounds:
        teams_seen = set()
        for match in r.matches:
            if match is None:
                continue
            t1 = match.home.name
            t2 = match.away.name
            if t1 in teams_seen or t2 in teams_seen:
                return False
            teams_seen.add(t1)
            teams_seen.add(t2)
    return True


def check_all_pairs_exactly_twice(schedule):
    pair_count = {}
    
    for r in schedule.rounds:
        for match in r.matches:
            if match is None:
                continue
            pair = frozenset({match.home.name, match.away.name})   
            pair_count[pair] = pair_count.get(pair, 0) + 1
    
    teams = [t.name for t in schedule.teams]
    
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            pair = frozenset({teams[i], teams[j]})
            if pair_count.get(pair, 0) != 2:
                return False
    
    return True


def check_home_away_balance(schedule):
    home_count = {}
    away_count = {}
    
    for r in schedule.rounds:
        for match in r.matches:
            if match is None:
                continue
            home = match.home.name
            away = match.away.name
            home_count[home] = home_count.get(home, 0) + 1
            away_count[away] = away_count.get(away, 0) + 1
    
    for team in schedule.teams:
        home = home_count.get(team.name, 0)
        away = away_count.get(team.name, 0)
        if abs(home - away) >= 1:
            return False
    
    return True


def is_partially_valid(schedule):
    # only checks that no team plays more than once per round and that no pair of teams plays more than twice
    for r in schedule.rounds:
        teams_seen = set()
        for m in r.matches:
            if m is None:
                continue
            if m.home.name in teams_seen or m.away.name in teams_seen:
                return False
            teams_seen.add(m.home.name)
            teams_seen.add(m.away.name)
    
    pair_count = {}
    for r in schedule.rounds:
        for m in r.matches:
            if m is None:
                continue
            pair = frozenset({m.home.name, m.away.name})
            pair_count[pair] = pair_count.get(pair, 0) + 1
            if pair_count[pair] > 2:
                return False
    
    return True


def is_valid(schedule):
    return (
        check_one_match_per_round(schedule) and
        check_all_pairs_exactly_twice(schedule) and
        check_home_away_balance(schedule)
    )


def csp_validate(schedule):
    violations = []
    
    for round_index, r in enumerate(schedule.rounds, 1):
        teams_seen = set()
        for match in r.matches:
            if match is None:
                continue
            t1 = match.home.name
            t2 = match.away.name
            
            if t1 in teams_seen:
                violations.append(f"Round {round_index}: Team {t1} plays more than one match.")
            else:
                teams_seen.add(t1)
                
            if t2 in teams_seen:
                violations.append(f"Round {round_index}: Team {t2} plays more than one match.")
            else:
                teams_seen.add(t2)  
    
    pair_counts = {}
    for r in schedule.rounds:
        for match in r.matches:
            if match is None:
                continue
            pair = frozenset({match.home.name, match.away.name})
            pair_counts[pair] = pair_counts.get(pair, 0) + 1
    
    teams = [t.name for t in schedule.teams]
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            pair = frozenset({teams[i], teams[j]})
            count = pair_counts.get(pair, 0)
            if count != 2:
                violations.append(f"Pair {pair} plays {count} times instead of 2.")
    
    home_count = {}
    away_count = {}
    for r in schedule.rounds:
        for match in r.matches:
            if match is None:
                continue
            home_count[match.home.name] = home_count.get(match.home.name, 0) + 1
            away_count[match.away.name] = away_count.get(match.away.name, 0) + 1
    
    for team in schedule.teams:
        home = home_count.get(team.name, 0)
        away = away_count.get(team.name, 0)
        if abs(home - away) >= 1:
            violations.append(f"Team '{team.name}' has unbalanced home/away: plays {home} home vs {away} away")
    
    return violations