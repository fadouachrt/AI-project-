import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

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
        teams,
        T_start = 15000,
        T_min = 0.1,
        alpha = 0.9997,
        reheat_every  = 4_000,
        reheat_factor = 2.0,
        max_iteration = 30000,
        cost_fn=cost_function
    )
    return teams, distances, best, best_cost


def team_travel_distance(team_name, schedule, dist_matrix):
    """
    Total km traveled by one team across the season.
    Uses the same logic as total_distance() in Minimize_total.py:
    tracks current_position and looks up dist_matrix[from][to].
    Only the away team moves each match.
    """
    current_position = team_name  # team starts at their own stadium
    total = 0.0

    for round_obj in schedule.rounds:
        for match in round_obj.matches:
            if match.away.name == team_name:
                from_city = current_position
                to_city   = match.home.name
                total += dist_matrix[from_city][to_city]
                current_position = match.home.name
            elif match.home.name == team_name:
                # home game — team stays put, no travel
                current_position = match.home.name

    return total


def get_team_route(team_name, schedule):
    """Returns list of (lat, lon) tuples representing the team's travel path."""
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
                if dest != route[-1]:
                    route.append(dest)
                break

    if route[-1] != home_coords:
        route.append(home_coords)

    return route


# ── Run once ────────────────────────────────────────────────
with st.spinner("Optimizing schedule... (first load only)"):
    teams, distances, best, best_cost = run_optimization()

st.title("🏟️ Algerian Ligue 1 – Season Schedule Map")

# ── Compute total travel for all teams ──────────────────────
total_travel_km = sum(
    team_travel_distance(t.name, best, distances) for t in teams
)
avg_travel_km = total_travel_km / len(teams)

col1, col2, col3 = st.columns(3)
col1.metric("Optimized Season Cost", f"{best_cost:,.0f}")
col2.metric("Total Travel (all teams)", f"{total_travel_km:,.0f} km")
col3.metric("Average per Team", f"{avg_travel_km:,.0f} km")

st.divider()

# ── Team selector ────────────────────────────────────────────
team_names = [t.name for t in teams]
selected_team = st.selectbox("Select a team to view its travel route:", team_names)

# ── Distance for selected team using dist_matrix ─────────────
selected_km = team_travel_distance(selected_team, best, distances)
st.metric(f"🚌 {selected_team} — Total Travel Distance", f"{selected_km:,.0f} km")

# ── Map ──────────────────────────────────────────────────────
m = folium.Map(location=[28.0, 2.5], zoom_start=5, tiles="CartoDB dark_matter")

SELECTED_COLOR = "#a0a0b0"   # muted blue-gray for selected team
DEFAULT_COLOR  = "#c8ff00"   # lime green — matches design accent

for team in teams:
    is_selected = team.name == selected_team
    folium.CircleMarker(
        location=[team.lat, team.lon],
        radius=10 if is_selected else 7,
        color=SELECTED_COLOR if is_selected else DEFAULT_COLOR,
        fill=True,
        fill_color=SELECTED_COLOR if is_selected else DEFAULT_COLOR,
        fill_opacity=1.0 if is_selected else 0.7,
        tooltip=team.name,
    ).add_to(m)

route_coords = get_team_route(selected_team, best)

if route_coords:
    folium.PolyLine(
        locations=route_coords,
        color=SELECTED_COLOR,
        weight=2.5,
        opacity=0.9,
        tooltip=f"{selected_team} — {selected_km:,.0f} km total",
    ).add_to(m)

    folium.Marker(
        location=route_coords[0],
        tooltip=f"{selected_team} — Home Stadium",
        icon=folium.Icon(color="gray", icon="home"),
    ).add_to(m)

st_folium(m, width=900, height=520)