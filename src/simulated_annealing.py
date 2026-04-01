import math
import random
from copy import deepcopy

#################### dummy functions just for testing ###################
def get_neighbor(schedule):
    neighbor = deepcopy(schedule)

    # pick two different rounds
    r1, r2 = random.sample(range(len(schedule)), 2)

    # swap them
    neighbor[r1], neighbor[r2] = neighbor[r2], neighbor[r1]

    return neighbor


def compute_cost(schedule, distances):
    cost = 0

    for round_matches in schedule:
        for (home, away) in round_matches:
            cost += distances[(home, away)]

    return cost


distances = {
    ("A", "B"): 10, ("B", "A"): 10,
    ("A", "C"): 20, ("C", "A"): 20,
    ("A", "D"): 30, ("D", "A"): 30,
    ("B", "C"): 15, ("C", "B"): 15,
    ("B", "D"): 25, ("D", "B"): 25,
    ("C", "D"): 35, ("D", "C"): 35
}

schedule = [
    [("A", "B"), ("C", "D")],
    [("A", "C"), ("B", "D")],
    [("A", "D"), ("B", "C")]
]

########################### simulated anealing function ################################
def simulated_anealing(schedule ,cost_func,T_start ,T_min ,alpha ,max_iteartion):
    T = T_start
    current=deepcopy(schedule)
    current_cost = cost_func(current,distances)
    best = deepcopy(current)
    best_cost = cost_func(best,distances)
    it=0
    history = [] #track improvment of cost
    while it < max_iteartion and T > T_min:
        
        neighbor = get_neighbor(current)
        neighbor_cost = cost_func(neighbor,distances)
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


print(simulated_anealing(schedule,compute_cost,50000,1,0.995,100))