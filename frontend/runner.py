# # # # # """
# # # # # runner.py — unified interface for all 4 algorithms.
# # # # # Every runner returns: (rounds_display, stats_dict, elapsed)
# # # # # """
# # # # # import sys, os, time, csv, random, copy
# # # # # sys.path.insert(0, os.path.dirname(__file__))

# # # # # from models import Match, Round, Schedule
# # # # # from data_loader import load_all
# # # # # from schedule import double_round_robin, assign_all_days
# # # # # from Minimize_total import cost_function, total_distance
# # # # # from Soft_constraints import Rest_day_penalty, Derbies_penalty

# # # # # # greedy and local search
# # # # # from greedy import greedy_schedule
# # # # # from hill_climbing import hill_climbing
# # # # # from simulated_annealing import simulated_annealing

# # # # # # CSP optional – fallback if missing
# # # # # try:
# # # # #     from csp_solver import csp_solver
# # # # #     CSP_AVAILABLE = True
# # # # # except ImportError:
# # # # #     CSP_AVAILABLE = False
# # # # #     def csp_solver(teams, time_limit=60, derbies=None, weekend=None, dist_matrix=None):
# # # # #         return assign_all_days(double_round_robin(teams))

# # # # # # constants
# # # # # DATA_DIR    = os.path.dirname(os.path.abspath(__file__))
# # # # # TEAMS_CSV   = os.path.join(DATA_DIR, "teams.csv")
# # # # # DERBIES_CSV = os.path.join(DATA_DIR, "derbies.csv")
# # # # # WEEKEND     = {"Friday", "Saturday"}

# # # # # _teams_obj, _distances = load_all(TEAMS_CSV)          # list[Team], dict
# # # # # _derby_set = set()
# # # # # with open(DERBIES_CSV, newline="", encoding="utf-8") as f:
# # # # #     for row in csv.DictReader(f):
# # # # #         _derby_set.add(frozenset([row["team_a"].strip(), row["team_b"].strip()]))

# # # # # _team_meta = {}
# # # # # with open(TEAMS_CSV, newline="", encoding="utf-8") as f:
# # # # #     for row in csv.DictReader(f):
# # # # #         n = row["team"].strip()
# # # # #         _team_meta[n] = {
# # # # #             "stadium": row["stadium"].strip(),
# # # # #             "city":    row["city"].strip(),
# # # # #             "lat":     float(row["latitude"]),
# # # # #             "lon":     float(row["longitude"]),
# # # # #         }

# # # # # def get_all_teams(): return _teams_obj
# # # # # def get_team_meta(): return _team_meta
# # # # # def get_derby_set(): return _derby_set

# # # # # # ----------------------------------------------------------------------
# # # # # # helpers to convert Schedule objects → display format
# # # # # # ----------------------------------------------------------------------
# # # # # def _round_date(r_idx, n_teams):
# # # # #     from datetime import date, timedelta
# # # # #     base = date(2025, 10, 3)
# # # # #     return (base + timedelta(weeks=r_idx)).strftime("%d - %m - %y")

# # # # # def _schedule_obj_to_display(schedule_obj, teams_slice, n_teams):
# # # # #     out = []
# # # # #     for r in schedule_obj.rounds:
# # # # #         matches = []
# # # # #         for m in r.matches:
# # # # #             meta = _team_meta.get(m.home.name, {})
# # # # #             matches.append({
# # # # #                 "home":         m.home.name,
# # # # #                 "away":         m.away.name,
# # # # #                 "day":          m.day or "Friday",
# # # # #                 "home_stadium": meta.get("stadium", "—"),
# # # # #                 "home_city":    meta.get("city", "—"),
# # # # #                 "is_derby":     frozenset([m.home.name, m.away.name]) in _derby_set,
# # # # #             })
# # # # #         out.append({
# # # # #             "round":   r.round_index + 1,
# # # # #             "date":    _round_date(r.round_index, n_teams),
# # # # #             "matches": matches,
# # # # #         })
# # # # #     return out

# # # # # def _stats_from_schedule_obj(schedule_obj, teams_slice):
# # # # #     dist  = total_distance(schedule_obj, _distances, teams_slice)
# # # # #     rest  = Rest_day_penalty(schedule_obj, teams_slice, 500)
# # # # #     derby = Derbies_penalty(schedule_obj, _derby_set, WEEKEND, 500)
# # # # #     cost  = dist + rest + derby
# # # # #     return {
# # # # #         "distance":           round(dist, 1),
# # # # #         "cost":               round(cost, 1),
# # # # #         "rest_violations":    rest // 500,
# # # # #         "derbies_on_weekday": derby // 500,
# # # # #         "violations":         (rest // 500) + (derby // 500),
# # # # #     }

# # # # # def _basic_schedule(teams_slice):
# # # # #     """Fallback: basic round-robin with days assigned."""
# # # # #     return assign_all_days(double_round_robin(teams_slice))

# # # # # # ----------------------------------------------------------------------
# # # # # # SAFE RUNNERS – each returns a valid schedule (fallback if algorithm fails)
# # # # # # ----------------------------------------------------------------------
# # # # # def run_greedy(n_teams: int):
# # # # #     teams_slice = _teams_obj[:n_teams]
# # # # #     name_list   = [t.name for t in teams_slice]
# # # # #     sub_dist    = {a: {b: _distances[a][b] for b in name_list} for a in name_list}
# # # # #     t0 = time.perf_counter()
# # # # #     try:
# # # # #         # greedy_schedule(teams: list, dist_matrix: dict, seed, verbose) -> list of rounds
# # # # #         greedy_list = greedy_schedule(name_list, sub_dist, seed=42, verbose=False)
# # # # #         # convert list-of-rounds format to Schedule object via display helper
# # # # #         out = []
# # # # #         for r_idx, rnd in enumerate(greedy_list):
# # # # #             matches = []
# # # # #             for h, a, day in rnd:
# # # # #                 meta = _team_meta.get(h, {})
# # # # #                 matches.append({
# # # # #                     "home":         h,
# # # # #                     "away":         a,
# # # # #                     "day":          day,
# # # # #                     "home_stadium": meta.get("stadium", "—"),
# # # # #                     "home_city":    meta.get("city", "—"),
# # # # #                     "is_derby":     frozenset([h, a]) in _derby_set,
# # # # #                 })
# # # # #             out.append({
# # # # #                 "round":   r_idx + 1,
# # # # #                 "date":    _round_date(r_idx, n_teams),
# # # # #                 "matches": matches,
# # # # #             })
# # # # #         elapsed = time.perf_counter() - t0
# # # # #         # compute stats directly from the greedy list
# # # # #         dist = 0.0
# # # # #         prev = {n: n for n in name_list}
# # # # #         for rnd in greedy_list:
# # # # #             for h, a, day in rnd:
# # # # #                 dist += _distances.get(prev.get(a, a), {}).get(h, 0)
# # # # #                 prev[a] = h; prev[h] = h
# # # # #         derby_viol = sum(
# # # # #             1 for rnd in greedy_list for h, a, day in rnd
# # # # #             if frozenset([h, a]) in _derby_set and day not in WEEKEND
# # # # #         )
# # # # #         stats = {
# # # # #             "distance":           round(dist, 1),
# # # # #             "cost":               round(dist + derby_viol * 500, 1),
# # # # #             "rest_violations":    0,
# # # # #             "derbies_on_weekday": derby_viol,
# # # # #             "violations":         derby_viol,
# # # # #         }
# # # # #         return out, stats, elapsed
# # # # #     except Exception as e:
# # # # #         print(f"⚠️ Greedy failed for n={n_teams}: {e}")
# # # # #         import traceback; traceback.print_exc()
# # # # #         final_schedule = _basic_schedule(teams_slice)
# # # # #         elapsed = time.perf_counter() - t0
# # # # #         return _schedule_obj_to_display(final_schedule, teams_slice, n_teams), \
# # # # #                _stats_from_schedule_obj(final_schedule, teams_slice), elapsed

