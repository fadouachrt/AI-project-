import csv
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import Team

def load_derbies(file_path):
    derbies = set()
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            team_a = row["team_a"]
            team_b = row["team_b"]

            derbies.add(frozenset([team_a, team_b]))

    return derbies



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



# Convenience wrapper

def load_all(filepath: str) -> tuple:
    teams       = load_teams(filepath)
    dist_matrix = build_distance_matrix(teams)
    return teams, dist_matrix


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

    teams, dist_matrix = load_all(path)

    print(f"Teams loaded : {len(teams)}")

    verify_distances(dist_matrix)

    print("=== Format check ===")
    print(f"  dist_matrix['MC Alger']['MC Oran']       = "
          f"{dist_matrix['MC Alger']['MC Oran']:.1f} km")



