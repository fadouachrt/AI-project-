import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import math
import streamlit as st
import folium
from streamlit_folium import st_folium
from simulated_annealing import simulated_annealing, load_derbies
from schedule import double_round_robin, assign_all_days
from data_loader import load_all
from Minimize_total import cost_function


@st.cache_resource
def run_optimization():
    teams, distances = load_all("data/teams.csv")
    derbies = load_derbies("data/derbies.csv")
    WEEKEND_DAYS = {"Friday", "Saturday"}
    schedule = double_round_robin(teams)
    schedule = assign_all_days(schedule)
    best, best_cost, history = simulated_annealing(
        schedule, distances, derbies, WEEKEND_DAYS,
        teams, 10000, 0.1, 0.999, 20000, cost_function
    )
    return teams, best, best_cost


def get_team_route(team_name, schedule):
    home_coords = None
    for round_obj in schedule.rounds:
        for match in round_obj.matches:
            if match.home.name == team_name:
                home_coords = (match.home.lat, match.home.lon)
                break
            elif match.away.name == team_name:
                home_coords = (match.away.lat, match.away.lon)
                break
        if home_coords:
            break

    if not home_coords:
        return []

    route = [home_coords]

    for round_obj in schedule.rounds:
        for match in round_obj.matches:
            if match.home.name == team_name or match.away.name == team_name:
                dest = (match.home.lat, match.home.lon)
                # only append if location actually changed
                if dest != route[-1]:
                    route.append(dest)
                break

    if route[-1] != home_coords:
        route.append(home_coords)

    return route


# ── Run once ────────────────────────────────────────────────
with st.spinner("Optimizing schedule... (first load only)"):
    teams, best, best_cost = run_optimization()

st.title("🏟️ Algerian Ligue 1 – Season Schedule Map")
st.metric("Optimized Season Cost", f"{best_cost:,.0f} km")

# ── Team selector ────────────────────────────────────────────
team_names = [t.name for t in teams]
selected_team = st.selectbox("Select a team to view its travel route:", team_names)

# ── Build map ────────────────────────────────────────────────
m = folium.Map(location=[28.0, 2.5], zoom_start=5, tiles="CartoDB dark_matter")

# Draw all team stadiums
for team in teams:
    folium.CircleMarker(
        location=[team.lat, team.lon],
        radius=8,
        color="#c8ff00",
        fill=True,
        fill_color="#c8ff00",
        fill_opacity=0.8,
        tooltip=team.name,
    ).add_to(m)

# Draw selected team's route
route_coords = get_team_route(selected_team, best)
# st.write(f"Total route points: {len(route_coords)}")
# st.write(route_coords)

# st.write("=== Matches per round ===")
# for round_obj in best.rounds:
#     for match in round_obj.matches:
#         if match.home.name == selected_team or match.away.name == selected_team:
#             st.write(f"Round {round_obj.round_index+1}: {match.home.name} vs {match.away.name} → stadium: ({match.home.lat}, {match.home.lon})")

if route_coords:
    folium.PolyLine(
        locations=route_coords,
        color="#ff4444",
        weight=2,
        opacity=0.8,
        # tooltip=f"{selected_team} — total travel: {total_km:,.0f} km"
    ).add_to(m)

    # Mark home stadium
    folium.Marker(
        location=route_coords[0],
        tooltip=f"{selected_team} — Home Stadium",
        icon=folium.Icon(color="red", icon="home")
    ).add_to(m)

    # st.info(f"🚌 **{selected_team}** travels **{total_km:,.0f} km** across the season ({len(route_coords)-1} trips)")

st_folium(m, width=900, height=550)