# # # # # def run_hill_climbing(n_teams: int):
# # # # #     teams_slice = _teams_obj[:n_teams]
# # # # #     initial = _basic_schedule(teams_slice)
# # # # #     t0 = time.perf_counter()
# # # # #     best, best_cost, _ = hill_climbing(
# # # # #         schedule       = initial,
# # # # #         distances      = _distances,
# # # # #         derbies        = _derby_set,
# # # # #         weekends       = WEEKEND,
# # # # #         teams          = teams_slice,
# # # # #         max_restarts   = 2,
# # # # #         max_iterations = 80,
# # # # #         max_sideways   = 10,
# # # # #         cost_fn        = cost_function,
# # # # #         verbose        = False
# # # # #     )
# # # # #     elapsed = time.perf_counter() - t0
# # # # #     return _schedule_obj_to_display(best, teams_slice, n_teams), \
# # # # #            _stats_from_schedule_obj(best, teams_slice), elapsed

# # # # # def run_simulated_annealing(n_teams: int):
# # # # #     teams_slice = _teams_obj[:n_teams]
# # # # #     initial = _basic_schedule(teams_slice)
# # # # #     t0 = time.perf_counter()
# # # # #     best, best_cost, _ = simulated_annealing(
# # # # #         schedule       = initial,
# # # # #         distances      = _distances,
# # # # #         derbies        = _derby_set,
# # # # #         weekends       = WEEKEND,
# # # # #         teams          = teams_slice,
# # # # #         T_start        = 5000,
# # # # #         T_min          = 0.5,
# # # # #         alpha          = 0.997,
# # # # #         max_iteration  = 3000,
# # # # #         cost_fn        = cost_function,
# # # # #     )
# # # # #     elapsed = time.perf_counter() - t0
# # # # #     return _schedule_obj_to_display(best, teams_slice, n_teams), \
# # # # #            _stats_from_schedule_obj(best, teams_slice), elapsed

# # # # # def run_csp(n_teams: int):
# # # # #     teams_slice = _teams_obj[:n_teams]
# # # # #     t0 = time.perf_counter()
# # # # #     try:
# # # # #         sched = csp_solver(
# # # # #             teams       = teams_slice,
# # # # #             time_limit  = 60,
# # # # #             derbies     = _derby_set,
# # # # #             weekend     = WEEKEND,
# # # # #             dist_matrix = _distances
# # # # #         )
# # # # #         if sched is None:
# # # # #             sched = _basic_schedule(teams_slice)
# # # # #     except Exception as e:
# # # # #         print(f"⚠️ CSP failed for n={n_teams}: {e}")
# # # # #         sched = _basic_schedule(teams_slice)
# # # # #     elapsed = time.perf_counter() - t0
# # # # #     return _schedule_obj_to_display(sched, teams_slice, n_teams), \
# # # # #            _stats_from_schedule_obj(sched, teams_slice), elapsed

# # # # # ALGO_RUNNERS = {
# # # # #     "greedy":              run_greedy,
# # # # #     "hill_climbing":       run_hill_climbing,
# # # # #     "simulated_annealing": run_simulated_annealing,
# # # # #     "csp":                 run_csp,
# # # # # }

# # # # """
# # # # runner.py — unified interface for all 4 algorithms.
# # # # Every runner returns: (rounds_display, stats_dict, elapsed)
# # # # """
# # # # import sys, os, time, csv, random, copy
# # # # sys.path.insert(0, os.path.dirname(__file__))

# # # # from models import Match, Round, Schedule
# # # # from data_loader import load_all
# # # # from schedule import double_round_robin, assign_all_days
# # # # from Minimize_total import cost_function, total_distance
# # # # from Soft_constraints import Rest_day_penalty, Derbies_penalty

# # # # # greedy and local search
# # # # from greedy import greedy_schedule
# # # # from hill_climbing import hill_climbing
# # # # from simulated_annealing import simulated_annealing

# # # # # CSP optional – fallback if missing
# # # # try:
# # # #     from csp_solver import csp_solver
# # # #     CSP_AVAILABLE = True
# # # # except ImportError:
# # # #     CSP_AVAILABLE = False
# # # #     def csp_solver(teams, time_limit=60, derbies=None, weekend=None, dist_matrix=None):
# # # #         return assign_all_days(double_round_robin(teams))

# # # # # constants
# # # # DATA_DIR    = os.path.dirname(os.path.abspath(__file__))
# # # # TEAMS_CSV   = os.path.join(DATA_DIR, "teams.csv")
# # # # DERBIES_CSV = os.path.join(DATA_DIR, "derbies.csv")
# # # # WEEKEND     = {"Friday", "Saturday"}

# # # # _teams_obj, _distances = load_all(TEAMS_CSV)          # list[Team], dict
# # # # _derby_set = set()
# # # # with open(DERBIES_CSV, newline="", encoding="utf-8") as f:
# # # #     for row in csv.DictReader(f):
# # # #         _derby_set.add(frozenset([row["team_a"].strip(), row["team_b"].strip()]))

# # # # _team_meta = {}
# # # # with open(TEAMS_CSV, newline="", encoding="utf-8") as f:
# # # #     for row in csv.DictReader(f):
# # # #         n = row["team"].strip()
# # # #         _team_meta[n] = {
# # # #             "stadium": row["stadium"].strip(),
# # # #             "city":    row["city"].strip(),
# # # #             "lat":     float(row["latitude"]),
# # # #             "lon":     float(row["longitude"]),
# # # #         }

