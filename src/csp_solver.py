from __future__ import annotations

import time
from itertools import permutations
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from constraints import is_valid
from models import Match, Round, Schedule

SOFT_W = 500


class ScheduleCSP:
    def __init__(
        self,
        teams,
        derbies: Optional[Set[FrozenSet[str]]] = None,
        weekend: Optional[List[str]] = None,
        dist_matrix: Optional[Dict] = None,
    ):
        self.teams = teams
        self.n = len(teams)
        self.derbies: Set[FrozenSet[str]] = derbies if derbies is not None else set()
        self.weekend: List[str] = weekend if weekend is not None else ["Friday", "Saturday"]
        self.dist_matrix = dist_matrix
        
        self.num_rounds = 2 * (self.n - 1)
        self.matches_per_round = self.n // 2

        self.schedule = [[None] * self.matches_per_round for _ in range(self.num_rounds)]
        self.teams_in_round = [[False] * self.n for _ in range(self.num_rounds)]
        
        self.pair_games = {}
        for i in range(self.n):
            for j in range(i + 1, self.n):
                self.pair_games[(i, j)] = {'home_count': 0, 'away_count': 0}
        
        self.home_count = [0] * self.n
        self.away_count = [0] * self.n
        self.consecutive_away = [0] * self.n
        self.current_position = [i for i in range(self.n)]
        self.current_travel = 0
        
        self.backtracks = 0
        self.nodes = 0
        
        # ----- Symmetry breaking flag -----
        self.symmetry_broken = False

    # ---------- distance helpers ----------
    def get_distance(self, from_team: int, to_team: int) -> float:
        if self.dist_matrix is None:
            return 0
        from_name = self.teams[from_team].name
        to_name = self.teams[to_team].name
        try:
            return self.dist_matrix[from_name][to_name]
        except (KeyError, TypeError):
            return 0

    def calculate_travel(self, team: int, loc: str, opp: int) -> float:
        if loc == "home":
            return 0
        else:
            from_city = self.current_position[team]
            return self.get_distance(from_city, opp)

    def calculate_away_penalty(self, team: int, loc: str) -> int:
        if loc == "away":
            new_consecutive = self.consecutive_away[team] + 1
            if new_consecutive >= 3:
                return SOFT_W
        return 0

    # ---------- core CSP methods ----------
    def is_complete(self):
        for r in range(self.num_rounds):
            for m in range(self.matches_per_round):
                if self.schedule[r][m] is None:
                    return False
        return True

    def get_available_teams(self, round_num):
        available = []
        for t in range(self.n):
            if not self.teams_in_round[round_num][t]:
                available.append(t)
        return available

    def get_possible_matches(self, round_num, match_idx):
        available = self.get_available_teams(round_num)
        possible = []
        for i in range(len(available)):
            for j in range(i + 1, len(available)):
                home = available[i]
                away = available[j]
                pair_key = (min(home, away), max(home, away))
                pair_info = self.pair_games[pair_key]
                total_games = pair_info['home_count'] + pair_info['away_count']
                if total_games >= 2:
                    continue
                if pair_info['home_count'] < 1:
                    possible.append((home, away))
                if pair_info['away_count'] < 1:
                    possible.append((away, home))
        return possible

    def assign_match(self, round_num, match_idx, home, away):
        travel_home = self.calculate_travel(home, "home", away)
        travel_away = self.calculate_travel(away, "away", home)
        away_penalty_home = self.calculate_away_penalty(home, "home")
        away_penalty_away = self.calculate_away_penalty(away, "away")
        
        self.schedule[round_num][match_idx] = (home, away)
        self.teams_in_round[round_num][home] = True
        self.teams_in_round[round_num][away] = True
        
        pair_key = (min(home, away), max(home, away))
        if home < away:
            self.pair_games[pair_key]['home_count'] += 1
        else:
            self.pair_games[pair_key]['away_count'] += 1
        
        self.home_count[home] += 1
        self.away_count[away] += 1
        self.consecutive_away[home] = 0
        self.consecutive_away[away] += 1
        
        self.current_travel += travel_home + travel_away + away_penalty_home + away_penalty_away
        self.current_position[home] = home
        self.current_position[away] = home

    def unassign_match(self, round_num, match_idx):
        home, away = self.schedule[round_num][match_idx]
        self.schedule[round_num][match_idx] = None
        self.teams_in_round[round_num][home] = False
        self.teams_in_round[round_num][away] = False
        
        pair_key = (min(home, away), max(home, away))
        if home < away:
            self.pair_games[pair_key]['home_count'] -= 1
        else:
            self.pair_games[pair_key]['away_count'] -= 1
        
        self.home_count[home] -= 1
        self.away_count[away] -= 1
        self.recalculate_state()

    def recalculate_state(self):
        positions = [i for i in range(self.n)]
        total = 0
        consec_away = [0] * self.n
        for r in range(self.num_rounds):
            for m in range(self.matches_per_round):
                assignment = self.schedule[r][m]
                if assignment is None:
                    continue
                home, away = assignment
                if positions[away] != home:
                    total += self.get_distance(positions[away], home)
                    positions[away] = home
                positions[home] = home
                consec_away[home] = 0
                consec_away[away] += 1
                if consec_away[away] >= 3:
                    total += SOFT_W
        self.current_travel = total
        for i in range(self.n):
            self.current_position[i] = positions[i]
            self.consecutive_away[i] = consec_away[i]

    def get_next_empty_slot(self):
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
        for m in range(match_idx + 1, self.matches_per_round):
            if self.schedule[round_num][m] is None:
                if len(self.get_possible_matches(round_num, m)) == 0:
                    return False
        for r in range(round_num + 1, self.num_rounds):
            for m in range(self.matches_per_round):
                if self.schedule[r][m] is None:
                    if len(self.get_possible_matches(r, m)) == 0:
                        return False
        return True

    def lcv_order(self, round_num, match_idx, possibilities):
        if len(possibilities) <= 1:
            return possibilities
        scored = []
        for home, away in possibilities:
            travel_cost = self.calculate_travel(home, "home", away)
            travel_cost += self.calculate_travel(away, "away", home)
            away_penalty = self.calculate_away_penalty(away, "away")
            constraint_score = travel_cost + away_penalty
            
            self.assign_match(round_num, match_idx, home, away)
            # Full lookahead over all remaining rounds
            for r in range(round_num + 1, self.num_rounds):
                for m in range(self.matches_per_round):
                    if self.schedule[r][m] is None:
                        poss = len(self.get_possible_matches(r, m))
                        if poss == 0:
                            constraint_score += 1000
                        elif poss == 1:
                            constraint_score += 100
                        elif poss <= 3:
                            constraint_score += 10
            self.unassign_match(round_num, match_idx)
            scored.append(((home, away), constraint_score))
        scored.sort(key=lambda x: x[1])
        return [x[0] for x in scored]

    # ----- Symmetry breaking -----
    def break_symmetry(self):
        """Fix first match (team 0 vs team 1) in round 0, slot 0."""
        if not self.symmetry_broken and self.n >= 2:
            if self.schedule[0][0] is None:
                available = self.get_available_teams(0)
                if 0 in available and 1 in available:
                    self.assign_match(0, 0, 0, 1)
                    self.symmetry_broken = True
                    return True
        return False

    # ----- Backtracking (chronological) -----
    def backtrack(self, start_time, time_limit):
        self.nodes += 1
        if time.time() - start_time > time_limit:
            return False
        
        # Apply symmetry breaking once at the beginning
        if not self.symmetry_broken:
            self.break_symmetry()
        
        if self.is_complete():
            return True
        
        slot = self.get_next_empty_slot()
        if slot is None:
            return False
        
        round_num, match_idx = slot
        possibilities = self.get_possible_matches(round_num, match_idx)
        if not possibilities:
            return False
        
        possibilities = self.lcv_order(round_num, match_idx, possibilities)
        
        for home, away in possibilities:
            self.assign_match(round_num, match_idx, home, away)
            self.backtracks += 1
            
            if self.forward_check(round_num, match_idx, home, away):
                if self.backtrack(start_time, time_limit):
                    return True
            
            self.unassign_match(round_num, match_idx)
        
        return False

    def to_schedule(self):
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
        start_time = time.time()
        print(f"\n{'='*60}")
        print(f"CSP Solver with Symmetry Breaking for {self.n} teams")
        print(f"Rounds: {self.num_rounds}, Matches per round: {self.matches_per_round}")
        print(f"{'='*60}")
        
        found = self.backtrack(start_time, time_limit)
        elapsed = time.time() - start_time
        
        if found:
            schedule = self.to_schedule()
            schedule = assign_days_balanced(schedule, self.derbies, self.weekend)
            print(f"\nSolution found in {elapsed:.2f}s")
            print(f"   Backtracks: {self.backtracks}")
            print(f"   Nodes: {self.nodes}")
            if self.dist_matrix:
                from Minimize_total import total_distance
                travel_dist = total_distance(schedule, self.dist_matrix, self.teams)
                print(f"   Travel distance: {travel_dist:.2f} km")
            if is_valid(schedule):
                print(f"   Valid: Yes")
            else:
                from constraints import csp_validate
                violations = csp_validate(schedule)
                print(f"   Valid: No ({len(violations)} violations)")
            return schedule
        else:
            print(f"\nNo solution found in {elapsed:.2f}s (nodes={self.nodes})")
            return None


