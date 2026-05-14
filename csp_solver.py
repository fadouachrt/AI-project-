
from __future__ import annotations

import time
from itertools import product
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from constraints import is_valid
from models import Match, Round, Schedule

# Same weight as soft_constraints.py (used only for day scoring, not CSP feasibility).
_SOFT_W = 500


class ScheduleCSP:
    def __init__(
        self,
        teams,
        derbies: Optional[Set[FrozenSet[str]]] = None,
        weekend: Optional[List[str]] = None,
    ):
        self.teams = teams
        self.n = len(teams)
        self.derbies: Set[FrozenSet[str]] = derbies if derbies is not None else set()
        self.weekend: List[str] = (
            weekend if weekend is not None else ["Saturday", "Friday"]
        )
        # Double round-robin: each team plays every other team twice
        # So each team plays 2*(n-1) games, total rounds = 2*(n-1)
        self.num_rounds = 2 * (self.n - 1)
        self.matches_per_round = self.n // 2

        # Track assignments: schedule[round][match] = (home_team, away_team)
        self.schedule = [[None] * self.matches_per_round for _ in range(self.num_rounds)]
        
        # Track which teams play in each round
        self.teams_in_round = [[False] * self.n for _ in range(self.num_rounds)]
        
        # Track how many times each pair has played and in which orientation
        # pair_games[(min, max)] = {'home_count': 0, 'away_count': 0}
        self.pair_games = {}
        for i in range(self.n):
            for j in range(i + 1, self.n):
                self.pair_games[(i, j)] = {'home_count': 0, 'away_count': 0}
        
        # Track home/away counts per team
        self.home_count = [0] * self.n
        self.away_count = [0] * self.n
        
        # Statistics
        self.backtracks = 0
        self.nodes = 0

    def is_complete(self):
        """Check if all rounds are fully scheduled."""
        for r in range(self.num_rounds):
            for m in range(self.matches_per_round):
                if self.schedule[r][m] is None:
                    return False
        return True

    def get_available_teams(self, round_num):
        """Get list of teams not yet scheduled in this round."""
        available = []
        for t in range(self.n):
            if not self.teams_in_round[round_num][t]:
                available.append(t)
        return available

    def get_possible_matches(self, round_num, match_idx):
        """
        Get all possible (home, away) pairs for this slot.
        Ensures each pair plays exactly twice (once home, once away).
        """
        available = self.get_available_teams(round_num)
        possible = []
        
        for i in range(len(available)):
            for j in range(i + 1, len(available)):
                home = available[i]
                away = available[j]
                
                # Get pair info
                pair_key = (min(home, away), max(home, away))
                pair_info = self.pair_games[pair_key]
                total_games = pair_info['home_count'] + pair_info['away_count']
                
                # Each pair must play exactly 2 games total
                if total_games >= 2:
                    continue
                
                # Try both orientations
                # Orientation 1: home as home, away as away
                if pair_info['home_count'] < 1:  # Can still play home
                    possible.append((home, away))
                
                # Orientation 2: away as home, home as away
                if pair_info['away_count'] < 1:  # Can still play away
                    possible.append((away, home))
        
        return possible

    def assign_match(self, round_num, match_idx, home, away):
        """Assign a match to the schedule."""
        self.schedule[round_num][match_idx] = (home, away)
        self.teams_in_round[round_num][home] = True
        self.teams_in_round[round_num][away] = True
        
        # Update pair counts
        pair_key = (min(home, away), max(home, away))
        if home < away:
            self.pair_games[pair_key]['home_count'] += 1
        else:
            self.pair_games[pair_key]['away_count'] += 1
        
        # Update home/away counts
        self.home_count[home] += 1
        self.away_count[away] += 1

    def unassign_match(self, round_num, match_idx):
        """Unassign a match (backtrack)."""
        home, away = self.schedule[round_num][match_idx]
        self.schedule[round_num][match_idx] = None
        self.teams_in_round[round_num][home] = False
        self.teams_in_round[round_num][away] = False
        
        # Update pair counts
        pair_key = (min(home, away), max(home, away))
        if home < away:
            self.pair_games[pair_key]['home_count'] -= 1
        else:
            self.pair_games[pair_key]['away_count'] -= 1
        
        # Update home/away counts
        self.home_count[home] -= 1
        self.away_count[away] -= 1

    def get_next_empty_slot(self):
        """Find the next empty slot using MRV."""
        best_round = -1
        best_match = -1
        min_possibilities = float('inf')
        
        for r in range(self.num_rounds):
            for m in range(self.matches_per_round):
                if self.schedule[r][m] is None:
                    possible = len(self.get_possible_matches(r, m))
                    if possible < min_possibilities:
                        min_possibilities = possible
                        best_round = r
                        best_match = m
                        if min_possibilities == 0:
                            return (best_round, best_match)
        
        if best_round == -1:
            return None
        return (best_round, best_match)

    def forward_check(self, round_num, match_idx, home, away):
        """
        Forward checking: ensure assignment doesn't make any future slot impossible.
        """
        # Check remaining slots in current round
        for m in range(match_idx + 1, self.matches_per_round):
            if self.schedule[round_num][m] is None:
                if len(self.get_possible_matches(round_num, m)) == 0:
                    return False
        
        # Check future rounds
        for r in range(round_num + 1, self.num_rounds):
            for m in range(self.matches_per_round):
                if self.schedule[r][m] is None:
                    if len(self.get_possible_matches(r, m)) == 0:
                        return False
        
        return True

    def lcv_order(self, round_num, match_idx, possibilities):
        """
        LCV: Order possibilities by least constraining first.
        """
        if len(possibilities) <= 1:
            return possibilities
        
        scored = []
        for home, away in possibilities:
            # Count how many future possibilities this eliminates
            constraint_score = 0
            
            # Simulate assignment
            self.assign_match(round_num, match_idx, home, away)
            
            # Check all future slots
            for r in range(round_num, self.num_rounds):
                for m in range(self.matches_per_round):
                    if self.schedule[r][m] is None:
                        poss = len(self.get_possible_matches(r, m))
                        if poss == 0:
                            constraint_score += 100  # Very bad
                        elif poss == 1:
                            constraint_score += 10   # Moderately bad
            
            # Undo simulation
            self.unassign_match(round_num, match_idx)
            
            scored.append(((home, away), constraint_score))
        
        # Sort by least constraining (lowest score first)
        scored.sort(key=lambda x: x[1])
        return [x[0] for x in scored]

    def backtrack(self, start_time, time_limit):
        """Backtracking search with MRV, LCV, and forward checking."""
        self.nodes += 1
        
        if time.time() - start_time > time_limit:
            return False
        
        if self.is_complete():
            return True
        
        slot = self.get_next_empty_slot()
        if slot is None:
            return False
        
        round_num, match_idx = slot
        
        # Get possible matches for this slot
        possibilities = self.get_possible_matches(round_num, match_idx)
        
        if not possibilities:
            return False
        
        # Apply LCV ordering
        possibilities = self.lcv_order(round_num, match_idx, possibilities)
        
        # Try each possibility
        for home, away in possibilities:
            # Assign
            self.assign_match(round_num, match_idx, home, away)
            self.backtracks += 1
            
            # Forward checking
            if self.forward_check(round_num, match_idx, home, away):
                # Recurse
                if self.backtrack(start_time, time_limit):
                    return True
            
            # Backtrack
            self.unassign_match(round_num, match_idx)
        
        return False

    def to_schedule(self):
        """Convert to Schedule object."""
        rounds = []
        
        for r in range(self.num_rounds):
            matches = []
            for m in range(self.matches_per_round):
                assignment = self.schedule[r][m]
                if assignment is not None:
                    home_idx, away_idx = assignment
                    home_team = self.teams[home_idx]
                    away_team = self.teams[away_idx]
                    match = Match(home=home_team, away=away_team)
                    matches.append(match)
            round_obj = Round(r, matches)
            rounds.append(round_obj)
        
        return Schedule(rounds, self.teams)

    def solve(self, time_limit=60):
        """Solve the CSP."""
        start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"CSP Solver for {self.n} teams")
        print(f"Rounds: {self.num_rounds}, Matches per round: {self.matches_per_round}")
        print(f"{'='*60}")
        
        found = self.backtrack(start_time, time_limit)
        elapsed = time.time() - start_time
        
        if found:
            schedule = self.to_schedule()
            assign_days_soft(schedule, self.derbies, self.weekend)
            
            print(f"\n✅ Solution found in {elapsed:.2f}s")
            print(f"   Backtracks: {self.backtracks}")
            print(f"   Nodes: {self.nodes}")
            
            # Validate
            if is_valid(schedule):
                print(f"   Valid: ✓")
            else:
                from constraints import csp_validate
                violations = csp_validate(schedule)
                print(f"   Valid: ✗ ({len(violations)} violations)")
                for v in violations[:5]:
                    print(f"     - {v}")
            
            return schedule
        else:
            print(f"\n❌ No solution found in {elapsed:.2f}s")
            return None