# # # # def get_all_teams(): return _teams_obj
# # # # def get_team_meta(): return _team_meta
# # # # def get_derby_set(): return _derby_set

# # # # # ----------------------------------------------------------------------
# # # # # helpers to convert Schedule objects → display format
# # # # # ----------------------------------------------------------------------
# # # # def _round_date(r_idx, n_teams):
# # # #     from datetime import date, timedelta
# # # #     base = date(2025, 10, 3)
# # # #     return (base + timedelta(weeks=r_idx)).strftime("%d - %m - %y")

# # # # def _schedule_obj_to_display(schedule_obj, teams_slice, n_teams):
# # # #     out = []
# # # #     for r in schedule_obj.rounds:
# # # #         matches = []
# # # #         for m in r.matches:
# # # #             meta = _team_meta.get(m.home.name, {})
# # # #             matches.append({
# # # #                 "home":         m.home.name,
# # # #                 "away":         m.away.name,
# # # #                 "day":          m.day or "Friday",
# # # #                 "home_stadium": meta.get("stadium", "—"),
# # # #                 "home_city":    meta.get("city", "—"),
# # # #                 "is_derby":     frozenset([m.home.name, m.away.name]) in _derby_set,
# # # #             })
# # # #         out.append({
# # # #             "round":   r.round_index + 1,
# # # #             "date":    _round_date(r.round_index, n_teams),
# # # #             "matches": matches,
# # # #         })
# # # #     return out

# # # # def _stats_from_schedule_obj(schedule_obj, teams_slice):
# # # #     dist  = total_distance(schedule_obj, _distances, teams_slice)
# # # #     rest  = Rest_day_penalty(schedule_obj, teams_slice, 500)
# # # #     derby = Derbies_penalty(schedule_obj, _derby_set, WEEKEND, 500)
# # # #     cost  = dist + rest + derby
# # # #     return {
# # # #         "distance":           round(dist, 1),
# # # #         "cost":               round(cost, 1),
# # # #         "rest_violations":    rest // 500,
# # # #         "derbies_on_weekday": derby // 500,
# # # #         "violations":         (rest // 500) + (derby // 500),
# # # #     }

# # # # def _basic_schedule(teams_slice):
# # # #     """Fallback: basic round-robin with days assigned."""
# # # #     return assign_all_days(double_round_robin(teams_slice))

# # # # # ----------------------------------------------------------------------
# # # # # SAFE RUNNERS – each returns a valid schedule (fallback if algorithm fails)
# # # # # ----------------------------------------------------------------------
# # # # def run_greedy(n_teams: int):
# # # #     teams_slice = _teams_obj[:n_teams]
# # # #     t0 = time.perf_counter()
# # # #     try:
# # # #         # Create a basic schedule first (required by greedy_schedule)
# # # #         base_schedule = _basic_schedule(teams_slice)
# # # #         # greedy_schedule expects: schedule, derbies, weekends, teams, dist_matrix, ...
# # # #         best, best_cost, _ = greedy_schedule(
# # # #             schedule=base_schedule,
# # # #             derbies=_derby_set,
# # # #             weekends=WEEKEND,
# # # #             teams=teams_slice,
# # # #             dist_matrix=_distances,
# # # #             seed=42,
# # # #             verbose=False
# # # #         )
# # # #         elapsed = time.perf_counter() - t0
# # # #         return _schedule_obj_to_display(best, teams_slice, n_teams), \
# # # #                _stats_from_schedule_obj(best, teams_slice), elapsed
# # # #     except Exception as e:
# # # #         print(f"⚠️ Greedy failed for n={n_teams}: {e}")
# # # #         import traceback; traceback.print_exc()
# # # #         final_schedule = _basic_schedule(teams_slice)
# # # #         elapsed = time.perf_counter() - t0
# # # #         return _schedule_obj_to_display(final_schedule, teams_slice, n_teams), \
# # # #                _stats_from_schedule_obj(final_schedule, teams_slice), elapsed

# # # # def run_hill_climbing(n_teams: int):
# # # #     teams_slice = _teams_obj[:n_teams]
# # # #     initial = _basic_schedule(teams_slice)
# # # #     t0 = time.perf_counter()
# # # #     try:
# # # #         best, best_cost, _ = hill_climbing(
# # # #             schedule       = initial,
# # # #             distances      = _distances,
# # # #             derbies        = _derby_set,
# # # #             weekends       = WEEKEND,
# # # #             teams          = teams_slice,
# # # #             max_restarts   = 2,
# # # #             max_iterations = 80,
# # # #             max_sideways   = 10,
# # # #             cost_fn        = cost_function,
# # # #             verbose        = False
# # # #         )
# # # #     except Exception as e:
# # # #         print(f"⚠️ Hill Climbing failed for n={n_teams}: {e}")
# # # #         import traceback; traceback.print_exc()
# # # #         best = initial
# # # #     elapsed = time.perf_counter() - t0
# # # #     return _schedule_obj_to_display(best, teams_slice, n_teams), \
# # # #            _stats_from_schedule_obj(best, teams_slice), elapsed

# # # # def run_simulated_annealing(n_teams: int):
# # # #     teams_slice = _teams_obj[:n_teams]
# # # #     initial = _basic_schedule(teams_slice)
# # # #     t0 = time.perf_counter()
# # # #     try:
# # # #         best, best_cost, _ = simulated_annealing(
# # # #             schedule       = initial,
# # # #             distances      = _distances,
# # # #             derbies        = _derby_set,
# # # #             weekends       = WEEKEND,
# # # #             teams          = teams_slice,
# # # #             T_start        = 5000,
# # # #             T_min          = 0.5,
# # # #             alpha          = 0.997,
# # # #             max_iteration  = 3000,
# # # #             cost_fn        = cost_function,
# # # #         )
# # # #     except Exception as e:
# # # #         print(f"⚠️ Simulated Annealing failed for n={n_teams}: {e}")
# # # #         import traceback; traceback.print_exc()
# # # #         best = initial
# # # #     elapsed = time.perf_counter() - t0
# # # #     return _schedule_obj_to_display(best, teams_slice, n_teams), \
# # # #            _stats_from_schedule_obj(best, teams_slice), elapsed

# # # # def run_csp(n_teams: int):
# # # #     teams_slice = _teams_obj[:n_teams]
# # # #     t0 = time.perf_counter()
# # # #     try:
# # # #         sched = csp_solver(
# # # #             teams       = teams_slice,
# # # #             time_limit  = 60,
# # # #             derbies     = _derby_set,
# # # #             weekend     = WEEKEND,
# # # #             dist_matrix = _distances
# # # #         )
# # # #         if sched is None:
# # # #             sched = _basic_schedule(teams_slice)
# # # #     except Exception as e:
# # # #         print(f"⚠️ CSP failed for n={n_teams}: {e}")
# # # #         import traceback; traceback.print_exc()
# # # #         sched = _basic_schedule(teams_slice)
# # # #     elapsed = time.perf_counter() - t0
# # # #     return _schedule_obj_to_display(sched, teams_slice, n_teams), \
# # # #            _stats_from_schedule_obj(sched, teams_slice), elapsed

