from models import Match, Round, Schedule
from constraints import is_partially_valid
from collections import deque
import time


class ScheduleCSP:
    def __init__(self, teams):
        self.teams = teams
        self.sched = self._create_empty_schedule()
        self.matches = self._generate_all_matches()
        self.variables = [
            (r_idx, s_idx)
            for r_idx, r in enumerate(self.sched.rounds)
            for s_idx in range(len(r.matches))
        ]
        self.domains = self._build_initial_domains(self.matches)

    def _create_empty_schedule(self):
        n = len(self.teams)
        num_rounds = (n - 1) * 2
        matches_per_round = n // 2
        rounds = [
            Round(round_index=r, matches=[None] * matches_per_round)
            for r in range(num_rounds)
        ]
        return Schedule(rounds=rounds, teams=list(self.teams))

    def _generate_all_matches(self):
        matches = []
        for i in range(len(self.teams)):
            for j in range(len(self.teams)):
                if i != j:
                    matches.append(Match(self.teams[i], self.teams[j]))
        return matches

    def _is_safe(self, match, r_idx):
        teams_in_round = set()
        for m in self.sched.rounds[r_idx].matches:
            if m:
                teams_in_round.add(m.home)
                teams_in_round.add(m.away)
        return match.home not in teams_in_round and match.away not in teams_in_round

    def _build_initial_domains(self, remaining_matches):
        domains = {}
        for r_idx, r in enumerate(self.sched.rounds):
            for s_idx, m in enumerate(r.matches):
                if m is None:
                    domains[(r_idx, s_idx)] = [
                        match for match in remaining_matches
                        if self._is_safe(match, r_idx)
                    ]
        return domains

    def _are_consistent(self, match_i, slot_i, match_j, slot_j):
        r_i, _ = slot_i
        r_j, _ = slot_j

        if r_i == r_j:
            if {match_i.home, match_i.away} & {match_j.home, match_j.away}:
                return False

        pair_count = {}
        for r in self.sched.rounds:
            for m in r.matches:
                if m is None:
                    continue
                pair = frozenset({m.home, m.away})
                pair_count[pair] = pair_count.get(pair, 0) + 1

        pair_i = frozenset({match_i.home, match_i.away})
        pair_j = frozenset({match_j.home, match_j.away})

        count_i = pair_count.get(pair_i, 0) + 1
        if pair_i == pair_j:
            count_i += 1
        if count_i > 2:
            return False

        count_j = pair_count.get(pair_j, 0) + 1
        if count_j > 2:
            return False

        return True

    def revise(self, domains, slot_i, slot_j):
        revised = False
        new_domain = []

        for match_i in domains[slot_i]:
            has_support = any(
                match_j != match_i and
                self._are_consistent(match_i, slot_i, match_j, slot_j)
                for match_j in domains[slot_j]
            )
            if has_support:
                new_domain.append(match_i)
            else:
                revised = True

        domains[slot_i] = new_domain
        return revised

    def ac3(self, domains):
        slots = list(domains.keys())
        queue = deque()
        queue_set = set()

        for si in slots:
            for sj in slots:
                if si != sj:
                    queue.append((si, sj))
                    queue_set.add((si, sj))

        while queue:
            slot_i, slot_j = queue.popleft()
            queue_set.discard((slot_i, slot_j))

            if slot_i not in domains or slot_j not in domains:
                continue

            if self.revise(domains, slot_i, slot_j):
                if not domains[slot_i]:
                    return False

                for slot_k in slots:
                    if slot_k != slot_i and slot_k in domains:
                        arc = (slot_k, slot_i)
                        if arc not in queue_set:
                            queue.append(arc)
                            queue_set.add(arc)

        return True

    def select_mrv_slot(self, domains, start_time, time_limit):
        if time.time() - start_time > time_limit:
            return None

        best_slot = None
        best_size = float("inf")

        for slot in self.variables:
            r_idx, s_idx = slot
            if self.sched.rounds[r_idx].matches[s_idx] is None:
                size = len(domains.get(slot, []))
                if size < best_size:
                    best_size = size
                    best_slot = slot

        return best_slot

    def backtrack(self, domains, remaining_matches, start_time, time_limit):
        if time.time() - start_time > time_limit:
            return None

        slot = self.select_mrv_slot(domains, start_time, time_limit)

        if slot is None:
            if time.time() - start_time > time_limit:
                return None
            return self.sched

        r_idx, s_idx = slot

        for match in domains.get(slot, []):
            self.sched.rounds[r_idx].matches[s_idx] = match
            new_remaining = [m for m in remaining_matches if m != match]

            if is_partially_valid(self.sched):
                new_domains = self._build_initial_domains(new_remaining)

                if self.ac3(new_domains):
                    result = self.backtrack(new_domains, new_remaining, start_time, time_limit)
                    if result is not None:
                        return result

            self.sched.rounds[r_idx].matches[s_idx] = None

        return None

    def solve(self, time_limit=60):
        start_time = time.time()

        if not self.ac3(self.domains):
            print("CSP: No valid schedule exists for these teams.")
            return None

        result = self.backtrack(self.domains, self.matches, start_time, time_limit)

        elapsed = time.time() - start_time

        if result is None:
            if elapsed >= time_limit:
                print(f"CSP Timeout after {elapsed:.1f}s — no solution found within time limit.")
            else:
                print("CSP: No valid schedule exists for these teams.")
        else:
            assign_all_days(result)
            print(f"CSP Solution found in {elapsed:.2f}s.")

        return result


def assign_all_days(schedule):
    for round_obj in schedule.rounds:
        assign_match_day(round_obj)
    return schedule


def assign_match_day(round_obj):
    matches = [m for m in round_obj.matches if m is not None]
    if len(matches) == 0:
        return
    
    n = len(matches)
    
    if n == 1:
        matches[0].day = "Saturday"
        return
    
    saturday_matches = matches[:1]
    friday_matches = matches[n-2:] if n >= 2 else []
    third_matches = matches[1:n-2] if n > 2 else []
    
    for match in saturday_matches:
        match.day = "Saturday"
    for match in friday_matches:
        match.day = "Friday"
    for match in third_matches:
        match.day = round_obj.third_day


def csp_solver(teams, time_limit=60):
    csp = ScheduleCSP(teams)
    return csp.solve(time_limit)


# i worked based on that 
# Vars = slots (round, match position)
# Domain = possible matches (A vs B, C vs D…)