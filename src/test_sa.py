import math
import random
from copy import deepcopy

# =========================
# 1. Dummy Data
# =========================

teams = ["A", "B", "C", "D"]

# distance matrix (symmetric)
distances = {
    "A": {"B": 10, "C": 20, "D": 30},
    "B": {"A": 10, "C": 25, "D": 15},
    "C": {"A": 20, "B": 25, "D": 10},
    "D": {"A": 30, "B": 15, "C": 10},
}

weekends = {"Friday", "Saturday"}
derbies = {frozenset(["A", "B"])}  # small penalty test


# =========================
# 2. Dummy Schedule Structure
# =========================

def create_dummy_schedule():
    # rounds → matches (very simplified)
    return [
        [
            ("A", "B", "Friday"),
            ("C", "D", "Saturday"),
        ],
        [
            ("A", "C", "Friday"),
            ("B", "D", "Saturday"),
        ],
    ]


# =========================
# 3. Cost Function
# =========================

def cost_function(schedule):
    cost = 0

    for r in schedule:
        for home, away, day in r:

            # travel cost
            cost += distances[home][away]

            # derby penalty if not weekend
            if frozenset([home, away]) in derbies and day not in weekends:
                cost += 50

            # penalty for Friday games (just to force variation)
            if day == "Friday":
                cost += 5

    return cost


# =========================
# 4. Neighbor Generator
# =========================

def swap_matches(schedule):
    new_sched = deepcopy(schedule)

    r1 = random.randint(0, len(new_sched) - 1)
    r2 = random.randint(0, len(new_sched) - 1)

    m1 = random.randint(0, len(new_sched[r1]) - 1)
    m2 = random.randint(0, len(new_sched[r2]) - 1)

    # swap full matches
    new_sched[r1][m1], new_sched[r2][m2] = new_sched[r2][m2], new_sched[r1][m1]

    return new_sched


# =========================
# 5. Simulated Annealing
# =========================

def simulated_annealing(initial_schedule, T=1000, T_min=0.1, alpha=0.99, iterations=1000):

    current = deepcopy(initial_schedule)
    current_cost = cost_function(current)

    best = deepcopy(current)
    best_cost = current_cost

    history = []

    for i in range(iterations):

        neighbor = swap_matches(current)
        neighbor_cost = cost_function(neighbor)

        delta = neighbor_cost - current_cost

        # accept better
        if delta < 0:
            current = neighbor
            current_cost = neighbor_cost

        # accept worse probabilistically
        else:
            if random.random() < math.exp(-delta / T):
                current = neighbor
                current_cost = neighbor_cost

        # update best
        if current_cost < best_cost:
            best = deepcopy(current)
            best_cost = current_cost

        history.append(best_cost)

        # cooling
        T *= alpha
        if T < T_min:
            break

    return best, best_cost, history


# =========================
# 6. RUN TEST
# =========================

if __name__ == "__main__":

    schedule = create_dummy_schedule()

    print("Initial schedule:", schedule)
    print("Initial cost:", cost_function(schedule))

    best, best_cost, history = simulated_annealing(schedule)

    print("\nFinal best cost:", best_cost)
    print("\nFinal schedule:", best)

    print("\nCost evolution:", history[:10], "...")

    # check if SA is actually working
    if best_cost < cost_function(schedule):
        print("\n✅ SA is working correctly (cost improved)")
    else:
        print("\n❌ SA is NOT improving → problem is NOT SA logic")