# # # # ALGO_RUNNERS = {
# # # #     "greedy":              run_greedy,
# # # #     "hill_climbing":       run_hill_climbing,
# # # #     "simulated_annealing": run_simulated_annealing,
# # # #     "csp":                 run_csp,
# # # # }

# # # """
# # # runner.py — unified interface for all 4 algorithms.
# # # Every runner returns: (rounds_display, stats_dict, elapsed)
# # # """
# # # import sys, os, time, csv, random, copy, traceback
# # # from concurrent.futures import ProcessPoolExecutor, TimeoutError as FuturesTimeoutError

# # # sys.path.insert(0, os.path.dirname(__file__))

# # # from models import Match, Round, Schedule
# # # from data_loader import load_all
# # # from schedule import double_round_robin, assign_all_days
# # # from Minimize_total import cost_function, total_distance
# # # from Soft_constraints import Rest_day_penalty, Derbies_penalty

# # # # greedy and local search
# # # from greedy import greedy_schedule
# # # from hill_climbing import hill_climbing
# # # from simulated_annealing import simulated_annealing

# # # # CSP optional – fallback if missing
# # # try:
# # #     from csp_solver import csp_solver
# # #     CSP_AVAILABLE = True
# # # except ImportError:
# # #     CSP_AVAILABLE = False
# # #     def csp_solver(teams, time_limit=60, derbies=None, weekend=None, dist_matrix=None):
# # #         return assign_all_days(double_round_robin(teams))

# # # # constants
# # # DATA_DIR    = os.path.dirname(os.path.abspath(__file__))
# # # TEAMS_CSV   = os.path.join(DATA_DIR, "teams.csv")
# # # DERBIES_CSV = os.path.join(DATA_DIR, "derbies.csv")
# # # WEEKEND     = {"Friday", "Saturday"}

# # # _teams_obj, _distances = load_all(TEAMS_CSV)          # list[Team], dict
# # # _derby_set = set()
# # # with open(DERBIES_CSV, newline="", encoding="utf-8") as f:
# # #     for row in csv.DictReader(f):
# # #         _derby_set.add(frozenset([row["team_a"].strip(), row["team_b"].strip()]))

# # # _team_meta = {}
# # # with open(TEAMS_CSV, newline="", encoding="utf-8") as f:
# # #     for row in csv.DictReader(f):
# # #         n = row["team"].strip()
# # #         _team_meta[n] = {
# # #             "stadium": row["stadium"].strip(),
# # #             "city":    row["city"].strip(),
# # #             "lat":     float(row["latitude"]),
# # #             "lon":     float(row["longitude"]),
# # #         }

# # # def get_all_teams(): return _teams_obj
# # # def get_team_meta(): return _team_meta
# # # def get_derby_set(): return _derby_set

# # # # ----------------------------------------------------------------------
# # # # helpers to convert Schedule objects → display format
# # # # ----------------------------------------------------------------------
# # # def _round_date(r_idx, n_teams):
# # #     from datetime import date, timedelta
# # #     base = date(2025, 10, 3)
# # #     return (base + timedelta(weeks=r_idx)).strftime("%d - %m - %y")

# # # def _schedule_obj_to_display(schedule_obj, teams_slice, n_teams):
# # #     out = []
# # #     for r in schedule_obj.rounds:
# # #         matches = []
# # #         for m in r.matches:
# # #             if m is None:
# # #                 continue
# # #             meta = _team_meta.get(m.home.name, {})
# # #             matches.append({
# # #                 "home":         m.home.name,
# # #                 "away":         m.away.name,
# # #                 "day":          m.day or "Friday",
# # #                 "home_stadium": meta.get("stadium", "—"),
# # #                 "home_city":    meta.get("city", "—"),
# # #                 "is_derby":     frozenset([m.home.name, m.away.name]) in _derby_set,
# # #             })
# # #         out.append({
# # #             "round":   r.round_index + 1,
# # #             "date":    _round_date(r.round_index, n_teams),
# # #             "matches": matches,
# # #         })
# # #     return out

# # # def _stats_from_schedule_obj(schedule_obj, teams_slice):
# # #     dist  = total_distance(schedule_obj, _distances, teams_slice)
# # #     rest  = Rest_day_penalty(schedule_obj, teams_slice, 500)
# # #     derby = Derbies_penalty(schedule_obj, _derby_set, WEEKEND, 500)
# # #     cost  = dist + rest + derby
# # #     return {
# # #         "distance":           round(dist, 1),
# # #         "cost":               round(cost, 1),
# # #         "rest_violations":    rest // 500,
# # #         "derbies_on_weekday": derby // 500,
# # #         "violations":         (rest // 500) + (derby // 500),
# # #     }

# # # def _basic_schedule(teams_slice):
# # #     """Fallback: basic round-robin with days assigned."""
# # #     return assign_all_days(double_round_robin(teams_slice))

# # # # ----------------------------------------------------------------------
# # # # Safe runner with timeout
# # # # ----------------------------------------------------------------------
# # # def _run_with_timeout(func, args, timeout=30):
# # #     """Run a function in a separate process with timeout."""
# # #     with ProcessPoolExecutor(max_workers=1) as executor:
# # #         future = executor.submit(func, *args)
# # #         try:
# # #             result = future.result(timeout=timeout)
# # #             return result
# # #         except FuturesTimeoutError:
# # #             print(f"⏰ Timeout after {timeout}s for {func.__name__}")
# # #             return None
# # #         except Exception as e:
# # #             print(f"❌ Exception in {func.__name__}: {e}")
# # #             traceback.print_exc()
# # #             return None

# # # def run_greedy(n_teams: int):
# # #     teams_slice = _teams_obj[:n_teams]
# # #     t0 = time.perf_counter()
# # #     try:
# # #         base_schedule = _basic_schedule(teams_slice)
# # #         # greedy_schedule expects (schedule, derbies, weekends, teams, dist_matrix, ...)
# # #         result = _run_with_timeout(
# # #             greedy_schedule,
# # #             (base_schedule, _derby_set, WEEKEND, teams_slice, _distances, 42, False, cost_function),
# # #             timeout=30
# # #         )
# # #         if result is None:
# # #             raise RuntimeError("Greedy timed out or crashed")
# # #         best, best_cost, _ = result
# # #     except Exception as e:
# # #         print(f"⚠️ Greedy failed for n={n_teams}: {e}")
# # #         traceback.print_exc()
# # #         best = _basic_schedule(teams_slice)
# # #     elapsed = time.perf_counter() - t0
# # #     return _schedule_obj_to_display(best, teams_slice, n_teams), \
# # #            _stats_from_schedule_obj(best, teams_slice), elapsed

