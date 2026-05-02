import math
import random
from neighbour import generate_one_random_neighbor
from fixed_version import cost_function
from models import Match, Schedule
from copy import deepcopy
from schedule import double_round_robin
from data_loader import load_all,build_distance_matrix
import csv

def simulated_annealing(schedule ,distances ,derbies ,weekends,teams,T_start ,T_min ,alpha ,max_iteration, cost_fn=None):
    T = T_start
    current=deepcopy(schedule)
    current_cost = cost_fn(current,teams,distances,derbies,weekends)
    best = deepcopy(current)
    best_cost = cost_fn(best,teams,distances,derbies,weekends)
    it=0
    history = [] #track improvment of cost
    while it < max_iteration and T > T_min:
        
        neighbor = generate_one_random_neighbor(current)
        neighbor_cost = cost_fn(neighbor,teams,distances,derbies,weekends)
        delta = neighbor_cost - current_cost
        if delta < 0:
            current = deepcopy(neighbor)
            current_cost = neighbor_cost
        else:
            P = math.exp(-delta/T)
            r=random.random()
            if r< P:
                current = deepcopy(neighbor)
                current_cost = neighbor_cost
            else:
                pass
        if current_cost<best_cost:
            best = deepcopy(current)
            best_cost = current_cost
        
        T = T * alpha
        history.append(best_cost)
        it +=1
    
    
    return best , best_cost , history    


if __name__ == "__main__":
    # 1. Load data
    teams_dict, distances = load_all("../data/teams.csv")
    teams = list(teams_dict.keys())

    # 2. Build distances
    distances = build_distance_matrix(teams_dict)

    # 3. Load derbies correctly
    with open("../data/derbies.csv") as f:
        reader = csv.reader(f)
        next(reader)  
        derbies = {frozenset([row[0].strip(), row[1].strip()]) for row in reader}
    # 4. Generate initial schedule
    schedule = double_round_robin(teams)
    
    best, best_cost, history = simulated_annealing(
        schedule = schedule,
        distances = distances,
        derbies = derbies,
        weekends =["Friday","Saturday"],
        teams = teams,
        T_start = 10000,
        T_min = 0.1,
        alpha = 0.995,
        max_iteration = 5000,
        cost_fn=cost_function
    )
    print(f"\nBest schedule found (cost={best_cost}):")
    best.print_schedule()