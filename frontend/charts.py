import streamlit as st
import plotly.express as px
import time
import csv
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from simulated_annealing import simulated_annealing,load_derbies
from greedy import greedy_schedule
# from hill_climbing import hill_climbing
from data_loader import load_all
from Minimize_total import cost_function
from schedule import double_round_robin



# PATHS





all_teams, distances = load_all("data/teams.csv")


derbies= load_derbies("data/derbies.csv")




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


#SA

start = time.time()

best_sa, cost_sa, history_sa = simulated_annealing(
    schedule=initial_schedule,
    distances=distances,
    derbies=derbies,
    weekends={"Friday", "Saturday"},
    teams= selected_teams,    
    T_start=10000,
    T_min=0.1,
    alpha=0.995,
    max_iteration=5000,
    cost_fn=cost_function,
)

sa_time = time.time() - start


#HC

# start = time.time()

# best_hc, cost_hc, history_hc = hill_climbing(
#     schedule=initial_schedule,
#     distances=distances,
#     derbies=derbies,
#     weekends=["Friday", "Saturday"],
#     teams=selected_team_names,      
#     max_iteration=5000,
#     cost_fn=cost_function,
# )

# hc_time = time.time() - start


#Greedy

start = time.time()

best_greedy, cost_greedy, history_greedy = greedy_schedule(
    teams=selected_team_names,      
    dist_matrix=distances,
)

greedy_time = time.time() - start



st.title("Algorithm Comparison")

# Cost comparison
fig_distance = px.bar(
    {"Algorithm": ["HC", "SA", "Greedy"], "Cost": [ cost_sa, cost_greedy]},
    x="Algorithm",
    y="Cost",
    title="Final Cost Comparison",
)
st.plotly_chart(fig_distance)

# Convergence
min_len = min(len(history_sa),  len(history_greedy))
fig_convergence = px.line(
    {
        "iteration": list(range(1, min_len + 1)),
        "SA":     history_sa[:min_len],
        "Greedy": history_greedy[:min_len],
    },
    x="iteration",
    y=[ "SA", "Greedy"],
    title="Convergence Per Iteration",
)
st.plotly_chart(fig_convergence)

# Runtime
fig_run = px.bar(
    {"Algorithm": [ "SA", "Greedy"], "Time": [ sa_time, greedy_time]},
    x="Algorithm",
    y="Time",
    title="Execution Time (seconds)",
)
st.plotly_chart(fig_run)