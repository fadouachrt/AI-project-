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
    home_team = None
    for round_obj in schedule.rounds:
        for match in round_obj.matches:
            if match.home.name == team_name:
                home_team = match.home
                break
            elif match.away.name == team_name:
                home_team = match.away
                break
        if home_team:
            break

    if not home_team:
        return [], 0

    current = (home_team.lat, home_team.lon)
    route = [current]
    total_dist = 0

    for round_obj in schedule.rounds:
        dest = None
        for match in round_obj.matches:
            if match.home.name == team_name:
                # playing at home → stay at home city
                dest = (match.home.lat, match.home.lon)
                break
            elif match.away.name == team_name:
                # playing away → travel to opponent's city
                dest = (match.home.lat, match.home.lon)
                break

        if dest is None:
            continue  # team has no match this round (shouldn't happen)

        # always compute distance and append, even if staying home
        dlat = current[0] - dest[0]
        dlon = (current[1] - dest[1]) * math.cos(math.radians((current[0] + dest[0]) / 2))
        total_dist += math.sqrt(dlat**2 + dlon**2) * 111

        route.append(dest)
        current = dest

    # return home at end of season
    home_coords = (home_team.lat, home_team.lon)
    if current != home_coords:
        dlat = current[0] - home_coords[0]
        dlon = (current[1] - home_coords[1]) * math.cos(math.radians((current[0] + home_coords[0]) / 2))
        total_dist += math.sqrt(dlat**2 + dlon**2) * 111
        route.append(home_coords)

    return route, total_dist


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
route_coords, total_km = get_team_route(selected_team, best)

if route_coords:
    folium.PolyLine(
        locations=route_coords,
        color="#ff4444",
        weight=2,
        opacity=0.8,
        tooltip=f"{selected_team} — total travel: {total_km:,.0f} km"
    ).add_to(m)

    # Mark home stadium
    folium.Marker(
        location=route_coords[0],
        tooltip=f"{selected_team} — Home Stadium",
        icon=folium.Icon(color="red", icon="home")
    ).add_to(m)

    st.info(f"🚌 **{selected_team}** travels **{total_km:,.0f} km** across the season ({len(route_coords)-1} trips)")

st_folium(m, width=900, height=550)