def _weekday_index(day: str) -> int:
   
    order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    return order.index(day)


def _circular_rest_gap(day_a: str, day_b: str) -> int:
    """Calendar days strictly between two match weekdays (same spirit as Rest_day_penalty)."""
    a = _weekday_index(day_a)
    b = _weekday_index(day_b)
    if b > a:
        return b - a - 1
    return (7 - a) + b - 1


def assign_days_soft(
    schedule: Schedule,
    derbies: Set[FrozenSet[str]],
    weekend: List[str],
) -> Schedule:
    """
    After CSP fixes who plays whom, assign ``match.day`` only.

    Keeps your CSP untouched; this step tries to *reduce* soft penalty:
      - derbies on ``weekend`` days (Derbies_penalty),
      - rest ≥ 6 “gap” between a team’s consecutive match days (Rest_day_penalty style),
      - avoid 3+ consecutive away when scanning rounds in order (successive_away_penalty style).

    Per round we try every tuple in ``product(round.days, repeat=#matches)`` (≤ 3^k) and
    pick the lowest incremental score. Not globally optimal, but fast and much better than
    a fixed Friday/Saturday pattern when k grows.
    """
    name_to_i: Dict[str, int] = {t.name: i for i, t in enumerate(schedule.teams)}
    nt = len(schedule.teams)
    last_day: List[Optional[str]] = [None] * nt
    away_run: List[int] = [0] * nt
    weekend_set = set(weekend)

    for round_obj in schedule.rounds:
        matches = round_obj.matches
        if not matches:
            continue

        day_choices = list(round_obj.days)
        k = len(matches)
        best_combo: Optional[Tuple[str, ...]] = None
        best_score = float("inf")

        for combo in product(day_choices, repeat=k):
            ld = last_day[:]
            ar = away_run[:]
            local = 0

            for match, d in zip(matches, combo):
                pr = match.pair()
                if pr in derbies and d not in weekend_set:
                    local += _SOFT_W

                hi = name_to_i[match.home.name]
                ai = name_to_i[match.away.name]

                if ld[hi] is not None and _circular_rest_gap(ld[hi], d) < 6:
                    local += _SOFT_W
                ar[hi] = 0
                ld[hi] = d

                if ld[ai] is not None and _circular_rest_gap(ld[ai], d) < 6:
                    local += _SOFT_W
                ar[ai] += 1
                if ar[ai] >= 3:
                    local += _SOFT_W
                    ar[ai] = 0
                ld[ai] = d

            if local < best_score:
                best_score = local
                best_combo = combo

        assert best_combo is not None
        for match, d in zip(matches, best_combo):
            match.day = d

        for match, d in zip(matches, best_combo):
            hi = name_to_i[match.home.name]
            ai = name_to_i[match.away.name]
            away_run[hi] = 0
            last_day[hi] = d
            away_run[ai] += 1
            if away_run[ai] >= 3:
                away_run[ai] = 0
            last_day[ai] = d

    return schedule


def csp_solver(
    teams,
    time_limit: float = 60,
    derbies: Optional[Set[FrozenSet[str]]] = None,
    weekend: Optional[List[str]] = None,
):
    """Main entry: same CSP as before; optional derbies / weekend for day assignment only."""
    csp = ScheduleCSP(teams, derbies=derbies, weekend=weekend)
    return csp.solve(time_limit)




# i worked based on that 
# Vars = slots (round, match position)
# Domain = possible matches (A vs B, C vs D…)