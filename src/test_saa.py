import random
import matplotlib.pyplot as plt
import copy
from simulated_annealing import simulated_annealing
from Minimize_total import cost_function
from neighbour import generate_one_random_neighbor

from data_loader import load_all
from schedule import generate_schedule
from simulated_annealing import load_derbies


# =========================
# LOAD DATA
# =========================

teams, distances = load_all("../data/teams.csv")

derbies = load_derbies("../data/derbies.csv")

weekend = {"Friday", "Saturday"}

schedule = generate_schedule(teams)


# =========================
# TEST INITIAL COST
# =========================

initial_cost = cost_function(
    schedule,
    teams,
    distances,
    derbies,
    weekend
)

print("\n========== INITIAL COST ==========")
print(initial_cost)


# =========================
# TEST NEIGHBOR FUNCTION
# =========================

print("\n========== TESTING NEIGHBOR ==========")

neighbor = generate_one_random_neighbor(schedule)

neighbor_cost = cost_function(
    neighbor,
    teams,
    distances,
    derbies,
    weekend
)

print("Original cost :", initial_cost)
print("Neighbor cost :", neighbor_cost)
print("Difference    :", neighbor_cost - initial_cost)


# =========================
# MULTIPLE NEIGHBOR TEST
# =========================

print("\n========== MULTIPLE NEIGHBOR TEST ==========")

for i in range(10):

    neighbor = generate_one_random_neighbor(schedule)

    cost = cost_function(
        neighbor,
        teams,
        distances,
        derbies,
        weekend
    )

    print(f"Neighbor {i+1}: {cost}")


# =========================
# RUN SA
# =========================

print("\n========== RUNNING SA ==========")

best, best_cost, history = simulated_annealing(
    schedule=schedule,
    distances=distances,
    derbies=derbies,
    weekends=weekend,
    teams=teams,
    T_start=10000,
    T_min=0.1,
    alpha=0.995,
    max_iteration=5000,
    cost_fn=cost_function
)

print("\n========== FINAL RESULTS ==========")

print("Initial cost :", initial_cost)
print("Best cost    :", best_cost)
print("Improvement  :", initial_cost - best_cost)


# =========================
# PLOT HISTORY
# =========================

plt.figure(figsize=(10, 5))

plt.plot(history)

plt.title("Simulated Annealing Cost Evolution")
plt.xlabel("Iteration")
plt.ylabel("Cost")

plt.grid(True)

plt.show()