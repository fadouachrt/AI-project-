
import json
import matplotlib.pyplot as plt
import numpy as np
import os

# Pistachio / green color palette
PISTACHIO = "#72c03f"
DARK_GREEN = "#387830"
LIGHT_GREEN = "#80d24d"
SOFT_GREEN = "#72be40"
FOREST_GREEN = '#3c7a34'

def load_csp_results(filename="csp_run_results.json"):
    
    if not os.path.exists(filename):
        print(f"Error: {filename} not found!")
        print("Please run test_csp.py first to generate results.")
        return None
    
    with open(filename, 'r') as f:
        data = json.load(f)
    
    print(f"Loaded results from: {filename}")
    print(f"Timestamp: {data['timestamp']}")
    print(f"Team sizes: {data['team_sizes']}")
    print(f"Execution times: {data['execution_times']}")
    
    return data


def draw_performance_graph(data):

    team_sizes = data['team_sizes']
    execution_times = data['execution_times']
    
    if not team_sizes:
        print("No data to plot!")
        return
    
    # Calculate growth factors
    growth_factors = []
    for i in range(1, len(execution_times)):
        factor = execution_times[i] / execution_times[i-1]
        growth_factors.append(factor)
    
    # Create figure with two subplots side by side
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle('CSP Solver Performance Analysis', fontsize=14, fontweight='bold', y=2.02)
    
    # Graph 1: Execution Time vs Team Size
    ax1.plot(team_sizes, execution_times, 'o-', color=PISTACHIO, linewidth=2.5, 
             markersize=9, markerfacecolor=DARK_GREEN, markeredgewidth=1.5,
             markeredgecolor=FOREST_GREEN)
    ax1.set_xlabel('Number of Teams', fontsize=11)
    ax1.set_ylabel('Execution Time (seconds)', fontsize=11)
    ax1.set_title('Execution Time vs Team Size', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.set_facecolor('#fafafa')
    
    # Add value labels on points
    for i, (n, t) in enumerate(zip(team_sizes, execution_times)):
        ax1.annotate(f'{t:.2f}s', xy=(n, t), xytext=(5, 5),
                     textcoords='offset points', fontsize=9, fontweight='bold',
                     bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))
    
    # Graph 2: Runtime Growth Between Sizes
    steps = [f'{team_sizes[i-1]}→{team_sizes[i]}' for i in range(1, len(team_sizes))]
    
    # Use different shades of green for bars
    bar_colors = [SOFT_GREEN, PISTACHIO, LIGHT_GREEN, SOFT_GREEN, PISTACHIO, LIGHT_GREEN]
    bars = ax2.bar(steps, growth_factors, color=bar_colors[:len(growth_factors)], 
                   edgecolor=DARK_GREEN, linewidth=1)
    ax2.set_xlabel('Team Size Increase', fontsize=11)
    ax2.set_ylabel('Growth Factor (x)', fontsize=11)
    ax2.set_title('Runtime Growth Between Sizes', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y', linestyle='--')
    ax2.set_facecolor('#fafafa')
    
    # Add value labels on bars
    for bar, val in zip(bars, growth_factors):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                 f'{val:.2f}x', ha='center', va='bottom', fontsize=10, fontweight='bold',
                 color=DARK_GREEN)
    
    # Add horizontal line at y=1
    ax2.axhline(y=1, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Baseline (1x)')
    ax2.legend(loc='upper left')
    
    plt.tight_layout()
    plt.savefig('csp_performance_graph.png', dpi=200, bbox_inches='tight', facecolor='white')
    plt.show()
    
    print(f"\n✓ Graph saved as: csp_performance_graph.png")


def main():
    """Main function to load data and draw graph"""
    
    
    data = load_csp_results("csp_run_results.json")
    
    if data is None:
        
        print("\nNo saved results found. Please enter your CSP results:")
        print("(leave team size empty to finish)")
        
        team_sizes = []
        execution_times = []
        
        while True:
            size_input = input("Team size (4, 6, 8, ...): ").strip()
            if not size_input:
                break
            time_input = input(f"Time for {size_input} teams (seconds): ").strip()
            if time_input:
                team_sizes.append(int(size_input))
                execution_times.append(float(time_input))
        
        if team_sizes:
            data = {
                "timestamp": "Manual entry",
                "team_sizes": team_sizes,
                "execution_times": execution_times
            }
        else:
            print("No data provided. Exiting.")
            return
    
    draw_performance_graph(data)


if __name__ == "__main__":
    
    try:
        import numpy as np
    except ImportError:
        print("Installing numpy...")
        import subprocess
        subprocess.check_call(['pip', 'install', 'numpy'])
        import numpy as np
    
    main()