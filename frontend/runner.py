"""
Unified frontend adapter for the algorithms in src/.

Every runner returns: (rounds_display, stats_dict, elapsed).
"""
import asyncio
import csv
import os
import sys
import time


FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(FRONTEND_DIR, ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

for path in (SRC_DIR, PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from data_loader import load_all
from schedule import double_round_robin, assign_all_days
from Minimize_total import cost_function, total_distance
from Soft_constraints import (
    Rest_day_penalty,
    Derbies_penalty,
    successive_away_penalty,
)
from greedy import greedy_schedule
from HC import hill_climbing
from simulated_annealing import simulated_annealing
from csp_solver import csp_solver


TEAMS_CSV = os.path.join(DATA_DIR, "teams.csv")
DERBIES_CSV = os.path.join(DATA_DIR, "derbies.csv")
WEEKEND = {"Friday", "Saturday"}
PENALTY = 500

SA_PARAMS = {
    "T_start": 8000,
    "T_min": 0.1,
    "alpha": 0.9997,
    "max_iteration": 30000,
    "reheat_every": 4000,
    "reheat_factor": 2.0,
}

HC_PARAMS = {
    "penalty": PENALTY,
    "max_restarts": 5,
    "max_iterations": 200,
    "n_samples": 50,
    "max_sideways": 20,
    "tabu_size": 20,
    "verbose": False,
}


_teams_obj, _distances = load_all(TEAMS_CSV)

_derby_set = set()
with open(DERBIES_CSV, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        _derby_set.add(frozenset([row["team_a"].strip(), row["team_b"].strip()]))

_team_meta = {}
with open(TEAMS_CSV, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        name = row["team"].strip()
        _team_meta[name] = {
            "stadium": row["stadium"].strip(),
            "city": row["city"].strip(),
            "lat": float(row["latitude"]),
            "lon": float(row["longitude"]),
        }


def get_all_teams():
    return _teams_obj


def get_team_meta():
    return _team_meta


def get_derby_set():
    return _derby_set


def _round_date(r_idx, n_teams):
    from datetime import date, timedelta

    base = date(2025, 10, 3)
    return (base + timedelta(weeks=r_idx)).strftime("%d - %m - %y")


def _build_initial_schedule(teams_slice):
    return assign_all_days(double_round_robin(teams_slice))


def _schedule_obj_to_display(schedule_obj, n_teams):
    out = []
    for round_obj in schedule_obj.rounds:
        matches = []
        for match in round_obj.matches:
            if match is None:
                continue

            meta = _team_meta.get(match.home.name, {})
            matches.append({
                "home": match.home.name,
                "away": match.away.name,
                "day": match.day or "Friday",
                "home_stadium": meta.get("stadium", "-"),
                "home_city": meta.get("city", "-"),
                "is_derby": frozenset([match.home.name, match.away.name]) in _derby_set,
            })

        out.append({
            "round": round_obj.round_index + 1,
            "date": _round_date(round_obj.round_index, n_teams),
            "matches": matches,
        })

    return out


def _stats_from_schedule_obj(schedule_obj, teams_slice):
    distance = total_distance(schedule_obj, _distances, teams_slice)
    rest_penalty = Rest_day_penalty(schedule_obj, teams_slice, 300)
    derby_penalty = Derbies_penalty(schedule_obj, _derby_set, WEEKEND, 600)
    away_penalty = sum(
        successive_away_penalty(team, schedule_obj, 900)
        for team in teams_slice
    )
    cost = cost_function(
        schedule_obj,
        teams_slice,
        _distances,
        _derby_set,
        WEEKEND,
        
    )

    rest_violations = rest_penalty // 300
    derby_violations = derby_penalty // 600
    away_violations = away_penalty // 900

    return {
        "distance": round(distance, 1),
        "cost": round(cost, 1),
        "initial_cost": None,
        "rest_violations": rest_violations,
        "derbies_on_weekday": derby_violations,
        "successive_away_violations": away_violations,
        "violations": rest_violations + derby_violations + away_violations,
    }


def _percent_improvement(initial_value, final_value):
    if initial_value in (None, 0):
        return 0.0
    return round((initial_value - final_value) / initial_value * 100, 1)


def _attach_baseline(stats, initial_stats):
    stats["initial"] = initial_stats
    stats["initial_cost"] = initial_stats["cost"]
    stats["cost_improvement_pct"] = _percent_improvement(initial_stats["cost"], stats["cost"])
    stats["distance_improvement_pct"] = _percent_improvement(initial_stats["distance"], stats["distance"])
    stats["violation_improvement_pct"] = _percent_improvement(initial_stats["violations"], stats["violations"])
    return stats


async def run_greedy(n_teams: int):
    teams_slice = _teams_obj[:n_teams]
    initial = _build_initial_schedule(teams_slice)
    initial_stats = _stats_from_schedule_obj(initial, teams_slice)
    start = time.perf_counter()

    result = await asyncio.to_thread(
        greedy_schedule,
        initial,
        _derby_set,
        WEEKEND,
        teams_slice,
        _distances,
        42,
        False,
        cost_function,
    )
    if result is None:
        raise RuntimeError("Greedy returned no result")

    best, _best_cost, _history = result
    elapsed = time.perf_counter() - start
    stats = _attach_baseline(_stats_from_schedule_obj(best, teams_slice), initial_stats)
    # Greedy history is built from partial schedules, so use only full-schedule endpoints.
    stats["history"] = [initial_stats["cost"], stats["cost"]]
    return _schedule_obj_to_display(best, n_teams), stats, elapsed


async def run_hill_climbing(n_teams: int):
    teams_slice = _teams_obj[:n_teams]
    initial = _build_initial_schedule(teams_slice)
    initial_stats = _stats_from_schedule_obj(initial, teams_slice)
    start = time.perf_counter()

    best, _best_cost, history = await asyncio.to_thread(
        hill_climbing,
        schedule=initial,
        distances=_distances,
        derbies=_derby_set,
        weekends=WEEKEND,
        teams=teams_slice,
        cost_fn=cost_function,
        **HC_PARAMS,
    )

    elapsed = time.perf_counter() - start
    stats = _attach_baseline(_stats_from_schedule_obj(best, teams_slice), initial_stats)
    stats["history"] = [initial_stats["cost"]] + [round(value, 1) for value in history]
    return _schedule_obj_to_display(best, n_teams), stats, elapsed


async def run_simulated_annealing(n_teams: int):
    teams_slice = _teams_obj[:n_teams]
    initial = _build_initial_schedule(teams_slice)
    initial_stats = _stats_from_schedule_obj(initial, teams_slice)
    start = time.perf_counter()

    best, _best_cost, history = await asyncio.to_thread(
        simulated_annealing,
        schedule=initial,
        distances=_distances,
        derbies=_derby_set,
        weekends=WEEKEND,
        teams=teams_slice,
        cost_fn=cost_function,
        **SA_PARAMS,
    )

    elapsed = time.perf_counter() - start
    stats = _attach_baseline(_stats_from_schedule_obj(best, teams_slice), initial_stats)
    stats["history"] = [initial_stats["cost"]] + [round(value, 1) for value in history]
    return _schedule_obj_to_display(best, n_teams), stats, elapsed


async def run_csp(n_teams: int):
    teams_slice = _teams_obj[:n_teams]
    start = time.perf_counter()

    sched = await asyncio.to_thread(csp_solver, teams_slice, 60)
    if sched is None:
        raise RuntimeError("CSP solver returned no schedule")

    elapsed = time.perf_counter() - start
    initial = _build_initial_schedule(teams_slice)
    initial_stats = _stats_from_schedule_obj(initial, teams_slice)
    return (
        _schedule_obj_to_display(sched, n_teams),
        _attach_baseline(_stats_from_schedule_obj(sched, teams_slice), initial_stats),
        elapsed,
    )


ALGO_RUNNERS = {
    "greedy": run_greedy,
    "hill_climbing": run_hill_climbing,
    "simulated_annealing": run_simulated_annealing,
    "csp": run_csp,
}
