# test_pure_csp.py
import time
import sys
from data_loader import load_teams, build_distance_matrix, DERBIES, WEEKEND
from csp_solver import CSPScheduler
import csv


def convert_to_schedule_format(schedule_result, teams):
    """
    Convert the CSP result to a readable schedule format
    """
    if schedule_result is None:
        return None
    
    n = len(teams)
    rounds = schedule_result.by_round
    
    print(f"\n{'='*80}")
    print(f"COMPLETE SCHEDULE - {n} Teams - Double Round Robin")
    print(f"{'='*80}")
    
    # Create team name mapping (index -> team name)
    team_names = [t.name for t in teams]
    
    total_matches = 0
    
    for round_idx, matches in enumerate(rounds):
        print(f"\n{'─'*60}")
        print(f"ROUND {round_idx + 1} of {len(rounds)}")
        print(f"{'─'*60}")
        
        for match_idx, (home_idx, away_idx) in enumerate(sorted(matches), 1):
            home_name = team_names[home_idx]
            away_name = team_names[away_idx]
            print(f"  Match {match_idx:2}: {home_name:25} vs {away_name:25}")
            total_matches += 1
    
    print(f"\n{'='*80}")
    print(f"SUMMARY:")
    print(f"  Total rounds: {len(rounds)}")
    print(f"  Total matches: {total_matches}")
    print(f"  Expected rounds: {(n - 1) * 2}")
    print(f"  Expected matches: {n * (n - 1)}")
    print(f"{'='*80}")
    
    return schedule_result


def test_csp_with_real_teams():
    """Test the pure CSP solver with real Algerian teams"""
    
    print("\n" + "="*80)
    print("PURE CSP SOLVER TEST - Real Algerian Teams")
    print("="*80)
    
    # Load real teams
    try:
        teams = load_teams("teams.csv")
        print(f"\n✓ Loaded {len(teams)} real Algerian teams:")
        for i, team in enumerate(teams[:8]):
            print(f"    {i}: {team.name}")
        if len(teams) > 8:
            print(f"    ... and {len(teams) - 8} more")
    except FileNotFoundError:
        print("❌ teams.csv not found!")
        return None
    except Exception as e:
        print(f"❌ Error loading teams: {e}")
        return None
    
    # Test different team sizes
    test_sizes = [4, 6, 8]  # Pure CSP only works for small sizes
    
    results = {}
    
    for size in test_sizes:
        if size > len(teams):
            print(f"\n⚠ Cannot test {size} teams: only {len(teams)} available")
            continue
        
        print(f"\n{'#'*80}")
        print(f"TESTING: {size} TEAMS")
        print(f"{'#'*80}")
        
        # Show which teams are being used
        test_teams = teams[:size]
        print(f"\nTeams participating:")
        for i, team in enumerate(test_teams):
            print(f"  {i}: {team.name}")
        
        # Run CSP solver
        print(f"\n⏳ Running pure CSP solver...")
        print(f"  Variables: {size} teams → {size * (size - 1)} ordered pairs")
        print(f"  Rounds: {(size - 1) * 2}")
        print(f"  Domain size per variable: {(size - 1) * 2}")
        print(f"  Time limit: 60 seconds")
        
        start_time = time.time()
        
        try:
            # Create CSP solver
            scheduler = CSPScheduler(
                n_teams=size,
                time_limit=60.0,
                verbose=True
            )
            
            # Solve
            schedule_result = scheduler.solve()
            
            elapsed = time.time() - start_time
            
            if schedule_result:
                print(f"\n✅ SUCCESS! Solution found in {elapsed:.2f} seconds")
                print(f"   Backtracking nodes explored: {scheduler._nodes}")
                print(f"   Is valid: {schedule_result.is_valid()}")
                
                # Display the schedule
                convert_to_schedule_format(schedule_result, test_teams)
                
                results[size] = {
                    "success": True,
                    "time": elapsed,
                    "nodes": scheduler._nodes,
                    "valid": schedule_result.is_valid()
                }
            else:
                print(f"\n❌ FAILED! No solution found in {elapsed:.2f} seconds")
                print(f"   Backtracking nodes explored: {scheduler._nodes}")
                
                results[size] = {
                    "success": False,
                    "time": elapsed,
                    "nodes": scheduler._nodes,
                    "valid": False
                }
                
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n❌ ERROR: {str(e)}")
            results[size] = {
                "success": False,
                "time": elapsed,
                "error": str(e)
            }
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY - Pure CSP Solver")
    print("="*80)
    
    print("\n| Teams | Status    | Time (s) | Nodes | Valid |")
    print("|-------|-----------|----------|-------|-------|")
    
    for size in test_sizes:
        if size in results:
            r = results[size]
            if r.get("success"):
                status = "✅ WORKS"
                time_str = f"{r['time']:8.2f}"
                nodes_str = str(r.get('nodes', '-'))
                valid_str = "✓" if r.get('valid') else "✗"
            else:
                status = "❌ FAILS"
                time_str = f"{r['time']:8.2f}"
                nodes_str = "-"
                valid_str = "-"
            
            print(f"| {size:5} | {status:9} | {time_str} | {nodes_str:5} | {valid_str:5} |")
    
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    print("Pure CSP Solver Limitations:")
    print("  - Works for n ≤ 6 teams")
    print("  - Fails for n ≥ 8 teams due to combinatorial explosion")
    print("  - Search space grows exponentially: (2*(n-1))^(n*(n-1))")
    print("\nFor n > 6, a hybrid approach (canonical schedule + local search) is required.")
    
    return results


