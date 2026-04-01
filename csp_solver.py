from models import Match, schedule
from constraints import is_valid
import time

# helper functions  

def generate_all_poss_matches(teams):
    matches = []
    for i in range(len(teams)):
        for j in range(len(teams)):
            if i != j:
                matches.append(Match(teams[i], teams[j]))
    return matches


# intializing an empty schedule 
def create_an_empty_schedule(teams):
    n = len(teams)
    rounds = (n - 1) * 2
    matches_per_round = n // 2
    return schedule(
        rounds=[[None for _ in range(matches_per_round)] for _ in range(rounds)]
    )


# filtering (to improve the backtracking)
def is_safe(match, sched, r_idx):
    teams_in_round = set()
    for m in sched.rounds[r_idx]:
        if m:
            teams_in_round.add(m.home)
            teams_in_round.add(m.away)
    return match.home not in teams_in_round and match.away not in teams_in_round


# forward checking to prune impossible paths
def forward_check(sched, remaining_matches):
    for r_idx, r in enumerate(sched.rounds):
        empty_slots = [s for s, m in enumerate(r) if m is None]
        if not empty_slots:
            continue
        valid_for_round = [m for m in remaining_matches if is_safe(m, sched, r_idx)]
        if len(valid_for_round) < len(empty_slots):
            return False
    return True


# soft constraints
def count_consecutive_away(team, sched, r_idx):
    count = 0
    for i in range(r_idx - 1, -1, -1):
        found = False
        for m in sched.rounds[i]:
            if m and m.away == team:
                count += 1
                found = True
                break
            elif m and m.home == team:
                return count
        if not found:
            return count
    return count


def soft_penalty(sched, r_idx, s_idx, match):
    penalty = 0
    if count_consecutive_away(match.away, sched, r_idx) >= 2:
        penalty += 10
    if hasattr(match, "is_derby") and match.is_derby:
        slots_per_round = len(sched.rounds[r_idx])
        derby_slots = [slots_per_round - 2, slots_per_round - 1]
        if s_idx not in derby_slots:
            penalty += 5
    return penalty


def select_mrv_slot(sched, matches, start_time, time_limit):
    best_slot = None
    best_domain = None

    for r_idx, r in enumerate(sched.rounds):
        for s_idx, m in enumerate(r):

            if time.time() - start_time > time_limit:
                return None, None

            if m is None:
                domain = []

                for match in matches:
                    if is_safe(match, sched, r_idx):
                        sched.rounds[r_idx][s_idx] = match

                        if is_valid(sched):
                            domain.append((match, soft_penalty(sched, r_idx, s_idx, match)))

                        sched.rounds[r_idx][s_idx] = None

                domain.sort(key=lambda x: x[1])
                domain = [m for m, _ in domain]

                if best_domain is None or len(domain) < len(best_domain):
                    best_slot = (r_idx, s_idx)
                    best_domain = domain

    return best_slot, best_domain

# best_slot :will store the (round_index, match_index) of the slot to fill next
# best_domain : the list of valid matches that can go in that slot  


def backtrack(sched, remaining_matches, start_time, time_limit):

    if time.time() - start_time > time_limit:
        return None

    slot, domain = select_mrv_slot(sched, remaining_matches, start_time, time_limit)

    if slot is None and domain is None:
        return None

    if slot is None:
        return sched

    r_idx, m_idx = slot

    for match in domain:
        sched.rounds[r_idx][m_idx] = match

        new_remaining = [m for m in remaining_matches if m != match]

        if forward_check(sched, new_remaining):
            result = backtrack(sched, new_remaining, start_time, time_limit)
            if result:
                return result

        sched.rounds[r_idx][m_idx] = None

    return None


# the fun that u can use !!!!
def csp_solver(teams, time_limit=60):
    sched = create_an_empty_schedule(teams)
    matches = generate_all_poss_matches(teams)
    start_time = time.time()

    result = backtrack(sched, matches, start_time, time_limit)

    elapsed = time.time() - start_time

    if result is None:
        if elapsed >= time_limit:
            print(f"CSP Timeout after {elapsed:.1f}s — no solution found within time limit.")
        else:
            print("CSP No valid schedule exists for these teams.")
    else:
        print(f"CSP Solution found in {elapsed:.2f}s.")

    return result


# i worked based on that 
# Vars = slots (round, match position)
# Domain = possible matches (A vs B, C vs D…)