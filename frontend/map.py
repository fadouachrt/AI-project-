import streamlit as st
import folium  
from streamlit_folium import st_folium
import pandas as pd
col1,col2 = st.columns(2)
with col1:
    st.metric("travel distance ","12,450mk")
with col2:
    st.metric("runtime","2.3s")
    
    
tab_schedule,tab_teams,tab_analysis,tab_map = st.tabs(
    [
    "📅 Schedule",
    "🏟️ Teams",
    "📊 Analysis",
    "🗺️ Map"
    ]
)

with tab_schedule:
    st.header("season schedule")
    #clander grid 

with tab_teams:
    st.header("teams")
    #teams info table

with tab_analysis:
    st.header("analysis")
    #charts 

with tab_map:
    teams = pd.read_csv(".../data/teams.csv")
    m = folium.Map(
    location=[28.0, 2.5],  # center of Algeria
    zoom_start=5,
    tiles="CartoDB dark_matter"
    )
    
    for _,row in teams.iterrows():
        folium.CircleMarker(
            location=[row["lat"],row["lon"]],
            radius=8,
            color="#c8ff00",
            fill = True,
            fill_color="#c8ff00",
            fill_opacity = 0.8,
            tooltip=row["team"],
            popup = row["stadium"]
        ).add_ro(m)
    
    if st.session_state.schedule is not None:
        route_coords = get_team_routr(selected_team,st.session-state_shedule, teams)
    
    st_folium(m, width=700, height=500)
    