# # # def run_hill_climbing(n_teams: int):
# # #     teams_slice = _teams_obj[:n_teams]
# # #     initial = _basic_schedule(teams_slice)
# # #     t0 = time.perf_counter()
# # #     try:
# # #         result = _run_with_timeout(
# # #             hill_climbing,
# # #             (initial, _distances, _derby_set, WEEKEND, teams_slice, 500, 2, 80, 10, 20, cost_function, False),
# # #             timeout=30
# # #         )
# # #         if result is None:
# # #             raise RuntimeError("Hill Climbing timed out")
# # #         best, best_cost, _ = result
# # #     except Exception as e:
# # #         print(f"⚠️ Hill Climbing failed for n={n_teams}: {e}")
# # #         traceback.print_exc()
# # #         best = initial
# # #     elapsed = time.perf_counter() - t0
# # #     return _schedule_obj_to_display(best, teams_slice, n_teams), \
# # #            _stats_from_schedule_obj(best, teams_slice), elapsed

# # # def run_simulated_annealing(n_teams: int):
# # #     teams_slice = _teams_obj[:n_teams]
# # #     initial = _basic_schedule(teams_slice)
# # #     t0 = time.perf_counter()
# # #     try:
# # #         result = _run_with_timeout(
# # #             simulated_annealing,
# # #             (initial, _distances, _derby_set, WEEKEND, teams_slice, 5000, 0.5, 0.997, 3000, cost_function, 2000, 2.0),
# # #             timeout=30
# # #         )
# # #         if result is None:
# # #             raise RuntimeError("Simulated Annealing timed out")
# # #         best, best_cost, _ = result
# # #     except Exception as e:
# # #         print(f"⚠️ Simulated Annealing failed for n={n_teams}: {e}")
# # #         traceback.print_exc()
# # #         best = initial
# # #     elapsed = time.perf_counter() - t0
# # #     return _schedule_obj_to_display(best, teams_slice, n_teams), \
# # #            _stats_from_schedule_obj(best, teams_slice), elapsed

# # # def run_csp(n_teams: int):
# # #     teams_slice = _teams_obj[:n_teams]
# # #     t0 = time.perf_counter()
# # #     try:
# # #         result = _run_with_timeout(
# # #             csp_solver,
# # #             (teams_slice, 60, _derby_set, WEEKEND, _distances),
# # #             timeout=30
# # #         )
# # #         sched = result if result is not None else _basic_schedule(teams_slice)
# # #     except Exception as e:
# # #         print(f"⚠️ CSP failed for n={n_teams}: {e}")
# # #         traceback.print_exc()
# # #         sched = _basic_schedule(teams_slice)
# # #     elapsed = time.perf_counter() - t0
# # #     return _schedule_obj_to_display(sched, teams_slice, n_teams), \
# # #            _stats_from_schedule_obj(sched, teams_slice), elapsed

# # # ALGO_RUNNERS = {
# # #     "greedy":              run_greedy,
# # #     "hill_climbing":       run_hill_climbing,
# # #     "simulated_annealing": run_simulated_annealing,
# # #     "csp":                 run_csp,
# # # }

# # """
# # runner.py — unified interface for all 4 algorithms.
# # Every runner returns: (rounds_display, stats_dict, elapsed)
# # """
# # import sys, os, time, csv, random, copy, traceback, asyncio

# # sys.path.insert(0, os.path.dirname(__file__))

# # from models import Match, Round, Schedule
# # from data_loader import load_all
# # from schedule import double_round_robin, assign_all_days
# # from Minimize_total import cost_function, total_distance
# # from Soft_constraints import Rest_day_penalty, Derbies_penalty

# # from greedy import greedy_schedule
# # from hill_climbing import hill_climbing
# # from simulated_annealing import simulated_annealing

# # try:
# #     from csp_solver import csp_solver
# #     CSP_AVAILABLE = True
# # except ImportError:
# #     CSP_AVAILABLE = False
# #     def csp_solver(teams, time_limit=60, derbies=None, weekend=None, dist_matrix=None):
# #         return assign_all_days(double_round_robin(teams))

# # DATA_DIR    = os.path.dirname(os.path.abspath(__file__))
# # TEAMS_CSV   = os.path.join(DATA_DIR, "teams.csv")
# # DERBIES_CSV = os.path.join(DATA_DIR, "derbies.csv")
# # WEEKEND     = {"Friday", "Saturday"}

# # _teams_obj, _distances = load_all(TEAMS_CSV)
# # _derby_set = set()
# # with open(DERBIES_CSV, newline="", encoding="utf-8") as f:
# #     for row in csv.DictReader(f):
# #         _derby_set.add(frozenset([row["team_a"].strip(), row["team_b"].strip()]))

# # _team_meta = {}
# # with open(TEAMS_CSV, newline="", encoding="utf-8") as f:
# #     for row in csv.DictReader(f):
# #         n = row["team"].strip()
# #         _team_meta[n] = {
# #             "stadium": row["stadium"].strip(),
# #             "city":    row["city"].strip(),
# #             "lat":     float(row["latitude"]),
# #             "lon":     float(row["longitude"]),
# #         }

# # def get_all_teams(): return _teams_obj
# # def get_team_meta(): return _team_meta
# # def get_derby_set(): return _derby_set

# # # ----------------------------------------------------------------------
# # # helpers
# # # ----------------------------------------------------------------------
# # def _round_date(r_idx, n_teams):
# #     from datetime import date, timedelta
# #     base = date(2025, 10, 3)
# #     return (base + timedelta(weeks=r_idx)).strftime("%d - %m - %y")

# # def _schedule_obj_to_display(schedule_obj, teams_slice, n_teams):
# #     out = []
# #     for r in schedule_obj.rounds:
# #         matches = []
# #         for m in r.matches:
# #             if m is None:
# #                 continue
# #             meta = _team_meta.get(m.home.name, {})
# #             matches.append({
# #                 "home":         m.home.name,
# #                 "away":         m.away.name,
# #                 "day":          m.day or "Friday",
# #                 "home_stadium": meta.get("stadium", "—"),
# #                 "home_city":    meta.get("city", "—"),
# #                 "is_derby":     frozenset([m.home.name, m.away.name]) in _derby_set,
# #             })
# #         out.append({
# #             "round":   r.round_index + 1,
# #             "date":    _round_date(r.round_index, n_teams),
# #             "matches": matches,
# #         })
# #     return out

