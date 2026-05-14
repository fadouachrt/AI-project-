"""
Slot-based CSP (as in the course): variables = (round, slot), domain = match indices.

Hard constraints (same as your project idea):
  - H1: at most one appearance per team per round (enforced by domains + revise).
  - H2: each unordered pair meets at most twice while building; exactly twice at the end
        (is_partially_valid + full schedule length).
  - Reverse legs in same round are impossible if H1 holds (team would appear twice).

Speed tricks (no bitmasks — still “variables + domains + lists”):
  1) Match indices — domains are lists of int, not copies of Match objects; cheap == and filters.
  2) Sparse AC-3 — only arcs between two *different slots in the same round* (binary “disjoint
     teams”). Your original queue was all ordered pairs of slots → O(S²) arcs × huge revise;
     that dominates runtime for n≥8.
  3) Incremental state — maintain pair_count and “teams used this round” from the grid so
     rebuilding a slot’s domain is O(|remaining|), not a full schedule rescan for every test.
  4) Symmetry break — fix one concrete fixture in (round 0, slot 0) to kill equivalent
     relabellings of rounds/teams (optional, big search cut).
  5) MRV — pick the empty slot with the smallest domain (lecture heuristic).
  6) Cheap value order — try matches whose unordered pair is “most constrained” first
     (already at 1 meeting before 0) to fail fast (LCV-lite without heavy scoring).

AC-3 + MRV + backtracking stay visible for the professor; forward propagation is the
same-round revise + is_partially_valid after each assignment.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

from constraints import is_partially_valid
from models import Match, Round, Schedule

Slot = Tuple[int, int]  # (round_index, slot_index)


class ScheduleCSP:
    def __init__(self, teams, symmetry_break: bool = True):
        self.teams = list(teams)
        self.n = len(self.teams)
        assert self.n % 2 == 0 and self.n >= 2, "Need an even number of teams."
        self.symmetry_break = symmetry_break

        self.sched = self._create_empty_schedule()
        self.match_list: List[Match] = self._generate_all_matches()
        self.num_matches = len(self.match_list)

        self.variables: List[Slot] = [
            (r_idx, s_idx)
            for r_idx, _ in enumerate(self.sched.rounds)
            for s_idx in range(len(self.sched.rounds[r_idx].matches))
        ]

        self.domains: Dict[Slot, List[int]] = {}
        self._t_start = 0.0
        self._time_limit = 60.0
        self._nodes = 0

    # ------------------------------------------------------------------ schedule
    def _create_empty_schedule(self) -> Schedule:
        n = len(self.teams)
        num_rounds = (n - 1) * 2
        matches_per_round = n // 2
        rounds = [
            Round(round_index=r, matches=[None] * matches_per_round)
            for r in range(num_rounds)
        ]
        return Schedule(rounds=rounds, teams=list(self.teams))

    def _generate_all_matches(self) -> List[Match]:
        matches: List[Match] = []
        for i in range(len(self.teams)):
            for j in range(len(self.teams)):
                if i != j:
                    matches.append(Match(self.teams[i], self.teams[j]))
        return matches

    # ----------------------------------------------------------- incremental helpers
    def _pair_key(self, mid: int) -> frozenset:
        m = self.match_list[mid]
        return frozenset({m.home.name, m.away.name})

    def _teams_in_match(self, mid: int) -> Tuple[str, str]:
        m = self.match_list[mid]
        return m.home.name, m.away.name

    def _teams_used_in_round_except_slot(self, r_idx: int, skip_s: int) -> Set[str]:
        used: Set[str] = set()
        for s_idx, m in enumerate(self.sched.rounds[r_idx].matches):
            if s_idx == skip_s or m is None:
                continue
            used.add(m.home.name)
            used.add(m.away.name)
        return used

    def _count_pairs_from_schedule(self) -> Dict[frozenset, int]:
        pair_count: Dict[frozenset, int] = {}
        for r in self.sched.rounds:
            for m in r.matches:
                if m is None:
                    continue
                p = frozenset({m.home.name, m.away.name})
                pair_count[p] = pair_count.get(p, 0) + 1
        return pair_count

    def _domain_for_slot(
        self,
        slot: Slot,
        remaining: Set[int],
        pair_count: Dict[frozenset, int],
    ) -> List[int]:
        r_idx, s_idx = slot
        used = self._teams_used_in_round_except_slot(r_idx, s_idx)
        out: List[int] = []
        for mid in remaining:
            h, a = self._teams_in_match(mid)
            if h in used or a in used:
                continue
            p = self._pair_key(mid)
            if pair_count.get(p, 0) >= 2:
                continue
            out.append(mid)
        # Symmetry: wlog first slot plays teams[0] at home vs teams[1] away
        if self.symmetry_break and r_idx == 0 and s_idx == 0:
            t0, t1 = self.teams[0].name, self.teams[1].name
            filtered = [
                mid
                for mid in out
                if self._teams_in_match(mid) == (t0, t1)
            ]
            if filtered:
                out = filtered
        return out

    def _build_all_domains(
        self, remaining: Set[int], pair_count: Dict[frozenset, int]
    ) -> Dict[Slot, List[int]]:
        dom: Dict[Slot, List[int]] = {}
        for slot in self.variables:
            r_idx, s_idx = slot
            if self.sched.rounds[r_idx].matches[s_idx] is not None:
                continue
            dom[slot] = self._domain_for_slot(slot, remaining, pair_count)
        return dom

    # ----------------------------------------------------------- binary consistency
    def _matches_disjoint_teams(self, mid_a: int, mid_b: int) -> bool:
        ha, aa = self._teams_in_match(mid_a)
        hb, ab = self._teams_in_match(mid_b)
        return len({ha, aa, hb, ab}) == 4

    def _same_round_neighbor_slots(self, slot: Slot) -> List[Slot]:
        r_idx, s_idx = slot
        k = len(self.sched.rounds[r_idx].matches)
        return [(r_idx, t) for t in range(k) if t != s_idx]

    def revise(self, domains: Dict[Slot, List[int]], slot_i: Slot, slot_j: Slot) -> bool:
        """AC-3 revise for arc (slot_i → slot_j): ∀ v∈D_i ∃ w∈D_j consistent (same round → disjoint teams)."""
        if slot_i not in domains or slot_j not in domains:
            return False
        r_i, _ = slot_i
        r_j, _ = slot_j
        if r_i != r_j:
            return False

        revised = False
        new_di: List[int] = []
        dj = domains[slot_j]

        for mid_i in domains[slot_i]:
            ok = any(
                mid_i != mid_j and self._matches_disjoint_teams(mid_i, mid_j)
                for mid_j in dj
            )
            if ok:
                new_di.append(mid_i)
            else:
                revised = True

        if revised:
            domains[slot_i] = new_di
        return revised

    def ac3(self, domains: Dict[Slot, List[int]]) -> bool:
        """Arc consistency on same-round disjoint-team constraints only (sparse graph)."""
        queue: deque[Tuple[Slot, Slot]] = deque()
        for slot_a in domains:
            for slot_b in self._same_round_neighbor_slots(slot_a):
                if slot_b in domains:
                    queue.append((slot_a, slot_b))

        while queue:
            slot_i, slot_j = queue.popleft()

            if slot_i not in domains or slot_j not in domains:
                continue

            if self.revise(domains, slot_i, slot_j):
                if not domains[slot_i]:
                    return False
                for slot_k in self._same_round_neighbor_slots(slot_i):
                    if slot_k in domains and slot_k != slot_j:
                        queue.append((slot_k, slot_i))
        return True

    # ----------------------------------------------------------- MRV + ordering
    def _timeout(self) -> bool:
        return (time.time() - self._t_start) > self._time_limit

    def select_mrv_slot(self, domains: Dict[Slot, List[int]]) -> Optional[Slot]:
        best_slot: Optional[Slot] = None
        best_size = float("inf")
        for slot in self.variables:
            r_idx, s_idx = slot
            if self.sched.rounds[r_idx].matches[s_idx] is not None:
                continue
            if slot not in domains:
                continue
            sz = len(domains[slot])
            if sz < best_size:
                best_size = sz
                best_slot = slot
        return best_slot

    def _order_values(self, slot: Slot, domain: List[int], pair_count: Dict[frozenset, int]):
        """Prefer matches that already have one meeting (closer to completion / fail-fast)."""
        return sorted(
            domain,
            key=lambda mid: (-pair_count.get(self._pair_key(mid), 0), mid),
        )

    # ----------------------------------------------------------- backtracking
    def backtrack(
        self,
        domains: Dict[Slot, List[int]],
        remaining: Set[int],
        pair_count: Dict[frozenset, int],
    ) -> bool:
        if self._timeout():
            return False

        self._nodes += 1
        slot = self.select_mrv_slot(domains)
        if slot is None:
            return True

        r_idx, s_idx = slot
        dom = self._order_values(slot, domains[slot], pair_count)

        for mid in dom:
            m = self.match_list[mid]
            self.sched.rounds[r_idx].matches[s_idx] = m

            if not is_partially_valid(self.sched):
                self.sched.rounds[r_idx].matches[s_idx] = None
                continue

            new_remaining = set(remaining)
            new_remaining.remove(mid)

            p = self._pair_key(mid)
            new_pc = dict(pair_count)
            new_pc[p] = new_pc.get(p, 0) + 1

            new_domains = self._build_all_domains(new_remaining, new_pc)

            if not self.ac3(new_domains):
                self.sched.rounds[r_idx].matches[s_idx] = None
                continue

            if self.backtrack(new_domains, new_remaining, new_pc):
                return True

            self.sched.rounds[r_idx].matches[s_idx] = None

        return False

    def solve(self, time_limit: float = 60.0) -> Optional[Schedule]:
        self._t_start = time.time()
        self._time_limit = time_limit
        self._nodes = 0

        remaining = set(range(self.num_matches))
        pair_count = self._count_pairs_from_schedule()
        self.domains = self._build_all_domains(remaining, pair_count)

        if not self.ac3(self.domains):
            print("CSP: AC-3 made a domain empty — no same-round-feasible assignment.")
            return None

        ok = self.backtrack(self.domains, remaining, pair_count)
        elapsed = time.time() - self._t_start

        if not ok or self._timeout():
            print(
                f"CSP: Timeout or exhausted search after {elapsed:.1f}s "
                f"(nodes expanded ≈ {self._nodes})."
            )
            return None

        assign_all_days(self.sched)
        print(f"CSP: Solution in {elapsed:.2f}s (nodes ≈ {self._nodes}).")
        return self.sched


def assign_all_days(schedule: Schedule) -> Schedule:
    for round_obj in schedule.rounds:
        assign_match_day(round_obj)
    return schedule


def assign_match_day(round_obj: Round) -> None:
    matches = [m for m in round_obj.matches if m is not None]
    if not matches:
        return

    n = len(matches)
    if n == 1:
        matches[0].day = "Saturday"
        return

    saturday_matches = matches[:1]
    friday_matches = matches[n - 2 :] if n >= 2 else []
    third_matches = matches[1 : n - 2] if n > 2 else []

    for match in saturday_matches:
        match.day = "Saturday"
    for match in friday_matches:
        match.day = "Friday"
    for match in third_matches:
        match.day = round_obj.third_day


def csp_solver(teams, time_limit: float = 60.0, symmetry_break: bool = True):
    csp = ScheduleCSP(teams, symmetry_break=symmetry_break)
    return csp.solve(time_limit=time_limit)
