import streamlit as st
import plotly.express as px
import time
import csv
import os
import pandas as pd


from src.simulated_annealing import simulated_annealing
from src.greedy import greedy_schedule
from src.HC import hill_climbing
from src.data_loader import load_all
from src.Minimize_total import cost_function,total_distance
from src.schedule import double_round_robin, assign_all_days
from src.csp_solver import csp_solver
from src.Soft_constraints import Rest_day_penalty
st.markdown("""
    <style>
    .stApp {
        background-color: white;
    }
    .stPlotlyChart {
        background-color: white;
    }
    </style>
""", unsafe_allow_html=True)


# PATHS

PISTACHIO    = "#72c03f"
DARK_GREEN   = "#387830"
LIGHT_GREEN  = "#80d24d"
SOFT_GREEN   = "#72be40"
FOREST_GREEN = "#3c7a34"
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
initial_distance=total_distance(schedule=initial_schedule, dist_Matric=distances, teams=selected_teams)
initial_cost=cost_function(schedule=initial_schedule, teams=selected_teams, dict_Matric=distances, derbies=derbies, weekend=["Friday", "Saturday"])
st.write("initial_cost:",initial_cost)
st.write("initial_cost:",initial_distance)
#SA
start = time.time()

best_sa, cost_sa, history_sa = simulated_annealing(
    schedule=initial_schedule,
    distances=distances,
    derbies=derbies,
    weekends=["Friday", "Saturday"],
    teams=selected_teams,      
    T_start=8000,
    T_min=0.1,
    alpha=0.9997,
    max_iteration=40000,
    cost_fn=cost_function,
)

sa_time = time.time() - start



#HC
start = time.time()

best_hc, cost_hc, history_hc = hill_climbing(
    schedule=initial_schedule,
    distances=distances,
    derbies=derbies,
    weekends=["Friday", "Saturday"],
    teams=selected_teams,      
    cost_fn=cost_function,
)

hc_time = time.time() - start

print("lengh of HC history is: ",len(history_hc))




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



st.title("Algorithm Comparison")

# Cost comparison bar chart
distance_data = {
    "Algorithm": ["Greedy","HC","SA"],
    "Cost":      [cost_greedy,cost_hc,cost_sa],
}
fig_distance = px.bar(
    distance_data,
    x     = "Algorithm",
    y     = "Cost",
    title = "Final Cost Comparison",
    color_discrete_sequence=[DARK_GREEN],
    template="simple_white",

)
st.plotly_chart(fig_distance)

# Convergence line chart



min_len = min(len(history_hc),len(history_sa))

if min_len == 0:
    st.warning("No convergence history to display. Check that your algorithms return a non-empty history list.")
else:
    iterations = list(range(1, min_len + 1))

    convergence_data = pd.DataFrame({
        "Iteration": iterations,
        "SA":            history_sa[:min_len],
        "HC":            history_hc[:min_len],
    })

    fig_convergence = px.line(
        convergence_data,
        x     = "Iteration",
        y     = ["HC","SA"],
        title = "Convergence Per Iteration",
        labels = {"value": "Cost", "variable": "Algorithm"},
        color_discrete_sequence=[DARK_GREEN,LIGHT_GREEN],
        template="simple_white",

    )
    st.plotly_chart(fig_convergence)

# Runtime bar chart
run_time = {
    "Algorithm": ["Greedy","HC","SA"],
    "Time":      [greedy_time,hc_time,sa_time],
}
fig_run = px.bar(
    run_time,
    x     = "Algorithm",
    y     = "Time",
    title = "Execution Time (seconds)",
    color_discrete_sequence=[DARK_GREEN],
    template="simple_white",

)
st.plotly_chart(fig_run)


hc_dist     = total_distance(schedule=best_hc,     dist_Matric=distances, teams=selected_teams)
sa_dist     = total_distance(schedule=best_sa,     dist_Matric=distances, teams=selected_teams)
greedy_dist = total_distance(schedule=best_greedy, dist_Matric=distances, teams=selected_teams)

dist_data = {
    "Algorithm": ["Greedy","HC","SA"],
    "Distance":  [greedy_dist,hc_dist,sa_dist],
}

fig_dist = px.bar(
    dist_data,
    x     = "Algorithm",
    y     = "Distance",
    title = "Total Distances (Km)",
    color_discrete_sequence=[DARK_GREEN],
    template="simple_white",
)
st.plotly_chart(fig_dist)
fig_distance.update_layout(paper_bgcolor="white", plot_bgcolor="white")
fig_convergence.update_layout(paper_bgcolor="white", plot_bgcolor="white")
fig_run.update_layout(paper_bgcolor="white", plot_bgcolor="white")
fig_dist.update_layout(paper_bgcolor="white", plot_bgcolor="white")