# # def _stats_from_schedule_obj(schedule_obj, teams_slice):
# #     dist  = total_distance(schedule_obj, _distances, teams_slice)
# #     rest  = Rest_day_penalty(schedule_obj, teams_slice, 500)
# #     derby = Derbies_penalty(schedule_obj, _derby_set, WEEKEND, 500)
# #     cost  = dist + rest + derby
# #     return {
# #         "distance":           round(dist, 1),
# #         "cost":               round(cost, 1),
# #         "rest_violations":    rest // 500,
# #         "derbies_on_weekday": derby // 500,
# #         "violations":         (rest // 500) + (derby // 500),
# #     }

# # def _basic_schedule(teams_slice):
# #     return assign_all_days(double_round_robin(teams_slice))

# # # ----------------------------------------------------------------------
# # # Async timeout helper — uses threads, no subprocess spawning
# # # ----------------------------------------------------------------------
# # async def _run_with_timeout(func, args, timeout=30):
# #     """Run a blocking algorithm in a thread with a timeout."""
# #     try:
# #         result = await asyncio.wait_for(
# #             asyncio.to_thread(func, *args),
# #             timeout=timeout
# #         )
# #         return result
# #     except asyncio.TimeoutError:
# #         print(f"⏰ Timeout after {timeout}s for {func.__name__}")
# #         return None
# #     except Exception as e:
# #         print(f"❌ Exception in {func.__name__}: {e}")
# #         traceback.print_exc()
# #         return None

# # # ----------------------------------------------------------------------
# # # Algorithm runners (all async)
# # # ----------------------------------------------------------------------
# # async def run_greedy(n_teams: int):
# #     teams_slice = _teams_obj[:n_teams]
# #     t0 = time.perf_counter()
# #     try:
# #         base_schedule = _basic_schedule(teams_slice)
# #         result = await _run_with_timeout(
# #             greedy_schedule,
# #             (base_schedule, _derby_set, WEEKEND, teams_slice, _distances, 42, False, cost_function),
# #             timeout=30
# #         )
# #         if result is None:
# #             raise RuntimeError("Greedy timed out or crashed")
# #         best, best_cost, _ = result
# #     except Exception as e:
# #         print(f"⚠️ Greedy failed for n={n_teams}: {e}")
# #         traceback.print_exc()
# #         best = _basic_schedule(teams_slice)
# #     elapsed = time.perf_counter() - t0
# #     return _schedule_obj_to_display(best, teams_slice, n_teams), \
# #            _stats_from_schedule_obj(best, teams_slice), elapsed

# # async def run_hill_climbing(n_teams: int):
# #     teams_slice = _teams_obj[:n_teams]
# #     initial = _basic_schedule(teams_slice)
# #     t0 = time.perf_counter()
# #     try:
# #         result = await _run_with_timeout(
# #             hill_climbing,
# #             (initial, _distances, _derby_set, WEEKEND, teams_slice, 500, 2, 80, 10, 20, cost_function, False),
# #             timeout=30
# #         )
# #         if result is None:
# #             raise RuntimeError("Hill Climbing timed out")
# #         best, best_cost, _ = result
# #     except Exception as e:
# #         print(f"⚠️ Hill Climbing failed for n={n_teams}: {e}")
# #         traceback.print_exc()
# #         best = initial
# #     elapsed = time.perf_counter() - t0
# #     return _schedule_obj_to_display(best, teams_slice, n_teams), \
# #            _stats_from_schedule_obj(best, teams_slice), elapsed

# # async def run_simulated_annealing(n_teams: int):
# #     teams_slice = _teams_obj[:n_teams]
# #     initial = _basic_schedule(teams_slice)
# #     t0 = time.perf_counter()
# #     try:
# #         result = await _run_with_timeout(
# #             simulated_annealing,
# #             (initial, _distances, _derby_set, WEEKEND, teams_slice, 5000, 0.5, 0.997, 3000, cost_function, 2000, 2.0),
# #             timeout=30
# #         )
# #         if result is None:
# #             raise RuntimeError("Simulated Annealing timed out")
# #         best, best_cost, _ = result
# #     except Exception as e:
# #         print(f"⚠️ Simulated Annealing failed for n={n_teams}: {e}")
# #         traceback.print_exc()
# #         best = initial
# #     elapsed = time.perf_counter() - t0
# #     return _schedule_obj_to_display(best, teams_slice, n_teams), \
# #            _stats_from_schedule_obj(best, teams_slice), elapsed

# # async def run_csp(n_teams: int):
# #     teams_slice = _teams_obj[:n_teams]
# #     t0 = time.perf_counter()
# #     try:
# #         result = await _run_with_timeout(
# #             csp_solver,
# #             (teams_slice, 60, _derby_set, WEEKEND, _distances),
# #             timeout=30
# #         )
# #         sched = result if result is not None else _basic_schedule(teams_slice)
# #     except Exception as e:
# #         print(f"⚠️ CSP failed for n={n_teams}: {e}")
# #         traceback.print_exc()
# #         sched = _basic_schedule(teams_slice)
# #     elapsed = time.perf_counter() - t0
# #     return _schedule_obj_to_display(sched, teams_slice, n_teams), \
# #            _stats_from_schedule_obj(sched, teams_slice), elapsed

# # ALGO_RUNNERS = {
# #     "greedy":              run_greedy,
# #     "hill_climbing":       run_hill_climbing,
# #     "simulated_annealing": run_simulated_annealing,
# #     "csp":                 run_csp,
# # }
# """
# runner.py — unified interface for all 4 algorithms.
# Every runner returns: (rounds_display, stats_dict, elapsed)
# """
# import sys, os, time, csv, random, copy, traceback, asyncio

# sys.path.insert(0, os.path.dirname(__file__))

# from models import Match, Round, Schedule
# from data_loader import load_all
# from schedule import double_round_robin, assign_all_days
# from Minimize_total import cost_function, total_distance
# from Soft_constraints import Rest_day_penalty, Derbies_penalty

# from greedy import greedy_schedule
# from hill_climbing import hill_climbing
# from simulated_annealing import simulated_annealing

# try:
#     from csp_solver import csp_solver
#     CSP_AVAILABLE = True
# except ImportError:
#     CSP_AVAILABLE = False
#     def csp_solver(teams, time_limit=60, derbies=None, weekend=None, dist_matrix=None):
#         return assign_all_days(double_round_robin(teams))

# DATA_DIR    = os.path.dirname(os.path.abspath(__file__))
# TEAMS_CSV   = os.path.join(DATA_DIR, "teams.csv")
# DERBIES_CSV = os.path.join(DATA_DIR, "derbies.csv")
# WEEKEND     = {"Friday", "Saturday"}

# _teams_obj, _distances = load_all(TEAMS_CSV)
# _derby_set = set()
# with open(DERBIES_CSV, newline="", encoding="utf-8") as f:
#     for row in csv.DictReader(f):
#         _derby_set.add(frozenset([row["team_a"].strip(), row["team_b"].strip()]))

