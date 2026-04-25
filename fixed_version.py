import math
import csv


def transfer_derbies(Derbies):
    return [frozenset([a, b]) for a, b in Derbies]



def Derbies_penalty(schedule, derbies, weekend, penalty=500):

    total = 0

    for r in schedule:
        for (home, away, day) in r:

            match = frozenset([home, away])

            if match in derbies and day not in weekend:
                total += penalty

    return total



def Rest_day_penalty(schedule, teams, penalty=500):

    match_days = {"Friday": 0, "Saturday": 1, "Sunday": 2}
    total = 0

    for team in teams:

        team_match_day = []

        for Round in schedule:
            for (home, away, day) in Round:
                if team == home or team == away:
                    team_match_day.append(day)

        for i in range(len(team_match_day) - 1):

            rest = 7 - match_days[team_match_day[i]] + match_days[team_match_day[i+1]]

            if rest < 6:
                total += penalty

    return total



def haversine(lat1, lon1, lat2, lon2):

    R = 6371

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c



def build_dict_matrix(teams):

    dict_Matric = {}

    for i, home in enumerate(teams):
        for j, away in enumerate(teams):

            if j > i:

                dict_Matric[(away["team"].strip(), home["team"].strip())] = haversine(float(away["latitude"]),float(away["longitude"]),float(home["latitude"]),float(home["longitude"]))

    return dict_Matric



def total_distance(schedule, dist_Matric):

    total = 0

    for Round in schedule:
        for (home, away, day) in Round:
            total += dist_Matric[(away, home)]

    return total



def cost_function(schedule, teams, dict_Matric, derbies, weekend, penalty=500):

    total_cost = 0

    total_cost += total_distance(schedule, dict_Matric)
    total_cost += Rest_day_penalty(schedule, teams, penalty)
    total_cost += Derbies_penalty(schedule, derbies, weekend, penalty)

    return total_cost
