import math
import random
from neighbors import random_neighbor, _deep_copy_schedule
from models import Match, Schedule

#################### dummy functions just for testing ###################
DUMMY_DISTANCES = {
    ("A","B"):100, ("B","A"):100,
    ("A","C"):200, ("C","A"):200,
    ("A","D"):300, ("D","A"):300,
    ("B","C"):150, ("C","B"):150,
    ("B","D"):250, ("D","B"):250,
    ("C","D"):350, ("D","C"):350,
}
DUMMY_DERBIES = {frozenset(["A", "B"])}  # A vs B is our test derby


def dummy_cost(schedule, distances, derbies):
    """
    Simple cost: travel distance only (no penalties yet).
    Works with Schedule objects. Replace with Douaa's total_cost() later.
    """
    cost = 0
    for round_matches in schedule.rounds:
        for match in round_matches:
            # Away team travels to home team's city
            cost += distances.get((match.home, match.away), 0)
    return cost

def build_test_schedule():
    """
    Verified 4-team DRR. Every pair meets exactly twice.
    Matches have day labels: cycles Friday/Saturday/Sunday.
    """
    teams = ["A", "B", "C", "D"]
    DAYS  = ["Friday", "Saturday", "Sunday"]
    raw_rounds = [
        [("A","D"), ("B","C")],
        [("A","C"), ("D","B")],
        [("A","B"), ("C","D")],
        [("D","A"), ("C","B")],
        [("C","A"), ("B","D")],
        [("B","A"), ("D","C")],
    ]
    rounds = []
    for rnd in raw_rounds:
        rounds.append([Match(home=h, away=a, day=DAYS[i % 3])
                       for i, (h, a) in enumerate(rnd)])
    return Schedule(rounds=rounds, teams=teams)


########################### simulated anealing function ################################
def simulated_annealing(schedule ,cost_func,distances ,derbies ,T_start ,T_min ,alpha ,max_iteartion):
    T = T_start
    current=_deep_copy_schedule(schedule)
    current_cost = cost_func(current,distances,derbies)
    best = _deep_copy_schedule(current)
    best_cost = cost_func(best,distances)
    it=0
    history = [] #track improvment of cost
    while it < max_iteartion and T > T_min:
        
        neighbor,move_desc = random_neighbor(current)
        neighbor_cost = cost_func(neighbor,distances,derbies)
        delta = neighbor_cost - current_cost
        if delta < 0:
            current = _deep_copy_schedule(neighbor)
            current_cost = neighbor_cost
        else:
            P = math.exp(-delta/T)
            r=random.random()
            if r< P:
                current = _deep_copy_schedule(neighbor)
                current_cost = neighbor_cost
            else:
                pass
        if current_cost<best_cost:
            best = _deep_copy_schedule(current)
            best_cost = current_cost
        
        T = T * alpha
        history.append(best_cost)
        it +=1
    
    
    return best , best_cost , history    


if __name__ == "__main__":
    schedule = build_test_schedule()
    best, best_cost, history = simulated_annealing(
        schedule      = schedule,
        cost_func     = dummy_cost,
        distances     = DUMMY_DISTANCES,
        derbies       = DUMMY_DERBIES,
        T_start       = 10000,
        alpha         = 0.995,
        T_min         = 0.1,
        max_iteration = 5000,
    )
    print(f"\nBest schedule found (cost={best_cost}):")
    best.print_schedule()