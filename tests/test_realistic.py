#!/usr/bin/env python3
"""
Test with realistic parameters
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / 'src'))

from visualization.network import NetworkManager
from optimization.data_interface import OptimizationData
from optimization.model import AmbulanceRoutingModel
import random

def test_realistic_scenario():
    """Test with realistic, feasible parameters"""
    print("=" * 70)
    print("TEST WITH REALISTIC PARAMETERS")
    print("=" * 70)
    
    nm = NetworkManager(cache_dir="../data")
    center_point = (6.2331, -75.5839)
    
    graph = nm.load_network(center_point, method='circle', distance=560, use_cache=True)
    
    # Use realistic capacity range
    nm.assign_random_capacities(c_min=30, c_max=80)
    
    # Multiple emergencies
    origin, destinations = nm.get_random_nodes(n_destinations=5)
    random.seed(42)  # For reproducibility
    severities = ['Leve', 'Media', 'Critica']
    destinations_with_severity = [
        (dest, random.choice(severities)) for dest in destinations
    ]
    
    print(f"\nScenario: 5 emergencies")
    print(f"  Origin: {origin}")
    for i, (dest, sev) in enumerate(destinations_with_severity, 1):
        print(f"  Emergency {i}: {dest} ({sev})")
    
    opt_data = OptimizationData()
    opt_data.from_network(graph, origin, destinations_with_severity)
    
    model = AmbulanceRoutingModel(opt_data)
    
    # Use conservative speed requirements that ensure feasibility
    # Critical: up to 50 km/h
    # Medium: up to 45 km/h
    # Low: up to 40 km/h
    costs = {'Leve': 100.0, 'Media': 250.0, 'Critica': 500.0}
    model.set_parameters(costs=costs, r_min=20, r_max=50)
    
    print(f"\nSpeed requirements:")
    for comm, speed in model.required_speeds.items():
        print(f"  Emergency {comm[0]} ({comm[1]}): {speed:.1f} km/h")
    
    # Check feasibility
    capacities = [opt_data.edge_data[e]['capacity'] for e in opt_data.edges]
    print(f"\nNetwork capacity statistics:")
    print(f"  Min: {min(capacities):.1f} km/h")
    print(f"  Max: {max(capacities):.1f} km/h")
    print(f"  Mean: {sum(capacities)/len(capacities):.1f} km/h")
    
    # Build and solve
    model.build_model()
    print(f"\nModel: {len(model.x_vars)} variables, {len(model.model.constraints)} constraints")
    
    success = model.solve(time_limit=120)
    
    if success:
        print("\n" + "=" * 70)
        model.print_solution()
        print("=" * 70)
        
        # Analyze solution
        summary = model.get_solution_summary()
        
        print(f"\nSOLUTION ANALYSIS:")
        total_dist = sum(s['distance_km'] for s in summary.values())
        total_time = sum(s['time_minutes'] for s in summary.values())
        
        print(f"  Total distance: {total_dist:.2f} km")
        print(f"  Total time: {total_time:.2f} minutes")
        print(f"  Emergencies served: {len(summary)}/{len(destinations_with_severity)}")
        
        return True
    else:
        print("\nModel is infeasible - adjusting parameters...")
        
        # Try with even lower speeds
        model2 = AmbulanceRoutingModel(opt_data)
        model2.set_parameters(costs=costs, r_min=15, r_max=40)
        model2.build_model()
        
        success2 = model2.solve(time_limit=120)
        if success2:
            print("\nSOLUTION FOUND with adjusted parameters!")
            model2.print_solution()
            return True
        else:
            print("\nStill infeasible - may need larger network or fewer emergencies")
            return False

if __name__ == "__main__":
    test_realistic_scenario()