def assign_days_balanced(schedule: Schedule, derbies: Set[FrozenSet[str]], weekend: List[str]) -> Schedule:
    weekend_set = set(weekend)
    for round_obj in schedule.rounds:
        matches = round_obj.matches
        if not matches:
            continue
        day_choices = round_obj.days
        k = len(matches)
        base_per_day = k // len(day_choices)
        remainder = k % len(day_choices)
        distribution = [base_per_day + (1 if i < remainder else 0) for i in range(len(day_choices))]
        day_pool = []
        for i, day in enumerate(day_choices):
            day_pool.extend([day] * distribution[i])
        best_assignment = None
        best_score = float('inf')
        for day_perm in set(permutations(day_pool)):
            score = 0
            for i, match in enumerate(matches):
                day = day_perm[i]
                if match.pair() in derbies and day not in weekend_set:
                    score += SOFT_W
            if score < best_score:
                best_score = score
                best_assignment = day_perm
        if best_assignment:
            for match, day in zip(matches, best_assignment):
                match.day = day
    return schedule


def csp_solver(teams, time_limit=60, derbies=None, weekend=None, dist_matrix=None):
    solver = ScheduleCSP(teams, derbies=derbies, weekend=weekend, dist_matrix=dist_matrix)
    return solver.solve(time_limit)