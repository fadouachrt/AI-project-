import streamlit as st
import plotly.express as px
import time
import csv
import os

import pandas as pd

from simulated_annealing import simulated_annealing
from src.greedy import greedy_schedule
from src.hill_climbing import hill_climbing
from src.data_loader import load_all
from src.Minimize_total import cost_function
from src.schedule import double_round_robin, assign_all_days
from src.csp_solver import csp_solver


# PATHS


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

csv_path     = os.path.join(BASE_DIR, "data", "teams.csv")
derbies_path = os.path.join(BASE_DIR, "data", "derbies.csv")



all_teams, distances = load_all(csv_path)


with open(derbies_path, newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader)
    derbies = {
        frozenset([row[0].strip(), row[1].strip()])
        for row in reader
    }



st.sidebar.header("Settings")

n_teams = st.sidebar.slider(
    "Number of teams",
    min_value=2,
    max_value=len(all_teams),
    value=len(all_teams),
)

selected_teams      = all_teams[:n_teams]               
selected_team_names = [t.name for t in selected_teams]  

initial_schedule = double_round_robin(selected_teams)
initial_schedule = assign_all_days(initial_schedule)


#SA

start = time.time()

best_sa, cost_sa, history_sa = simulated_annealing(
    schedule=initial_schedule,
    distances=distances,
    derbies=derbies,
    weekends=["Friday", "Saturday"],
    teams=selected_teams,      
    T_start=1000000,
    T_min=0.1,
    alpha=0.9,
    max_iteration=50000,
    cost_fn=cost_function,
)

sa_time = time.time() - start


#HC







#Greedy

start = time.time()

best_greedy, cost_greedy, history_greedy = greedy_schedule(
    schedule=initial_schedule,
    weekends=["Friday", "Saturday"],
    derbies=derbies,
    teams= selected_teams,
    dist_matrix    = distances,

)

greedy_time = time.time() - start




N_RUNS = st.sidebar.slider("Number of runs (for box plot)", 5, 20, 10)

sa_costs, greedy_costs= [], []

for _ in range(N_RUNS):
    # SA
    _, cost, _ = simulated_annealing(
        schedule=initial_schedule,
        distances=distances,
        derbies=derbies,
        weekends=["Friday", "Saturday"],
        teams=selected_teams,
        T_start=10000,
        T_min=0.1,
        alpha=0.9994,
        max_iteration=50000,
        cost_fn=cost_function,
    )
    sa_costs.append(cost)

    # Greedy
    _, cost, _ = greedy_schedule(
        schedule=initial_schedule,
        weekends=["Friday", "Saturday"],
        derbies=derbies,
        teams=selected_teams,
        dist_matrix=distances,
    )
    greedy_costs.append(cost)

    # CSP — runs once, always same result (deterministic)
    # so just repeat the same cost N times
   












st.title("Algorithm Comparison")

# Cost comparison bar chart
distance_data = {
    "Algorithm": ["SA", "Greedy"],
    "Cost":      [ cost_sa, cost_greedy],
}

fig_distance = px.bar(
    {"Algorithm": ["HC", "SA", "Greedy"], "Cost": [ cost_sa, cost_greedy]},
    x="Algorithm",
    y="Cost",
    title="Final Cost Comparison",
)
st.plotly_chart(fig_distance)

# Convergence line chart

min_len    = min(len(history_sa), len(history_greedy))
iterations = list(range(1, min_len + 1))

convergence_data = {
    "iteration": iterations,
    #"HC":        history_hc[:min_len],
    "SA":        history_sa[:min_len],
    "Greedy":    history_greedy[:min_len],
}
fig_convergence = px.line(
    convergence_data,
    x     = "iteration",
    y     = ["SA", "Greedy"],
    title = "Convergence Per Iteration",
)
st.plotly_chart(fig_convergence)

# Runtime bar chart
run_time = {
    "Algorithm": ["SA", "Greedy"],
    "Time":      [sa_time, greedy_time],
}

fig_run = px.bar(
    {"Algorithm": [ "SA", "Greedy"], "Time": [ sa_time, greedy_time]},
    x="Algorithm",
    y="Time",
    title="Execution Time (seconds)",
)

st.plotly_chart(fig_run)






box_data = pd.DataFrame({
    "Algorithm": (["SA"] * N_RUNS + 
                  ["Greedy"] * N_RUNS ),
    "Cost":      (sa_costs + greedy_costs),
})

fig_box = px.box(
    box_data,
    x="Algorithm",
    y="Cost",
    title="Cost Distribution per Algorithm (Whisker Plot)",
    points="all",       # show individual run dots too
    color="Algorithm",  # color per algorithm
)
st.plotly_chart(fig_box)