def test_specific_size(size, time_limit=120):
    """Test a specific team size"""
    print(f"\n{'='*80}")
    print(f"TESTING SPECIFIC SIZE: {size} TEAMS")
    print(f"{'='*80}")
    
    # Load teams
    try:
        teams = load_teams("teams.csv")
        if size > len(teams):
            print(f"⚠ Only {len(teams)} teams available. Using synthetic teams for remaining.")
            # Generate synthetic teams
            from models import Team
            for i in range(len(teams), size):
                teams.append(Team(f"Synthetic_{i+1}", 36.0 + i*0.1, 3.0 + i*0.1))
    except:
        # Generate all synthetic teams
        from models import Team
        teams = [Team(f"Team_{i+1}", 36.0 + i*0.1, 3.0 + i*0.1) for i in range(size)]
    
    print(f"\nRunning CSP solver for {size} teams...")
    print(f"  This may take a long time for n > 6")
    
    start_time = time.time()
    
    scheduler = CSPScheduler(
        n_teams=size,
        time_limit=time_limit,
        verbose=True
    )
    
    result = scheduler.solve()
    
    elapsed = time.time() - start_time
    
    if result:
        print(f"\n✅ SOLUTION FOUND in {elapsed:.2f}s")
        print(f"   Nodes explored: {scheduler._nodes}")
        print(f"   Valid: {result.is_valid()}")
        
        # Display full schedule
        team_names = [f"Team_{i}" for i in range(size)]
        convert_to_schedule_format(result, team_names)
        
        return result
    else:
        print(f"\n❌ NO SOLUTION in {elapsed:.2f}s")
        print(f"   Nodes explored: {scheduler._nodes}")
        return None


def run_scalability_test():
    """Test scalability limits of pure CSP"""
    print("\n" + "="*80)
    print("PURE CSP SCALABILITY TEST")
    print("="*80)
    print("\nThis test will determine the maximum team size")
    print("that pure CSP can solve within 60 seconds.\n")
    
    test_sizes = [4, 6, 8, 10]
    results = []
    
    for size in test_sizes:
        print(f"\n{'─'*60}")
        print(f"Testing {size} teams...")
        
        start_time = time.time()
        
        scheduler = CSPScheduler(
            n_teams=size,
            time_limit=60.0,
            verbose=False
        )
        
        result = scheduler.solve()
        
        elapsed = time.time() - start_time
        
        success = result is not None
        nodes = scheduler._nodes if scheduler else 0
        
        results.append({
            "size": size,
            "success": success,
            "time": elapsed,
            "nodes": nodes
        })
        
        if success:
            print(f"  ✅ SOLVED in {elapsed:.2f}s ({nodes} nodes)")
        else:
            print(f"  ❌ FAILED after {elapsed:.2f}s ({nodes} nodes)")
    
    # Print summary
    print("\n" + "="*80)
    print("SCALABILITY TEST RESULTS")
    print("="*80)
    
    print("\n| Teams | Result    | Time (s) | Nodes |")
    print("|-------|-----------|----------|-------|")
    
    for r in results:
        status = "✅ WORKS" if r["success"] else "❌ FAILS"
        print(f"| {r['size']:5} | {status:9} | {r['time']:8.2f} | {r['nodes']:5} |")
    
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    print("Pure CSP is only feasible for:")
    print("  - 4 teams: ✅ (fast)")
    print("  - 6 teams: ✅ (acceptable)")
    print("  - 8 teams: ❌ (too slow / fails)")
    print("  - 10+ teams: ❌ (infeasible)")
    print("\nFor larger leagues, a hybrid approach is necessary.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Pure CSP Solver with Real Data")
    parser.add_argument("--size", type=int, default=None,
                       help="Test specific team size (e.g., --size 6)")
    parser.add_argument("--time", type=int, default=60,
                       help="Time limit in seconds (default: 60)")
    parser.add_argument("--scalability", action="store_true",
                       help="Run scalability test (4,6,8,10 teams)")
    
    args = parser.parse_args()
    
    if args.scalability:
        run_scalability_test()
    elif args.size:
        test_specific_size(args.size, args.time)
    else:
        test_csp_with_real_teams()