# _team_meta = {}
# with open(TEAMS_CSV, newline="", encoding="utf-8") as f:
#     for row in csv.DictReader(f):
#         n = row["team"].strip()
#         _team_meta[n] = {
#             "stadium": row["stadium"].strip(),
#             "city":    row["city"].strip(),
#             "lat":     float(row["latitude"]),
#             "lon":     float(row["longitude"]),
#         }

# def get_all_teams(): return _teams_obj
# def get_team_meta(): return _team_meta
# def get_derby_set(): return _derby_set

# # ----------------------------------------------------------------------
# # helpers
# # ----------------------------------------------------------------------
# def _round_date(r_idx, n_teams):
#     from datetime import date, timedelta
#     base = date(2025, 10, 3)
#     return (base + timedelta(weeks=r_idx)).strftime("%d - %m - %y")

# def _schedule_obj_to_display(schedule_obj, teams_slice, n_teams):
#     out = []
#     for r in schedule_obj.rounds:
#         matches = []
#         for m in r.matches:
#             if m is None:
#                 continue
#             meta = _team_meta.get(m.home.name, {})
#             matches.append({
#                 "home":         m.home.name,
#                 "away":         m.away.name,
#                 "day":          m.day or "Friday",
#                 "home_stadium": meta.get("stadium", "—"),
#                 "home_city":    meta.get("city", "—"),
#                 "is_derby":     frozenset([m.home.name, m.away.name]) in _derby_set,
#             })
#         out.append({
#             "round":   r.round_index + 1,
#             "date":    _round_date(r.round_index, n_teams),
#             "matches": matches,
#         })
#     return out

# def _stats_from_schedule_obj(schedule_obj, teams_slice):
#     dist  = total_distance(schedule_obj, _distances, teams_slice)
#     rest  = Rest_day_penalty(schedule_obj, teams_slice, 500)
#     derby = Derbies_penalty(schedule_obj, _derby_set, WEEKEND, 500)
#     cost  = dist + rest + derby
#     return {
#         "distance":           round(dist, 1),
#         "cost":               round(cost, 1),
#         "rest_violations":    rest // 500,
#         "derbies_on_weekday": derby // 500,
#         "violations":         (rest // 500) + (derby // 500),
#     }

# def _basic_schedule(teams_slice):
#     return assign_all_days(double_round_robin(teams_slice))

# # ----------------------------------------------------------------------
# # Async timeout helper — uses threads, no subprocess spawning
# # ----------------------------------------------------------------------
# async def _run_with_timeout(func, args, timeout=30):
#     """Run a blocking algorithm in a thread with a timeout."""
#     try:
#         result = await asyncio.wait_for(
#             asyncio.to_thread(func, *args),
#             timeout=timeout
#         )
#         return result
#     except asyncio.TimeoutError:
#         print(f"⏰ Timeout after {timeout}s for {func.__name__}")
#         return None
#     except Exception as e:
#         print(f"❌ Exception in {func.__name__}: {e}")
#         traceback.print_exc()
#         return None

# # ----------------------------------------------------------------------
# # Algorithm runners (all async)
# # ----------------------------------------------------------------------
# async def run_greedy(n_teams: int):
#     teams_slice = _teams_obj[:n_teams]
#     t0 = time.perf_counter()
#     try:
#         base_schedule = _basic_schedule(teams_slice)
#         result = await _run_with_timeout(
#             greedy_schedule,
#             (base_schedule, _derby_set, WEEKEND, teams_slice, _distances, 42, False, cost_function),
#             timeout=30
#         )
#         if result is None:
#             raise RuntimeError("Greedy timed out or crashed")
#         best, best_cost, _ = result
#     except Exception as e:
#         print(f"⚠️ Greedy failed for n={n_teams}: {e}")
#         traceback.print_exc()
#         best = _basic_schedule(teams_slice)
#     elapsed = time.perf_counter() - t0
#     return _schedule_obj_to_display(best, teams_slice, n_teams), \
#            _stats_from_schedule_obj(best, teams_slice), elapsed

# async def run_hill_climbing(n_teams: int):
#     teams_slice = _teams_obj[:n_teams]
#     initial = _basic_schedule(teams_slice)
#     t0 = time.perf_counter()
#     try:
#         result = await _run_with_timeout(
#             hill_climbing,
#             #          schedule   distances    derbies      weekends  teams        pen  restarts iters  samples sideways tabu cost_fn       verbose
#             (initial, _distances, _derby_set, WEEKEND, teams_slice,  500,    2,    80,     10,    20,   20, cost_function, False),
#             timeout=30
#         )
#         if result is None:
#             raise RuntimeError("Hill Climbing timed out")
#         best, best_cost, _ = result
#     except Exception as e:
#         print(f"⚠️ Hill Climbing failed for n={n_teams}: {e}")
#         traceback.print_exc()
#         best = initial
#     elapsed = time.perf_counter() - t0
#     return _schedule_obj_to_display(best, teams_slice, n_teams), \
#            _stats_from_schedule_obj(best, teams_slice), elapsed

# async def run_simulated_annealing(n_teams: int):
#     teams_slice = _teams_obj[:n_teams]
#     initial = _basic_schedule(teams_slice)
#     t0 = time.perf_counter()
#     try:
#         result = await _run_with_timeout(
#             simulated_annealing,
#             (initial, _distances, _derby_set, WEEKEND, teams_slice, 5000, 0.5, 0.997, 3000, cost_function, 2000, 2.0),
#             timeout=30
#         )
#         if result is None:
#             raise RuntimeError("Simulated Annealing timed out")
#         best, best_cost, _ = result
#     except Exception as e:
#         print(f"⚠️ Simulated Annealing failed for n={n_teams}: {e}")
#         traceback.print_exc()
#         best = initial
#     elapsed = time.perf_counter() - t0
#     return _schedule_obj_to_display(best, teams_slice, n_teams), \
#            _stats_from_schedule_obj(best, teams_slice), elapsed

# async def run_csp(n_teams: int):
#     teams_slice = _teams_obj[:n_teams]
#     t0 = time.perf_counter()
#     try:
#         result = await _run_with_timeout(
#             csp_solver,
#             (teams_slice, 600, _derby_set, WEEKEND, _distances),
#             timeout=30
#         )
#         sched = result if result is not None else _basic_schedule(teams_slice)
#     except Exception as e:
#         print(f"⚠️ CSP failed for n={n_teams}: {e}")
#         traceback.print_exc()
#         sched = _basic_schedule(teams_slice)
#     elapsed = time.perf_counter() - t0
#     return _schedule_obj_to_display(sched, teams_slice, n_teams), \
#            _stats_from_schedule_obj(sched, teams_slice), elapsed

