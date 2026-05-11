from . import Soft_constraints
from .models import Match, Round, Schedule
from .Soft_constraints import (
    Rest_day_penalty,
    Derbies_penalty,
    successive_away_penalty
)
def total_distance(schedule, dist_Matric, teams):
    total = 0
    current_position = {team.name: team.name for team in teams}

    for round_obj in schedule.rounds:
        for match in round_obj.matches:
            from_city = current_position[match.away.name]
            to_city = match.home.name

            total += dist_Matric[from_city][ to_city]

            current_position[match.away.name] = match.home.name
            

    return total



def cost_function(schedule, teams, dict_Matric, derbies, weekend, penalty=500):

    total_cost = 0

    total_cost += total_distance(schedule, dict_Matric, teams)
    total_cost += Rest_day_penalty(schedule, teams, penalty)
    total_cost += Derbies_penalty(schedule, derbies, weekend, penalty)
    for team in teams:
        total_cost+=successive_away_penalty(team, schedule, penalty)

    
    return total_cost
