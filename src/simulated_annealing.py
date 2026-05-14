import math
import random
from neighbour import generate_one_random_neighbor
from Minimize_total import cost_function
from models import Match, Schedule
from copy import deepcopy
from schedule import double_round_robin ,assign_all_days
from data_loader import load_all,build_distance_matrix
import csv



def load_derbies(file_path):
    derbies = set()

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            team_a = row["team_a"]
            team_b = row["team_b"]

            derbies.add(frozenset([team_a, team_b]))

    return derbies

def simulated_annealing(schedule ,distances ,derbies ,weekends,teams,T_start ,T_min ,alpha ,max_iteration, cost_fn=None, reheat_every=2000, reheat_factor=2.0):
    T = T_start
    current=deepcopy(schedule)
    current_cost = cost_fn(current,teams,distances,derbies,weekends)
    best = deepcopy(current)
    best_cost = cost_fn(best,teams,distances,derbies,weekends)
    no_improve_count = 0
    last_best = best_cost
    it=0
    history = [] #track improvment of cost
    while it < max_iteration and T > T_min:

        neighbor = generate_one_random_neighbor(current)
        neighbor_cost = cost_fn(neighbor,teams,distances,derbies,weekends)
        delta = neighbor_cost - current_cost
        if delta < 0:
            current = neighbor
            current_cost = neighbor_cost
        else:
            P = math.exp(-delta/T)
            r=random.random()
            if r< P:
                current = neighbor
                current_cost = neighbor_cost
            else:
                pass
        if current_cost<best_cost:
            best = deepcopy(current)
            best_cost = current_cost
        
        #implement reheat
        # if current_cost < last_best:
        #     last_best = current_cost
        #     no_improve_count = 0
        # else:
        #     no_improve_count += 1

        # if no_improve_count >= reheat_every:
        #     T = min(T * reheat_factor, T_start * 0.1)  # reheat but cap below T_start
        #     no_improve_count = 0
        
        
        if best_cost < last_best:          # track BEST, not current
            last_best = best_cost
            no_improve_count = 0
        else:
            no_improve_count += 1

        if no_improve_count >= reheat_every:
            T = min(T * reheat_factor, T_start * 0.5)  # cap at 50% not 10%
            no_improve_count = 0
            last_best = best_cost  
        T = T * alpha
        history.append(best_cost)
        it +=1    
    
    
    return best , best_cost , history    


if __name__ == "__main__":

    teamms , distances = load_all("../data/teams.csv")
    WEEKEND_DAYS = {"Friday", "Saturday"}
    derbie= load_derbies("../data/derbies.csv")
    
    schedulle = double_round_robin(teamms)
    shechdual = assign_all_days(schedulle)
    print(cost_function(shechdual,teamms,distances,derbie,WEEKEND_DAYS))
    
    best, best_cost, history = simulated_annealing(
        schedule = shechdual,
        distances = distances,
        derbies = derbie,
        weekends = WEEKEND_DAYS,
        teams = teamms,
        T_start = 15000,
        T_min = 0.1,
        alpha = 0.9997,
        reheat_every  = 2_000,
        reheat_factor = 2.0,
        max_iteration = 20000,
        cost_fn=cost_function
    )
    print(f"\nBest schedule found (cost={best_cost}):")
  
    
    

