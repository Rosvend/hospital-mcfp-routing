import pulp
import random
from typing import Dict, List, Tuple, Optional


class AmbulanceRoutingModel:
    """
    Modelo de optimización de flujo multimercancía para enrutamiento de ambulancias.

    """
    
    def __init__(self, opt_data):
        """
        Inicializa el modelo.
        
        Parámetros:
        - opt_data: objeto OptimizationData con la red vial (en osmnx)
        """
        self.data = opt_data
        self.model = None
        self.x_vars = {}  # Variables binarias x_ijk
        self.solution = None
        
        # Mapeo de severidad a commodity
        self.severity_map = {
            'Leve': 'Leve',
            'Media': 'Media', 
            'Crítica': 'Critica',
            'Critica': 'Critica'
        }
        
        # Cada emergencia es un commodity separado
        # commodity_id = (dest_node, severity_type)
        self.commodities = []
        for dest_node, severity in self.data.destinations:
            commodity = self.severity_map.get(severity, 'Leve')
            self.commodities.append((dest_node, commodity))
        
        # Mapeo de commodity a nodo destino
        self.commodity_destinations = {
            comm: dest for dest, comm in self.commodities
        }
    
    def set_parameters(self, costs=None, r_min=30, r_max=70):
        """
        Define parámetros del modelo.
        
        Parámetros:
        - costs: dict {tipo: α_k} costo operativo en $/hora
        - r_min, r_max: rango para velocidades requeridas en km/h
        """
        # Costos operativos α_k en $/hora
        self.costs = costs or {
            'Leve': 100,      # Ambulancia básica
            'Media': 250,     # Ambulancia intermedia  
            'Critica': 500    # Ambulancia crítica
        }
        
        # Generar velocidades requeridas r_k
        self.required_speeds = self._generate_required_speeds(r_min, r_max)
    
    def _generate_required_speeds(self, r_min, r_max):
        """
        Genera velocidades requeridas r_k según severidad.
        
        Críticas: velocidades altas (80-100% del rango superior)
        Medias: velocidades intermedias (50-90% del rango)
        Leves: velocidades moderadas (rango inferior)
        """
        speeds = {}
        for dest_node, severity_type in self.commodities:
            if severity_type == 'Critica':
                speed = random.uniform(r_max * 0.8, r_max)
            elif severity_type == 'Media':
                speed = random.uniform(
                    r_min + (r_max - r_min) * 0.4, 
                    r_max * 0.9
                )
            else:  # Leve
                speed = random.uniform(
                    r_min, 
                    r_min + (r_max - r_min) * 0.6
                )
            speeds[(dest_node, severity_type)] = speed
        return speeds
    
    def build_model(self):
        """
        Construye el modelo de optimización siguiendo la formulación matemática.
        """
        
        self.model = pulp.LpProblem("Ambulance_Routing", pulp.LpMinimize)
        
        # Crear variables
        self._create_variables()
        
        # Función objetivo
        self._set_objective()
        
        # Restricciones
        self._add_flow_conservation()
        self._add_speed_requirements()
        
        print(f"Modelo construido: {len(self.x_vars)} variables, "
              f"{len(self.model.constraints)} restricciones")
        
        return self.model
    
    def _create_variables(self):
        """
        Crea variables binarias x_ijk.
        
        x_ijk = 1 si el commodity k usa el arco (i,j)
        x_ijk = 0 en caso contrario
        """
        for (u, v, key) in self.data.edges:
            for commodity in self.commodities:
                var_name = f"x_{u}_{v}_{key}_{commodity[0]}_{commodity[1]}"
                self.x_vars[(u, v, key, commodity)] = pulp.LpVariable(
                    var_name, 
                    cat='Binary'
                )
    
    def _set_objective(self):
        """
        Define función objetivo: Min Z = Σ_k (α_k · Σ_(i,j) t_ij · x_ijk)
        
        Minimiza el costo total considerando:
        - α_k: costo operativo por hora del commodity k
        - t_ij: tiempo de viaje en el arco (i,j) en horas
        - x_ijk: 1 si se usa el arco, 0 si no
        """
        objective = pulp.lpSum([
            self.costs[commodity[1]] *                           # α_k ($/hora) basado en severidad
            self.data.edge_data[(u, v, key)]['travel_time'] *    # t_ij (segundos)
            (1.0 / 3600) *                                       # Convertir a horas
            self.x_vars[(u, v, key, commodity)]                  # x_ijk
            for (u, v, key) in self.data.edges
            for commodity in self.commodities
            if (u, v, key, commodity) in self.x_vars
        ])
        
        self.model += objective, "Total_Cost"
    
    def _add_flow_conservation(self):
        """
        Restricciones de conservación de flujo:
        
        Σ_j x_ijk - Σ_j x_jik = b_ik
        
        donde b_ik = +1 si i es origen
                   = -1 si i es destino del commodity k
                   = 0 en caso contrario
        """
        for commodity in self.commodities:
            destination = commodity[0]  # El nodo destino es el primer elemento de la tupla
            
            for node in self.data.nodes:
                # Flujo que sale
                outflow = pulp.lpSum([
                    self.x_vars[(node, v, key, commodity)]
                    for (u, v, key) in self.data.edges
                    if u == node and (node, v, key, commodity) in self.x_vars
                ])
                
                # Flujo que entra
                inflow = pulp.lpSum([
                    self.x_vars[(u, node, key, commodity)]
                    for (u, v, key) in self.data.edges
                    if v == node and (u, node, key, commodity) in self.x_vars
                ])
                
                # Balance según tipo de nodo
                if node == self.data.origin:
                    balance = 1   # Origen: sale una unidad
                elif node == destination:
                    balance = -1  # Destino: llega una unidad
                else:
                    balance = 0   # Intermedio: conservación
                
                constraint_name = f"flow_{node}_{commodity[0]}_{commodity[1]}"
                self.model += (outflow - inflow == balance, constraint_name)
    
    def _add_speed_requirements(self):
        """
        Restricciones de velocidad requerida:
        
        x_ijk · r_k ≤ c_ij  ∀(i,j) ∈ A, ∀k ∈ K
        
        Si el commodity k usa el arco (i,j), entonces su velocidad
        requerida r_k debe ser menor o igual a la capacidad c_ij del arco.
        
        Esta restricción se puede expresar también como:
        r_k · x_ijk ≤ c_ij
        
        que es equivalente pero más clara para PuLP.
        """
        for (u, v, key) in self.data.edges:
            edge_data = self.data.edge_data[(u, v, key)]
            capacity = edge_data['capacity']  # c_ij en km/h
            
            for commodity in self.commodities:
                if (u, v, key, commodity) not in self.x_vars:
                    continue
                
                required_speed = self.required_speeds[commodity]  # r_k
                
                # r_k · x_ijk ≤ c_ij
                constraint_name = f"speed_{u}_{v}_{key}_{commodity}"
                self.model += (
                    required_speed * self.x_vars[(u, v, key, commodity)] <= capacity,
                    constraint_name
                )
    
    def solve(self, time_limit=60):
        """
        Resuelve el modelo.
        
        Parámetros:
        - time_limit: tiempo máximo en segundos (default 60)
        
        Retorna True si encuentra solución óptima.
        """
        if self.model is None:
            print("Error: Construye el modelo primero con build_model()")
            return False
        
        # Resolver con límite de tiempo
        status = self.model.solve(
            pulp.PULP_CBC_CMD(msg=0, timeLimit=time_limit)
        )
        
        if status == pulp.LpStatusOptimal:
            print(f"Solución óptima encontrada")
            print(f"Costo total: ${pulp.value(self.model.objective):.2f}")
            self.solution = self._extract_solution()
            return True
        else:
            print(f"No se encontró solución óptima: {pulp.LpStatus[status]}")
            return False
    
    def _extract_solution(self):
        """Extrae las rutas de las variables x_ijk."""
        routes = {commodity: [] for commodity in self.commodities}
        
        for (u, v, key, commodity), var in self.x_vars.items():
            if var.varValue and var.varValue > 0.5:
                routes[commodity].append((u, v, key))
        
        return routes
    
    def get_routes_as_paths(self):
        """
        Convierte rutas (arcos) a caminos (nodos ordenados).
        
        Retorna: {commodity: [nodo1, nodo2, ..., destino]}
        """
        if self.solution is None:
            print("Error: Resuelve el modelo primero")
            return None
        
        paths = {}
        for commodity in self.commodities:
            arcs = self.solution[commodity]
            if not arcs:
                paths[commodity] = []
                continue
            
            # Construir camino desde el origen
            arc_dict = {u: v for u, v, _ in arcs}
            path = [self.data.origin]
            current = self.data.origin
            
            while current in arc_dict:
                current = arc_dict[current]
                path.append(current)
            
            paths[commodity] = path
        
        return paths
    
    def get_solution_summary(self):
        """
        Retorna resumen detallado de la solución.
        """
        if self.solution is None:
            return None
        
        summary = {}
        
        for commodity in self.commodities:
            arcs = self.solution[commodity]
            if not arcs:
                continue
            
            dest_node, severity_type = commodity
            
            # Calcular métricas
            total_distance = sum(
                self.data.edge_data[(u, v, key)]['length'] / 1000
                for u, v, key in arcs
            )
            
            total_time = sum(
                self.data.edge_data[(u, v, key)]['travel_time']
                for u, v, key in arcs
            )
            
            cost = self.costs[severity_type] * (total_time / 3600)
            
            summary[commodity] = {
                'destination': dest_node,
                'severity': severity_type,
                'required_speed_kmh': self.required_speeds[commodity],
                'distance_km': total_distance,
                'time_seconds': total_time,
                'time_minutes': total_time / 60,
                'cost': cost,
                'num_segments': len(arcs)
            }
        
        return summary
    
    def print_solution(self):
        """Imprime resumen legible de la solución."""
        if self.solution is None:
            print("No hay solución disponible")
            return
        print("RESUMEN DE LA SOLUCIÓN")
        
        summary = self.get_solution_summary()
        
        for commodity in self.commodities:
            if commodity not in summary:
                print(f"\nEmergencia {commodity[0]} ({commodity[1]}): Sin ruta")
                continue
            
            info = summary[commodity]
            print(f"\nEMERGENCIA {info['destination']} ({info['severity'].upper()}):")
            print(f"  Velocidad requerida: {info['required_speed_kmh']:.1f} km/h")
            print(f"  Distancia: {info['distance_km']:.2f} km")
            print(f"  Tiempo: {info['time_minutes']:.2f} min")
            print(f"  Costo: ${info['cost']:.2f}")
            print(f"  Segmentos: {info['num_segments']}")
        
        total = pulp.value(self.model.objective)
        print(f"\nCOSTO TOTAL DEL SISTEMA: ${total:.2f}")
