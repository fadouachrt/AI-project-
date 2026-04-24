import csv 
import math 
from pathlib import Path


_EARTH_RADIUS_KM = 6_371.0          # mean radius of Earth in kilometres


# call this function to load data for testing (you all need it)
def load_teams(filepath: str) -> dict:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"teams file not found: {filepath}")
    
    teams = {}
    with open(path, newline="", encoding="utf-8") as fileHandler:
        reader = csv.DictReader(fileHandler)

        required_cols = {"team", "latitude", "longitude"}

        if not required_cols.issubset(reader.fieldnames or []):
            missing = required_cols - set(reader.fieldnames or [])
            raise ValueError(f"CSV is missing required columns: {missing}")
 
        for row in reader:
            name = row["team"].strip()
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
            except ValueError:
                raise ValueError(
                    f"Cannot parse coordinates for team '{name}': "
                    f"lat={row['latitude']!r}, lon={row['longitude']!r}"
                )
            teams[name] = (lat, lon)
 
    return teams




#haversine distance implementation that returns distance in Km between 2 points on Earth
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:

    # Convert degrees to radians
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi       = math.radians(lat2 - lat1)
    dlambda    = math.radians(lon2 - lon1)
 
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
 
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
 
    return round(_EARTH_RADIUS_KM * c, 2)




# distances between each pair of teams as dictionary
def build_distance_matrix(teams_dict: dict) -> dict:
    team_names = list(teams_dict.keys())
    dist = {t: {} for t in team_names}
 
    for i, team_a in enumerate(team_names):
        lat1, lon1 = teams_dict[team_a]
        for team_b in team_names:
            if team_a == team_b:
                dist[team_a][team_b] = 0.0
            elif team_b in dist[team_a]:
                pass                                # already computed
            else:
                lat2, lon2 = teams_dict[team_b]
                d = haversine(lat1, lon1, lat2, lon2)
                dist[team_a][team_b] = d
                dist[team_b][team_a] = d            # symmetric
 
    return dist


# you may need this to load teams and distances at once 
def load_all(filepath: str) -> tuple:
    teams_dict  = load_teams(filepath)
    dist_matrix = build_distance_matrix(teams_dict)
    return teams_dict, dist_matrix
 


# this is a quick check for distances by Claude (may replaced by distance validator after)
def verify_distances(dist_matrix: dict) -> None:

    checks = [
        ("MC Alger",  "USM Alger",       "~5 km (same city)"),
        ("MC Alger",  "MC Oran",         "~360 km"),
        ("MC Alger",  "ES Setif",        "~280 km"),
        ("MC Alger",  "CS Constantine",  "~360 km"),
        ("MC Alger",  "JS Saoura",       "~940 km (south)"),
    ]
    print("\n=== Distance Matrix Spot-Check ===")
    for team_a, team_b, note in checks:
        if team_a in dist_matrix and team_b in dist_matrix[team_a]:
            d = dist_matrix[team_a][team_b]
            print(f"  {team_a:<20} → {team_b:<20} : {d:>8.1f} km   (expected {note})")
        else:
            print(f"  !! {team_a!r} or {team_b!r} not found in matrix")
    print()
 


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
 
    print(f"  → {len(teams)} teams loaded")
    verify_distances(dist)
 
    names = list(teams.keys())
    print("Full distance matrix (km):")
    header = f"{'':22}" + "".join(f"{n[:10]:>12}" for n in names)
    print(header)
    for a in names:
        row = f"{a[:22]:22}" + "".join(f"{dist[a][b]:>12.1f}" for b in names)
        print(row)


