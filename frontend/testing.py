import streamlit as st
import sys
sys.path.append("src")  # so we can import our algorithms

# ── page config (MUST be first) ──────────────────────
st.set_page_config(
    page_title="Algeria Ligue 1 Scheduler",
    page_icon="⚽",
    layout="wide"
)

# ── session state setup ──────────────────────────────
for key in ["schedule", "history", "runtime", "distance"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ── sidebar ──────────────────────────────────────────
with st.sidebar:
    st.markdown("# ⚽ SPORT\n**LEAGUE SCHEDULER**")
    st.markdown("---")
    st.markdown("### ALGORITHMS")
    algo = st.radio("", ["Greedy Search", "Hill Climbing",
                           "Simulated Annealing", "CSP"])
    st.markdown("### TEAM NUMBER")
    n_teams = st.slider("", 10, 20, 16, 2)
    run = st.button("▶ RUN", use_container_width=True, type="primary")
    st.markdown("---")
    st.markdown("### RESULTS")
    st.metric("Running Time",
        f"{st.session_state.runtime:.2f} s" if st.session_state.runtime else "—")
    st.metric("Travel Distance",
        f"{st.session_state.distance:,.0f} km" if st.session_state.distance else "—")

# ── run algorithm when RUN clicked ───────────────────
if run:
    import time
    from data_loader import load_teams, build_distance_matrix
    from schedule_generator import circle_method
    from simulated_annealing import simulated_annealing
    # ... import other algorithms similarly

    teams = load_teams("data/teams.csv")
    dist = build_distance_matrix(teams)
    initial = circle_method(list(teams.keys()))

    with st.spinner(f"Running {algo}..."):
        t0 = time.time()
        # call the right algorithm based on selection
        if algo == "Simulated Annealing":
            sched, hist = simulated_annealing(initial, dist)
        # ... elif for other algorithms
        st.session_state.schedule = sched
        st.session_state.history  = hist
        st.session_state.runtime  = time.time() - t0

# ── 4 tabs ───────────────────────────────────────────
t1, t2, t3, t4 = st.tabs(["📅 Schedule","🏟️ Teams","📊 Analysis","🗺️ Map"])

with t1:
    from frontend.calendar_page import show_calendar
    show_calendar()         # Rofaida's function

with t4:
    from frontend.map_page import show_map
    show_map()              # YOUR function