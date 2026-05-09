import streamlit as st
import plotly.express as px
import time
import csv

from src.simulate_anealing import simulated_annealing
from src.greedy import greedy_schedule
from src.hill_climbing import hill_climbing
from src.data_loader import load_all          # load_all returns (teams, dist_matrix, flat_matrix)
from src.Minimize_total import cost_function
from src.schedule import double_round_robin


teams, distances, flat_distances = load_all("../data/teams.csv")


team_names = [t.name for t in teams]


with open("../data/derbies.csv") as f:
    reader = csv.reader(f)
    next(reader)  # skip header
    derbies = {
        frozenset([row[0].strip(), row[1].strip()])
        for row in reader
    }

team_names = [t.name for t in teams]

# just to control
st.sidebar.header("Settings")
n_teams = st.sidebar.slider(
    "Number of teams",
    min_value=2,
    max_value=len(team_names),
    value=len(team_names),   
)
team_names = team_names[:n_teams]   

initial_schedule = double_round_robin(team_names)

#Simulated Annealing 
start = time.time()
best_sa, cost_sa, history_sa = simulated_annealing(
    schedule      = initial_schedule,
    distances     = distances,
    derbies       = derbies,
    weekends      = ["Friday", "Saturday"],
    teams         = team_names,
    T_start       = 10000,
    T_min         = 0.1,
    alpha         = 0.995,
    max_iteration = 5000,
    cost_fn       = cost_function,
)
sa_time = time.time() - start

#Hill Climbing 
start = time.time()
best_hc, cost_hc, history_hc = hill_climbing(
    schedule      = initial_schedule,
    distances     = distances,
    derbies       = derbies,
    weekends      = ["Friday", "Saturday"],
    teams         = team_names,
    max_iteration = 5000,
    cost_fn       = cost_function,
)
hc_time = time.time() - start

# Greedy
start = time.time()
best_greedy, cost_greedy, history_greedy = greedy_schedule(
    schedule      = initial_schedule,
    distances     = distances,
    derbies       = derbies,
    weekends      = ["Friday", "Saturday"],
    teams         = team_names,
    max_iteration = 5000,
    cost_fn       = cost_function,
)
greedy_time = time.time() - start


st.title("Algorithm Comparison")

# Cost comparison bar chart
distance_data = {
    "Algorithm": ["HC", "SA", "Greedy"],
    "Cost":      [cost_hc, cost_sa, cost_greedy],
}
fig_distance = px.bar(
    distance_data,
    x     = "Algorithm",
    y     = "Cost",
    title = "Final Cost Comparison",
)
st.plotly_chart(fig_distance)

# Convergence line chart

min_len    = min(len(history_sa), len(history_hc), len(history_greedy))
iterations = list(range(1, min_len + 1))

convergence_data = {
    "iteration": iterations,
    "HC":        history_hc[:min_len],
    "SA":        history_sa[:min_len],
    "Greedy":    history_greedy[:min_len],
}
fig_convergence = px.line(
    convergence_data,
    x     = "iteration",
    y     = ["HC", "SA", "Greedy"],
    title = "Convergence Per Iteration",
)
st.plotly_chart(fig_convergence)

# Runtime bar chart
run_time = {
    "Algorithm": ["HC", "SA", "Greedy"],
    "Time":      [hc_time, sa_time, greedy_time],
}
fig_run = px.bar(
    run_time,
    x     = "Algorithm",
    y     = "Time",
    title = "Execution Time (seconds)",
)
st.plotly_chart(fig_run)
