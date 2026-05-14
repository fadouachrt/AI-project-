

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import Team
from constraints import is_valid, csp_validate
from csp_solver import csp_solver
from data_loader import DERBIES, WEEKEND, build_flat_matrix, load_teams
from Minimize_total import cost_function

# Max wall-clock per league size (seconds)
TIME_LIMIT_SEC = 20 * 60

# Sizes to benchmark (even teams only for this CSP)
BENCHMARK_NS = (10, 12, 14, 16, 18, 20)

# Print full round-by-round schedule only for these sizes (large output)
FULL_SCHEDULE_NS = frozenset({10, 12})


def _find_teams_csv() -> str:
    candidates = [
        os.path.join(os.path.dirname(__file__), "data", "teams.csv"),
        os.path.join(os.path.dirname(__file__), "teams.csv"),
        "data/teams.csv",
        "teams.csv",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    raise FileNotFoundError("teams.csv not found (tried data/teams.csv and ./teams.csv).")


def make_n_teams(n: int, csv_path: str) -> List[Team]:
    """Use first n teams from CSV; pad with synthetic teams if the file has fewer than n."""
    loaded = load_teams(csv_path)
    if len(loaded) >= n:
        return loaded[:n]
    teams = list(loaded)
    base = len(teams)
    for i in range(base, n):
        teams.append(
            Team(
                name=f"Synthetic_{i + 1}",
                lat=36.35 + (i % 7) * 0.15,
                lon=3.08 + (i // 7) * 0.12,
            )
        )
    return teams


def derbies_relevant(teams: List[Team], derby_source: Set[frozenset]) -> Set[frozenset]:
    names = {t.name for t in teams}
    return {d for d in derby_source if d <= names}


def print_full_schedule(schedule, title: str = "COMPLETE SCHEDULE") -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    for round_obj in schedule.rounds:
        print(f"\n{'─' * 70}")
        print(f"ROUND {round_obj.round_index + 1}  (days in round: {round_obj.days})")
        print(f"{'─' * 70}")
        for match in round_obj.matches:
            day_str = f"  [{match.day}]" if match.day else ""
            print(f"  {match.home.name:28} vs {match.away.name:28}{day_str}")
    print("\n" + "=" * 80)


def print_results_table(rows: List[Tuple[int, float, str, Optional[float]]]) -> None:
    """
    rows: (n_teams, elapsed_sec, status, total_cost or None)
    status: OK | NO_SCHEDULE_IN_TIME | INVALID
    """
    print("\n")
    print("=" * 88)
    print("BENCHMARK SUMMARY  (time limit per size: 20 minutes)")
    print("=" * 88)
    w_n, w_t, w_s, w_c = 6, 14, 28, 18
    header = (
        f"| {'n':^{w_n}} | {'time (s)':^{w_t}} | {'result':^{w_s}} | {'total_cost':^{w_c}} |"
    )
    sep = (
        "+"
        + "-" * (w_n + 2)
        + "+"
        + "-" * (w_t + 2)
        + "+"
        + "-" * (w_s + 2)
        + "+"
        + "-" * (w_c + 2)
        + "+"
    )
    print(sep)
    print(header)
    print(sep)
    for n, elapsed, status, cost in rows:
        ts = f"{elapsed:.2f}"
        if cost is None:
            cs = "—"
        else:
            cs = f"{cost:.2f}"
        print(f"| {n:^{w_n}} | {ts:^{w_t}} | {status:^{w_s}} | {cs:^{w_c}} |")
    print(sep)
    print(
        "\nNotes:\n"
        "  • total_cost = travel km + rest-day penalty + derby penalty + successive-away "
        "penalties (see Minimize_total.cost_function).\n"
        "  • NO_SCHEDULE_IN_TIME means csp_solver returned None within the limit.\n"
    )


def run_one(
    n: int,
    teams: List[Team],
    derbies: Set[frozenset],
    weekend: Set[str],
    time_limit: float,
    print_schedule: bool,
) -> Tuple[float, str, Optional[float], Optional[object]]:
    """
    Returns (elapsed_seconds, status, total_cost_or_None, schedule_or_None).
    """
    dist_matrix = build_flat_matrix(teams)
    t0 = time.time()
    schedule = csp_solver(
        teams,
        time_limit=time_limit,
        derbies=derbies,
        weekend=list(weekend),
    )
    elapsed = time.time() - t0

    if schedule is None:
        print(f"\n❌ n={n}: no full schedule within {time_limit:.0f}s (elapsed {elapsed:.2f}s).")
        return elapsed, "NO_SCHEDULE_IN_TIME", None, None

    if not is_valid(schedule):
        print(f"\n⚠ n={n}: solver returned a grid but is_valid() failed.")
        for line in csp_validate(schedule)[:8]:
            print(f"   - {line}")
        return elapsed, "INVALID", None, schedule

    total = cost_function(schedule, teams, dist_matrix, derbies, weekend, 500)
    print(f"\n✅ n={n}: valid schedule in {elapsed:.2f}s  |  total_cost = {total:.2f}")

    if print_schedule:
        print_full_schedule(schedule, title=f"FULL SCHEDULE  (n = {n} teams)")

    return elapsed, "OK", float(total), schedule


def main() -> None:
    parser = argparse.ArgumentParser(description="CSP benchmark + schedules for n=10,12")
    parser.add_argument(
        "--sizes",
        type=str,
        default=",".join(str(x) for x in BENCHMARK_NS),
        help=f"Comma-separated even team counts (default: {','.join(map(str,BENCHMARK_NS))})",
    )
    parser.add_argument(
        "--time-limit",
        type=float,
        default=TIME_LIMIT_SEC,
        help="Per-size time limit in seconds (default: 1200 = 20 min)",
    )
    parser.add_argument(
        "--no-full-print",
        action="store_true",
        help="Do not print round-by-round schedule even for n=10,12",
    )
    args = parser.parse_args()

    try:
        sizes = tuple(int(x.strip()) for x in args.sizes.split(",") if x.strip())
    except ValueError:
        print("Bad --sizes", file=sys.stderr)
        sys.exit(1)

    csv_path = _find_teams_csv()
    time_limit = float(args.time_limit)

    print("\n" + "=" * 80)
    print("CSP BENCHMARK  (csp_solver → days optimized in solver)")
    print("=" * 80)
    print(f"teams.csv: {csv_path}")
    print(f"Per-size time limit: {time_limit:.0f}s ({time_limit/60:.1f} min)")
    print(f"Sizes: {sizes}")

    rows: List[Tuple[int, float, str, Optional[float]]] = []

    for n in sizes:
        if n % 2 or n < 2:
            print(f"\nSkip n={n} (need an even number of teams ≥ 2).")
            continue
        teams = make_n_teams(n, csv_path)
        derbies = derbies_relevant(teams, DERBIES)

        want_full = (n in FULL_SCHEDULE_NS) and (not args.no_full_print)
        elapsed, status, cost, _sched = run_one(
            n, teams, derbies, WEEKEND, time_limit, print_schedule=want_full
        )
        rows.append((n, elapsed, status, cost))

    print_results_table(rows)


if __name__ == "__main__":
    main()
