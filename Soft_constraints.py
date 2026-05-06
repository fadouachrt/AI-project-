def Derbies_penalty(schedule, derbies, weekend, penalty=500):

    total = 0

    for round_obj in schedule.rounds:
        for match in round_obj.matches:

            match_pair = frozenset([match.home, match.away])

            if match_pair in derbies and match.day not in weekend:
                total += penalty

    return total



def Rest_day_penalty(schedule, teams, penalty=500):
match_days = {
        "Friday": 0,
        "Saturday": 1,
        "Sunday": 2
    }
    
    total = 0

    for team in teams:

        team_match_day = []

        for round_obj in schedule.rounds:
            for match in round_obj.matches:

                if team.name == match.home or team.name == match.away:
                    team_match_day.append(match.day)

        for i in range(len(team_match_day) - 1):

            rest = 7 - match_days[team_match_day[i]] + match_days[team_match_day[i + 1]]

            if rest < 6:
                total += penalty

    return total


def total_distance(schedule, dist_Matric, teams):

    total = 0

    current_position = {team.name: team.name for team in teams}

    for round_obj in schedule.rounds:
        for match in round_obj.matches:

            from_city = current_position[match.away]
            to_city = match.home

            total += dist_Matric[(from_city, to_city)]

            current_position[match.away] = match.home
            current_position[match.home] = match.home

    return total




def cost_function(schedule, teams, dict_Matric, derbies, weekend, penalty=500):

    total_cost = 0

    total_cost += total_distance(schedule, dict_Matric, teams)
    total_cost += Rest_day_penalty(schedule, teams, penalty)
    total_cost += Derbies_penalty(schedule, derbies, weekend, penalty)

    return total_cost



def successive_away_penalty(team, schedule, penalty=500):

    total = 0
    counter = 0

    for round_obj in schedule.rounds:
        for match in round_obj.matches:

            if team == match.away:
                counter += 1
            elif team == match.home:
                counter = 0

            if counter >= 3:
                total += penalty
                counter = 0

    return total
