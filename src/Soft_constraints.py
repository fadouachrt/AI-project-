
from models import Match , Round , Schedule

def Derbies_penalty(schedule, derbies, weekend, penalty=1000):

    total = 0

    for round_obj in schedule.rounds:
        for match in round_obj.matches:


            match_pair = frozenset([match.home.name, match.away.name])


            if match_pair in derbies and match.day not in weekend:
                total += penalty

    return total




def Rest_day_penalty(schedule, teams, penalty=500):

    match_days = {"Friday": 0, "Saturday": 1, "Sunday": 2,"wednesday":3, "Thursday": 4}

    total = 0
    for team in teams:
        team_match_day = []
        for round_obj in schedule.rounds:
            for match in round_obj.matches:

                if team.name == match.home.name or team.name == match.away.name:  # ← .name

                    team_match_day.append(match.day)

        for i in range(len(team_match_day) - 1):
            day_i = match_days[team_match_day[i]]
            day_j = match_days[team_match_day[i + 1]]
            if day_j > day_i:
                rest = day_j - day_i - 1
            else:
                rest = (7 - day_i) + day_j - 1
            if rest < 5 :#6
                total += penalty

    return total
def successive_away_penalty(team, schedule, penalty=7000):
    total = 0
    counter = 0
    for round_obj in schedule.rounds:
        for match in round_obj.matches:
            if team.name == match.away.name:       
                counter += 1
            elif team.name == match.home.name:     
                counter = 0
            if counter >= 3:
                total += penalty
                counter = 0
    return total