# ALGO_RUNNERS = {
#     "greedy":              run_greedy,
#     "hill_climbing":       run_hill_climbing,
#     "simulated_annealing": run_simulated_annealing,
#     "csp":                 run_csp,
# }

"""
runner.py — unified interface for all 4 algorithms.
Every runner returns: (rounds_display, stats_dict, elapsed)
On failure: raises exception (no round-robin fallback).
"""
import sys, os, time, csv, random, copy, traceback, asyncio

sys.path.insert(0, os.path.dirname(__file__))

from models import Match, Round, Schedule
from data_loader import load_all
from schedule import double_round_robin, assign_all_days
from Minimize_total import cost_function, total_distance
from Soft_constraints import Rest_day_penalty, Derbies_penalty

from greedy import greedy_schedule
from hill_climbing import hill_climbing
from simulated_annealing import simulated_annealing

try:
    from csp_solver import csp_solver
    CSP_AVAILABLE = True
except ImportError:
    CSP_AVAILABLE = False
    def csp_solver(teams, time_limit=60, derbies=None, weekend=None, dist_matrix=None):
        return assign_all_days(double_round_robin(teams))

DATA_DIR    = os.path.dirname(os.path.abspath(__file__))
TEAMS_CSV   = os.path.join(DATA_DIR, "teams.csv")
DERBIES_CSV = os.path.join(DATA_DIR, "derbies.csv")
WEEKEND     = {"Friday", "Saturday"}

_teams_obj, _distances = load_all(TEAMS_CSV)
_derby_set = set()
with open(DERBIES_CSV, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        _derby_set.add(frozenset([row["team_a"].strip(), row["team_b"].strip()]))

_team_meta = {}
with open(TEAMS_CSV, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        n = row["team"].strip()
        _team_meta[n] = {
            "stadium": row["stadium"].strip(),
            "city":    row["city"].strip(),
            "lat":     float(row["latitude"]),
            "lon":     float(row["longitude"]),
        }

def get_all_teams(): return _teams_obj
def get_team_meta(): return _team_meta
def get_derby_set(): return _derby_set

# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def _round_date(r_idx, n_teams):
    from datetime import date, timedelta
    base = date(2025, 10, 3)
    return (base + timedelta(weeks=r_idx)).strftime("%d - %m - %y")

def _schedule_obj_to_display(schedule_obj, teams_slice, n_teams):
    out = []
    for r in schedule_obj.rounds:
        matches = []
        for m in r.matches:
            if m is None:
                continue
            meta = _team_meta.get(m.home.name, {})
            matches.append({
                "home":         m.home.name,
                "away":         m.away.name,
                "day":          m.day or "Friday",
                "home_stadium": meta.get("stadium", "—"),
                "home_city":    meta.get("city", "—"),
                "is_derby":     frozenset([m.home.name, m.away.name]) in _derby_set,
            })
        out.append({
            "round":   r.round_index + 1,
            "date":    _round_date(r.round_index, n_teams),
            "matches": matches,
        })
    return out

def _stats_from_schedule_obj(schedule_obj, teams_slice):
    dist  = total_distance(schedule_obj, _distances, teams_slice)
    rest  = Rest_day_penalty(schedule_obj, teams_slice, 500)
    derby = Derbies_penalty(schedule_obj, _derby_set, WEEKEND, 500)
    cost  = dist + rest + derby
    return {
        "distance":           round(dist, 1),
        "cost":               round(cost, 1),
        "rest_violations":    rest // 500,
        "derbies_on_weekday": derby // 500,
        "violations":         (rest // 500) + (derby // 500),
    }

# ----------------------------------------------------------------------
# Algorithm runners (all async, no fallback to round-robin on failure)
# ----------------------------------------------------------------------

async def run_greedy(n_teams: int):
    teams_slice = _teams_obj[:n_teams]
    t0 = time.perf_counter()
    base_schedule = assign_all_days(double_round_robin(teams_slice))
    result = await asyncio.to_thread(
        greedy_schedule,
        base_schedule, _derby_set, WEEKEND, teams_slice, _distances, 42, False, cost_function
    )
    if result is None:
        raise RuntimeError("Greedy returned no result")
    best, best_cost, _ = result
    elapsed = time.perf_counter() - t0
    return (
        _schedule_obj_to_display(best, teams_slice, n_teams),
        _stats_from_schedule_obj(best, teams_slice),
        elapsed
    )

async def run_hill_climbing(n_teams: int):
    teams_slice = _teams_obj[:n_teams]
    initial = assign_all_days(double_round_robin(teams_slice))
    t0 = time.perf_counter()
    result = await asyncio.to_thread(
        hill_climbing,
        initial, _distances, _derby_set, WEEKEND, teams_slice,
        500, 2, 80, 10, 20, 20, cost_function, False
    )
    if result is None:
        raise RuntimeError("Hill Climbing returned no result")
    best, best_cost, _ = result
    elapsed = time.perf_counter() - t0
    return (
        _schedule_obj_to_display(best, teams_slice, n_teams),
        _stats_from_schedule_obj(best, teams_slice),
        elapsed
    )

async def run_simulated_annealing(n_teams: int):
    teams_slice = _teams_obj[:n_teams]
    initial = assign_all_days(double_round_robin(teams_slice))
    t0 = time.perf_counter()
    result = await asyncio.to_thread(
        simulated_annealing,
        initial, _distances, _derby_set, WEEKEND, teams_slice,
        5000, 0.5, 0.997, 3000, cost_function, 2000, 2.0
    )
    if result is None:
        raise RuntimeError("Simulated Annealing returned no result")
    best, best_cost, _ = result
    elapsed = time.perf_counter() - t0
    return (
        _schedule_obj_to_display(best, teams_slice, n_teams),
        _stats_from_schedule_obj(best, teams_slice),
        elapsed
    )

async def run_csp(n_teams: int):
    """
    CSP runs without any timeout — it will finish when it finishes.
    The browser spinner will just keep going until the server responds.
    """
    teams_slice = _teams_obj[:n_teams]
    t0 = time.perf_counter()
    # No wait_for / timeout wrapper — CSP gets all the time it needs
    sched = await asyncio.to_thread(
        csp_solver,
        teams_slice, 600, _derby_set, WEEKEND, _distances
    )
    if sched is None:
        raise RuntimeError("CSP solver returned no schedule")
    elapsed = time.perf_counter() - t0
    return (
        _schedule_obj_to_display(sched, teams_slice, n_teams),
        _stats_from_schedule_obj(sched, teams_slice),
        elapsed
    )

ALGO_RUNNERS = {
    "greedy":              run_greedy,
    "hill_climbing":       run_hill_climbing,
    "simulated_annealing": run_simulated_annealing,
    "csp":                 run_csp,
}