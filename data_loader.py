import csv
import math
import os
import sys


from models import Team
DERBIES = {
    # Priority 1 
    frozenset({"USM Alger",      "MC Alger"}),
    frozenset({"USM Alger",      "CR Belouizdad"}),
    frozenset({"MC Alger",       "CR Belouizdad"}),
    # Priority 2 
    frozenset({"JS Kabylie",     "Olympique Akbou"}),
    frozenset({"CS Constantine", "ES Setif"}),
    # Priority 3 
    frozenset({"CS Constantine", "USM Khenchela"}),
    frozenset({"ES Setif",       "USM Khenchela"}),
    frozenset({"JS Saoura",      "MB Rouissat"}),
}

WEEKEND = {"Saturday", "Sunday"}

def load_derbies(filepath: str) -> set:

    derbies = set()
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            derbies.add(frozenset({row["team_a"].strip(), row["team_b"].strip()}))
    return derbies


def load_derbies_with_priority(filepath: str) -> dict:
    PRIORITY_MULTIPLIER = {"1": 3, "2": 2, "3": 1}
    weights = {}
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pair = frozenset({row["team_a"].strip(), row["team_b"].strip()})
            multiplier = PRIORITY_MULTIPLIER.get(row["priority"].strip(), 1)
            weights[pair] = multiplier
    return weights

# Load teams
def load_teams(filepath: str) -> list:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    teams = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["team"].strip()
            teams.append(Team(
                name         = name,
                lat          = float(row["latitude"]),
                lon          = float(row["longitude"])
                ))
    return teams

# Haversine formula
_EARTH_RADIUS_KM = 6_371.0
def haversine(lat1: float, lon1: float,
              lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(_EARTH_RADIUS_KM * c, 2)


# Dict-of-dicts distance matrix  
def build_distance_matrix(teams: list) -> dict:
    dist = {t.name: {} for t in teams}

    for a in teams:
        for b in teams:
            if a.name == b.name:
                dist[a.name][b.name] = 0.0
            elif b.name not in dist[a.name]:
                d = haversine(a.lat, a.lon, b.lat, b.lon)
                dist[a.name][b.name] = d
                dist[b.name][a.name] = d

    return dist


#Flat tuple-key matrix  (for soft_constraints.total_distance)

def build_flat_matrix(teams: list) -> dict:
    flat = {}
    for a in teams:
        for b in teams:
            d = haversine(a.lat, a.lon, b.lat, b.lon) if a.name != b.name else 0.0
            flat[(a.name, b.name)] = d
    return flat


# Convenience wrapper

def load_all(filepath: str) -> tuple:
    teams       = load_teams(filepath)
    dist_matrix = build_distance_matrix(teams)
    flat_matrix = build_flat_matrix(teams)
    return teams, dist_matrix, flat_matrix


def verify_distances(dist_matrix: dict) -> None:
    checks = [
        ("MC Alger",  "USM Alger",      "~9 km (same city)"),
        ("MC Alger",  "MC Oran",        "~337 km"),
        ("MC Alger",  "CS Constantine", "~328 km"),
        ("MC Alger",  "JS Saoura",      "~739 km"),
        ("JS Saoura", "CS Constantine", "~971 km"),
    ]
    print("\n=== Distance Verification ===")
    for a, b, note in checks:
        d = dist_matrix.get(a, {}).get(b, "NOT FOUND")
        print(f"  {a:<22} → {b:<22}: {d!s:>8} km   (expected {note})")
    print()


# test
if __name__ == "__main__":
    candidates = ["data/teams.csv", "../data/teams.csv", "teams.csv"]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if path is None:
        print("ERROR: teams.csv not found.")
        raise SystemExit(1)

    teams, dist_matrix, flat_matrix = load_all(path)

    print(f"Teams loaded : {len(teams)}")

    verify_distances(dist_matrix)

    print("=== Format check ===")
    print(f"  dist_matrix['MC Alger']['MC Oran']       = "
          f"{dist_matrix['MC Alger']['MC Oran']:.1f} km")
    print(f"  flat_matrix[('MC Alger', 'MC Oran')]     = "
          f"{flat_matrix[('MC Alger', 'MC Oran')]:.1f} km")

    print(f"\n  DERBIES  = {DERBIES}")
    print(f"  WEEKEND  = {WEEKEND}")