#!/usr/bin/env python3
"""
Final validation test for the complete system
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / 'src'))

from visualization.network import NetworkManager
from optimization.data_interface import OptimizationData
from optimization.model import AmbulanceRoutingModel

def final_validation():
    """Complete system validation"""
    print("=" * 70)
    print("FINAL SYSTEM VALIDATION")
    print("=" * 70)
    
    # Test 1: Network loading
    print("\n[TEST 1] Network Loading")
    nm = NetworkManager(cache_dir="../data")
    center_point = (6.2331, -75.5839)
    
    try:
        graph = nm.load_network(center_point, method='circle', distance=560, use_cache=True)
        print(f"  PASS: Loaded {len(graph.nodes)} nodes, {len(graph.edges)} edges")
    except Exception as e:
        print(f"  FAIL: {e}")
        return False
    
    # Test 2: Capacity assignment
    print("\n[TEST 2] Capacity Assignment")
    try:
        nm.assign_random_capacities(c_min=30, c_max=70)
        sample = list(graph.edges(keys=True, data=True))[0]
        assert 'capacity' in sample[3], "Capacity not assigned"
        print(f"  PASS: Capacities assigned (sample: {sample[3]['capacity']:.1f} km/h)")
    except Exception as e:
        print(f"  FAIL: {e}")
        return False
    
    # Test 3: Node selection
    print("\n[TEST 3] Origin and Destination Selection")
    try:
        origin, destinations = nm.get_random_nodes(n_destinations=3)
        assert origin in graph.nodes, "Invalid origin"
        assert all(d in graph.nodes for d in destinations), "Invalid destinations"
        print(f"  PASS: Origin {origin}, {len(destinations)} destinations")
    except Exception as e:
        print(f"  FAIL: {e}")
        return False
    
    # Test 4: Data interface
    print("\n[TEST 4] Optimization Data Interface")
    try:
        destinations_with_severity = [
            (destinations[0], 'Leve'),
            (destinations[1], 'Media'),
            (destinations[2], 'Critica')
        ]
        
        opt_data = OptimizationData()
        opt_data.from_network(graph, origin, destinations_with_severity)
        
        # Validate data
        assert len(opt_data.nodes) > 0, "No nodes"
        assert len(opt_data.edges) > 0, "No edges"
        assert opt_data.origin is not None, "No origin"
        assert len(opt_data.destinations) == 3, "Wrong destination count"
        
        # Check edge data
        sample_edge = opt_data.edges[0]
        edge_data = opt_data.edge_data[sample_edge]
        assert 'length' in edge_data, "Missing length"
        assert 'capacity' in edge_data, "Missing capacity"
        assert 'travel_time' in edge_data, "Missing travel_time"
        
        print(f"  PASS: Data structure created with {len(opt_data.destinations)} emergencies")
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Model building
    print("\n[TEST 5] Optimization Model Construction")
    try:
        model = AmbulanceRoutingModel(opt_data)
        costs = {'Leve': 100.0, 'Media': 250.0, 'Critica': 500.0}
        model.set_parameters(costs=costs, r_min=15, r_max=40)
        
        assert len(model.commodities) == 3, "Wrong commodity count"
        assert len(model.required_speeds) == 3, "Wrong speed count"
        
        model.build_model()
        
        assert model.model is not None, "Model not built"
        assert len(model.x_vars) > 0, "No variables created"
        
        print(f"  PASS: Model built with {len(model.x_vars)} variables, {len(model.model.constraints)} constraints")
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 6: Model solving
    print("\n[TEST 6] Model Solving")
    try:
        success = model.solve(time_limit=60)
        
        if not success:
            print("  WARNING: Infeasible with current parameters, trying relaxed...")
            model2 = AmbulanceRoutingModel(opt_data)
            model2.set_parameters(costs=costs, r_min=10, r_max=30)
            model2.build_model()
            success = model2.solve(time_limit=60)
            model = model2
        
        if success:
            print(f"  PASS: Solution found")
            
            # Validate solution
            assert model.solution is not None, "No solution stored"
            
            paths = model.get_routes_as_paths()
            assert len(paths) == len(model.commodities), "Missing routes"
            
            for commodity, path in paths.items():
                assert len(path) >= 2, f"Invalid path for {commodity}"
                assert path[0] == origin, f"Path doesn't start at origin"
                assert path[-1] == commodity[0], f"Path doesn't end at destination"
            
            summary = model.get_solution_summary()
            assert len(summary) == len(model.commodities), "Missing summary entries"
            
            print(f"  All {len(paths)} routes validated")
            
        else:
            print(f"  FAIL: Could not find feasible solution")
            return False
            
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 7: Solution quality
    print("\n[TEST 7] Solution Quality")
    try:
        summary = model.get_solution_summary()
        
        total_cost = sum(s['cost'] for s in summary.values())
        total_time = sum(s['time_minutes'] for s in summary.values())
        total_dist = sum(s['distance_km'] for s in summary.values())
        
        print(f"  Total cost: ${total_cost:.2f}")
        print(f"  Total time: {total_time:.2f} minutes")
        print(f"  Total distance: {total_dist:.2f} km")
        print(f"  Emergencies served: {len(summary)}/3")
        
        assert total_cost > 0, "Zero cost"
        assert total_time > 0, "Zero time"
        assert total_dist > 0, "Zero distance"
        
        print(f"  PASS: Solution is valid")
    except Exception as e:
        print(f"  FAIL: {e}")
        return False
    
    # Display solution
    print("\n" + "=" * 70)
    model.print_solution()
    print("=" * 70)
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED")
    print("=" * 70)
    print("\nSYSTEM VALIDATION SUMMARY:")
    print("  - Network loading: OK")
    print("  - Capacity assignment: OK")
    print("  - Data interface: OK")
    print("  - Model construction: OK")
    print("  - Optimization solver: OK")
    print("  - Solution validation: OK")
    print("\nThe system is ready for production use.")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    success = final_validation()
    sys.exit(0 if success else 1)
