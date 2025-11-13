#!/usr/bin/env python3
"""
Test scenarios for technical report
Pruebas del modelo de optimización con tres escenarios diferentes
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from visualization.network import NetworkManager
from optimization.data_interface import OptimizationData
from optimization.model import AmbulanceRoutingModel
import random

def print_separator(char="=", length=70):
    print(char * length)

def print_scenario_header(number, title):
    print_separator()
    print(f"ESCENARIO #{number}: {title}")
    print_separator()

def print_parameters(params):
    print("\nPARÁMETROS:")
    print(f"  • Área: Radio {params['distance']}m")
    print(f"  • Velocidades requeridas: R_min = {params['r_min']} km/h, R_max = {params['r_max']} km/h")
    print(f"  • Capacidades viales: C_min = {params['c_min']} km/h, C_max = {params['c_max']} km/h")
    print(f"  • Número de emergencias: K = {params['n_emergencies']}")
    print(f"  • Costos operativos:")
    print(f"      - Leve: ${params['cost_leve']:.0f}/h")
    print(f"      - Media: ${params['cost_media']:.0f}/h")
    print(f"      - Crítica: ${params['cost_critica']:.0f}/h")

def print_results(model, summary, success):
    print("\nRESULTADOS:")
    
    if not success:
        print("  ✗ No se encontró solución factible")
        print("  El modelo es INFACTIBLE con estos parámetros.")
        return
    
    print("  ✓ Solución óptima encontrada\n")
    
    # Estadísticas generales
    total_cost = sum(s['cost'] for s in summary.values())
    total_distance = sum(s['distance_km'] for s in summary.values())
    total_time = sum(s['time_minutes'] for s in summary.values())
    
    print(f"  Métricas Globales:")
    print(f"    • Costo Total: ${total_cost:.2f}")
    print(f"    • Distancia Total: {total_distance:.2f} km")
    print(f"    • Tiempo Total: {total_time:.2f} min")
    print(f"    • Emergencias atendidas: {len(summary)}")
    
    # Detalles por emergencia
    print(f"\n  Detalles por Emergencia:")
    for i, (commodity, info) in enumerate(summary.items(), 1):
        print(f"\n    Emergencia #{i} ({info['severity']}):")
        print(f"      - Velocidad requerida: {info['required_speed_kmh']:.1f} km/h")
        print(f"      - Distancia recorrida: {info['distance_km']:.2f} km")
        print(f"      - Tiempo de viaje: {info['time_minutes']:.2f} min")
        print(f"      - Costo operativo: ${info['cost']:.2f}")
        print(f"      - Segmentos de ruta: {info['num_segments']}")

def run_scenario(scenario_number, description, params):
    """Run a single test scenario"""
    
    print_scenario_header(scenario_number, description)
    print(f"\nDescripción: {params['description']}")
    print_parameters(params)
    
    # Initialize network
    nm = NetworkManager(cache_dir="../data")
    center_point = (6.2331, -75.5839)
    
    print(f"\nCargando red vial...")
    graph = nm.load_network(
        center_point, 
        method='circle', 
        distance=params['distance'], 
        use_cache=True
    )
    print(f"  Red cargada: {len(graph.nodes)} nodos, {len(graph.edges)} arcos")
    
    # Assign capacities
    random.seed(params['seed'])
    nm.assign_random_capacities(c_min=params['c_min'], c_max=params['c_max'])
    
    # Select emergencies
    origin, destinations = nm.get_random_nodes(n_destinations=params['n_emergencies'])
    
    # Assign severities
    severities = params['severities']
    destinations_with_severity = [
        (destinations[i], severities[i % len(severities)]) 
        for i in range(len(destinations))
    ]
    
    print(f"\nEmergencias generadas:")
    print(f"  Origen (base ambulancias): Nodo {origin}")
    for i, (dest, sev) in enumerate(destinations_with_severity, 1):
        print(f"  Emergencia {i}: Nodo {dest} - Severidad {sev}")
    
    # Create optimization data
    opt_data = OptimizationData()
    opt_data.from_network(graph, origin, destinations_with_severity)
    
    # Build model
    model = AmbulanceRoutingModel(opt_data)
    costs = {
        'Leve': params['cost_leve'],
        'Media': params['cost_media'],
        'Critica': params['cost_critica']
    }
    model.set_parameters(costs=costs, r_min=params['r_min'], r_max=params['r_max'])
    
    print(f"\nVelocidades requeridas generadas:")
    for comm, speed in model.required_speeds.items():
        print(f"  {comm[1]}: {speed:.1f} km/h")
    
    # Solve
    print(f"\nConstruyendo y resolviendo modelo...")
    model.build_model()
    print(f"  Variables: {len(model.x_vars)}")
    print(f"  Restricciones: {len(model.model.constraints)}")
    
    success = model.solve(time_limit=120)
    
    # Get results
    summary = model.get_solution_summary() if success else None
    
    # Print results
    print_results(model, summary, success)
    
    return success, summary

def main():
    """Run all three scenarios for the technical report"""
    
    print("\n")
    print_separator("=", 70)
    print("PRUEBAS DEL MODELO DE OPTIMIZACIÓN - REPORTE TÉCNICO")
    print("Multi-Commodity Flow Problem para Enrutamiento de Ambulancias")
    print_separator("=", 70)
    print("\n")
    
    # ========== SCENARIO 1: IDEAL (Low demand, high capacity) ==========
    scenario1_params = {
        'description': 'Baja demanda de emergencias y alta capacidad vial. Escenario ideal.',
        'distance': 560,
        'r_min': 15,
        'r_max': 35,
        'c_min': 50,
        'c_max': 90,
        'n_emergencies': 2,
        'cost_leve': 100.0,
        'cost_media': 250.0,
        'cost_critica': 500.0,
        'severities': ['Leve', 'Media'],
        'seed': 42
    }
    
    success1, summary1 = run_scenario(1, "ESCENARIO IDEAL", scenario1_params)
    
    print("\n" * 3)
    
    # ========== SCENARIO 2: MODERATE (Medium demand, medium capacity) ==========
    scenario2_params = {
        'description': 'Demanda moderada con capacidades medias. Escenario realista.',
        'distance': 560,
        'r_min': 18,
        'r_max': 40,
        'c_min': 40,
        'c_max': 80,
        'n_emergencies': 4,
        'cost_leve': 100.0,
        'cost_media': 250.0,
        'cost_critica': 500.0,
        'severities': ['Leve', 'Media', 'Critica', 'Media'],
        'seed': 123
    }
    
    success2, summary2 = run_scenario(2, "ESCENARIO MODERADO", scenario2_params)
    
    print("\n" * 3)
    
    # ========== SCENARIO 3: CRITICAL (High demand, limited capacity) ==========
    scenario3_params = {
        'description': 'Alta demanda de emergencias críticas con capacidad vial limitada. Escenario de estrés.',
        'distance': 560,
        'r_min': 25,
        'r_max': 50,
        'c_min': 40,
        'c_max': 80,
        'n_emergencies': 6,
        'cost_leve': 100.0,
        'cost_media': 250.0,
        'cost_critica': 500.0,
        'severities': ['Critica', 'Critica', 'Media', 'Critica', 'Media', 'Leve'],
        'seed': 456
    }
    
    success3, summary3 = run_scenario(3, "ESCENARIO CRÍTICO", scenario3_params)
    
    print("\n" * 3)
    
    # ========== SUMMARY ==========
    print_separator("=", 70)
    print("RESUMEN COMPARATIVO")
    print_separator("=", 70)
    print()
    
    print("Escenario | Emergencias | Estado      | Costo Total | Tiempo Total | Distancia Total")
    print("-" * 85)
    
    # Scenario 1
    status1 = "FACTIBLE ✓" if success1 else "INFACTIBLE ✗"
    cost1 = f"${sum(s['cost'] for s in summary1.values()):.2f}" if success1 else "N/A"
    time1 = f"{sum(s['time_minutes'] for s in summary1.values()):.2f} min" if success1 else "N/A"
    dist1 = f"{sum(s['distance_km'] for s in summary1.values()):.2f} km" if success1 else "N/A"
    print(f"    #1    |      2      | {status1:11} | {cost1:11} | {time1:12} | {dist1:15}")
    
    # Scenario 2
    status2 = "FACTIBLE ✓" if success2 else "INFACTIBLE ✗"
    cost2 = f"${sum(s['cost'] for s in summary2.values()):.2f}" if success2 else "N/A"
    time2 = f"{sum(s['time_minutes'] for s in summary2.values()):.2f} min" if success2 else "N/A"
    dist2 = f"{sum(s['distance_km'] for s in summary2.values()):.2f} km" if success2 else "N/A"
    print(f"    #2    |      4      | {status2:11} | {cost2:11} | {time2:12} | {dist2:15}")
    
    # Scenario 3
    status3 = "FACTIBLE ✓" if success3 else "INFACTIBLE ✗"
    cost3 = f"${sum(s['cost'] for s in summary3.values()):.2f}" if success3 else "N/A"
    time3 = f"{sum(s['time_minutes'] for s in summary3.values()):.2f} min" if success3 else "N/A"
    dist3 = f"{sum(s['distance_km'] for s in summary3.values()):.2f} km" if success3 else "N/A"
    print(f"    #3    |      6      | {status3:11} | {cost3:11} | {time3:12} | {dist3:15}")
    
    print()
    print_separator("=", 70)
    
    print("\n")
    print("ANÁLISIS:")
    feasible_count = sum([success1, success2, success3])
    print(f"  • Escenarios factibles: {feasible_count}/3")
    
    if success1:
        print(f"  • Escenario ideal (#1): Solución encontrada con bajo costo")
    if success2:
        print(f"  • Escenario moderado (#2): Solución encontrada con mayor demanda")
    if success3:
        print(f"  • Escenario crítico (#3): {'Solución encontrada bajo condiciones de estrés' if success3 else 'Infactible - recursos insuficientes'}")
    
    print("\n")
    print("="*70)
    print("FIN DE LAS PRUEBAS")
    print("="*70)
    print("\nLos resultados anteriores pueden copiarse directamente al documento de Word.")
    print()

if __name__ == "__main__":
    main()
