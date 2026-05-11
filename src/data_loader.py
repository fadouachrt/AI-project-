"""
this is how you can use this file:

from src.data_loader import load_all
teams_dict, dist_matrix = load_all("data/teams.csv")

"""



import csv 
import math 
from models import Team



# -- Derby rivals------
DERBY_RIVALS = {
    "MC Alger"      : ["USM Alger", "CR Belouizdad"],
    "USM Alger"     : ["MC Alger",  "CR Belouizdad"],
    "CR Belouizdad" : ["MC Alger",  "USM Alger"],
}

def load_teams(filepath: str) -> list:
    """Read teams.csv → list[Team]. Injects derby_rivals from DERBY_RIVALS."""
    teams = []
    with open(filepath, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row["team"].strip()
            teams.append(Team(
                name=name,
                lat=float(row["latitude"]),
                lon=float(row["longitude"]),
            ))
    return teams

def haversine(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in km (Haversine formula)."""
    R = 6_371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a)), 2)

def build_distance_matrix(teams: list) -> dict:
    """Build symmetric distance dict keyed by team name strings.
    Access: dist[match.away.name][match.home.name]"""
    dist = {t.name: {} for t in teams}
    for a in teams:
        for b in teams:
            if a.name == b.name: dist[a.name][b.name] = 0.0
            elif b.name not in dist[a.name]:
                d = haversine(a.lat, a.lon, b.lat, b.lon)
                dist[a.name][b.name] = d; dist[b.name][a.name] = d
    return dist

def load_all(filepath: str) -> tuple:
    """Returns (list[Team], dist_matrix). One-line import for teammates."""
    t = load_teams(filepath)
    return t, build_distance_matrix(t)



# testing functions
if __name__ == "__main__":
    import sys, os
    csv_candidates = [
        "data/teams.csv",
        "../data/teams.csv",
        "teams.csv",
    ]
    csv_path = next((p for p in csv_candidates if os.path.exists(p)), None)
    if csv_path is None:
        print("ERROR: teams.csv not found. Run from project root.")
        sys.exit(1)
 
    print(f"Loading teams from: {csv_path}")
    teams, dist = load_all(csv_path)
 
 
    names = [t.name for t in teams]
    print("Full distance matrix (km):")
    header = f"{'':22}" + "".join(f"{n[:10]:>12}" for n in names)
    print(header)
    for a in names:
        row = f"{a[:22]:22}" + "".join(f"{dist[a][b]:>12.1f}" for b in names)
        print(row)
