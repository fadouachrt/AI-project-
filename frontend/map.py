import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import streamlit as st
import folium  
from streamlit_folium import st_folium
import pandas as pd
# from src.simulated_annealing import simulated_annealing
# from src.schedule import double_round_robin
# from src.fixed_version import build_dict_matrix
# from src.data_loader import load_teams


teams = pd.read_csv("../data/teams.csv")
# derbies = pd.read_csv("data/derbies.csv")
# def get_team_route(team_name,schedule,teams):
#     route=[]
#     for round in schedule.rounds:
#         matches = round.matches
#         for match in matches :
#             if match.home == team_name:
#                 row = teams[teams["team"] == team_name]
#                 lat = row["latitude"].values[0]
#                 lon = row["longitude"].values[0]
#                 route.append((lat,lon))
#                 break
#             elif match.away == team_name:
#                 opp=match.home
#                 row = teams[teams["team"] == opp]
#                 lat = row["latitude"].values[0]
#                 lon = row["longitude"].values[0]
#                 route.append((lat,lon))
#                 break
#     return route
# teamms = load_teams("data/teams.csv")  
# schedule = double_round_robin(teamms)
# distances=build_dict_matrix(teamms)
# schedule = simulated_annealing(
#         schedule      = schedule,
#         distances     = distances,
#         derbies       = derbies,
#         weekends      =["Friday","Saturday"],
#         teams          = teamms,
#         T_start       = 10000,
#         T_min         = 0.1,
#         alpha         = 0.995,
#         max_iteration = 5000
# )


m = folium.Map(
location=[28.0, 2.5],  # center of Algeria
zoom_start=5,
tiles="CartoDB dark_matter"
)
    
for _, row in teams.iterrows():
    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=8,
        color="#c8ff00",
        fill=True,
        fill_color="#c8ff00",
        fill_opacity=0.8,
        tooltip=row["team"],    # hover text
        popup=row["stadium"]     # click text
    ).add_to(m)

# team_name ="USM"
# if schedule is not None:
#     route_coords = get_team_route(team_name,schedule,teams)
#     folium.PolyLine(
#         locations = route_coords,
#         color="#c8ff00",
#         weight = 2,
#         opacity = 0.7,
#         tooltip =f"{team_name}travel route"
#     ).add_to(m)
st_folium(m, width=700, height=500)

