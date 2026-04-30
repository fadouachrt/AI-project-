
class Match:
    def __init__(self, home, away):
        self.home = home  # home team name (str)
        self.away = away  # away team name (str)

    def __repr__(self):
        return f"{self.home} (H) vs {self.away}"

    def pair(self):
        """Return the unordered pair as a frozenset (ignores home/away)."""
        return frozenset({self.home, self.away})

    def ordered_pair(self):
        """Return the ordered pair as a tuple (home, away)."""
        return (self.home, self.away)


class Schedule:
    """A full season schedule: a list of rounds, each round is a list of Matches."""

    def __init__(self, rounds=None, teams=None):
        self.rounds = rounds if rounds is not None else []
        self.teams = teams if teams is not None else []

    def total_rounds(self):
        return len(self.rounds)

    def total_matches(self):
        return sum(len(round_matches) for round_matches in self.rounds)

    def print_schedule(self):
        """Pretty-print the full schedule."""
        for i, round_matches in enumerate(self.rounds, 1):
            print(f"\n--- Round {i} ---")
            for match in round_matches:
                print(f"  {match}")
