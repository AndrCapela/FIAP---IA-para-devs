# -*- coding: utf-8 -*-
"""
Módulo de Algoritmo Genético e Modelagem VRP para Otimização de Rotas Médicas
Tech Challenge - Fase 2 (Projeto 2: Otimização de Rotas para Distribuição de Medicamentos e Insumos)

Este módulo contém:
1. A estrutura de dados `DeliveryPoint` (unidades hospitalares / pacientes);
2. A função `split_route_into_vehicles` que suporta tanto frota homogênea quanto
   FROTA HETEROGÊNEA (cada veículo com sua própria capacidade em kg e autonomia máxima em px);
3. A função de avaliação multicritério (`evaluate_solution_details` e `calculate_fitness`);
4. Os operadores do Algoritmo Genético (Seleção por Torneio/Roleta, Order Crossover OX,
   Mutação 2-opt + Swap + Prioridade) e o gerador passo a passo `run_genetic_algorithm`.
"""

import random
import math
import copy
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional, Generator


# ==============================================================================
# 1. REPRESENTAÇÃO DOS PONTOS DE ENTREGA E ESTRUTURAS DE DADOS
# ==============================================================================

PRIORITY_DEPOT = 0     # Ponto de partida/retorno (Hospital Central / Centro de Distribuição)
PRIORITY_REGULAR = 1   # Insumos regulares (ex.: luvas, gazes, seringas, soro fisiológico)
PRIORITY_URGENT = 2    # Medicamentos urgentes (ex.: antibióticos, insulina refrigerada)
PRIORITY_CRITICAL = 3  # Medicamentos críticos / emergência (ex.: bolsas de sangue, UTI, quimioterápicos)

PRIORITY_LABELS = {
    PRIORITY_DEPOT: "Depósito Central",
    PRIORITY_REGULAR: "Regular",
    PRIORITY_URGENT: "Urgente",
    PRIORITY_CRITICAL: "Crítico (UTI/Emergência)"
}


@dataclass(frozen=True)
class DeliveryPoint:
    """
    Representa uma unidade hospitalar, clínica ou residência de paciente (um "gene" da rota).
    Usamos `frozen=True` para que o objeto seja imutável e possa ser comparado diretamente
    nos operadores de cruzamento (`gene not in child`).
    """
    id: int                       # Identificador único (0 = Hospital Central)
    name: str                     # Nome da unidade de saúde ou paciente domiciliar
    x: int                        # Coordenada X na tela (em pixels)
    y: int                        # Coordenada Y na tela (em pixels)
    demand_kg: float              # Peso da entrega em quilogramas (kg)
    priority: int                 # Nível de prioridade: 1 (Regular), 2 (Urgente), 3 (Crítico)
    item_description: str = ""    # Descrição do medicamento/insumo entregue
    lat: float = -23.5505         # Latitude real aproximada (para o mapa geográfico)
    lon: float = -46.6333         # Longitude real aproximada (para o mapa geográfico)

    @property
    def pos(self) -> Tuple[int, int]:
        return (self.x, self.y)


# Mantemos o dicionário `default_problems` original para retrocompatibilidade
default_problems = {
    5: [(733, 251), (706, 87), (546, 97), (562, 49), (576, 253)],
    10: [(470, 169), (602, 202), (754, 239), (476, 233), (468, 301), (522, 29), (597, 171), (487, 325), (746, 232), (558, 136)],
    12: [(728, 67), (560, 160), (602, 312), (712, 148), (535, 340), (720, 354), (568, 300), (629, 260), (539, 46), (634, 343), (491, 135), (768, 161)],
    15: [(512, 317), (741, 72), (552, 50), (772, 346), (637, 12), (589, 131), (732, 165), (605, 15), (730, 38), (576, 216), (589, 381), (711, 387), (563, 228), (494, 22), (787, 288)]
}


def get_hospital_scenario() -> Tuple[DeliveryPoint, List[DeliveryPoint]]:
    """
    Cria o cenário hospitalar pré-definido realista com:
    - 1 Hospital Universitário Central (Depósito de onde saem os veículos);
    - 14 pontos de entrega entre UTIs, Pronto-Socorros, UPAs, UBS e pacientes em Home Care.
    """
    depot = DeliveryPoint(
        id=0,
        name="Hospital Universitário Central (CD)",
        x=760, y=300,
        demand_kg=0.0,
        priority=PRIORITY_DEPOT,
        item_description="Centro de Distribuição Farmacêutica",
        lat=-23.5587, lon=-46.6623
    )

    deliveries = [
        DeliveryPoint(
            id=1, name="UTI Cardio - Anexo Sul",
            x=710, y=420, demand_kg=12.0, priority=PRIORITY_CRITICAL,
            item_description="Hemoderivados e Vasopressores (UTI)",
            lat=-23.5989, lon=-46.6476
        ),
        DeliveryPoint(
            id=2, name="Pronto Socorro Norte",
            x=740, y=110, demand_kg=18.0, priority=PRIORITY_CRITICAL,
            item_description="Kit Intubação e Sedativos de Emergência",
            lat=-23.4950, lon=-46.6250
        ),
        DeliveryPoint(
            id=3, name="Centro Oncológico Leste",
            x=960, y=260, demand_kg=10.0, priority=PRIORITY_CRITICAL,
            item_description="Quimioterápicos Termolábeis",
            lat=-23.5420, lon=-46.5600
        ),
        DeliveryPoint(
            id=4, name="Maternidade Universitária",
            x=610, y=210, demand_kg=15.0, priority=PRIORITY_URGENT,
            item_description="Antibióticos Pediátricos e Surfactante",
            lat=-23.5320, lon=-46.7150
        ),
        DeliveryPoint(
            id=5, name="Home Care - Paciente 01 (Insulina)",
            x=850, y=170, demand_kg=5.0, priority=PRIORITY_URGENT,
            item_description="Insulina Glargina Refrigerada",
            lat=-23.5180, lon=-46.5980
        ),
        DeliveryPoint(
            id=6, name="UPA Zona Oeste",
            x=520, y=320, demand_kg=22.0, priority=PRIORITY_URGENT,
            item_description="Analgésicos Injetáveis e Antitérmicos",
            lat=-23.5650, lon=-46.7550
        ),
        DeliveryPoint(
            id=7, name="Home Care - Paciente 02 (Pós-Cirúrgico)",
            x=880, y=410, demand_kg=6.0, priority=PRIORITY_URGENT,
            item_description="Anticoagulantes e Curativos Especiais",
            lat=-23.5950, lon=-46.5850
        ),
        DeliveryPoint(
            id=8, name="UBS Vila Mariana",
            x=790, y=490, demand_kg=25.0, priority=PRIORITY_REGULAR,
            item_description="Soro Fisiológico, Gazes e Luvas",
            lat=-23.6180, lon=-46.6350
        ),
        DeliveryPoint(
            id=9, name="UBS Santana",
            x=640, y=90, demand_kg=20.0, priority=PRIORITY_REGULAR,
            item_description="Vacinas de Rotina e Seringas Descartáveis",
            lat=-23.4850, lon=-46.6850
        ),
        DeliveryPoint(
            id=10, name="Ambulatório de Especialidades",
            x=920, y=100, demand_kg=16.0, priority=PRIORITY_REGULAR,
            item_description="Insumos Ambulatoriais e Ataduras",
            lat=-23.4920, lon=-46.5720
        ),
        DeliveryPoint(
            id=11, name="Laboratório Central de Análises",
            x=1020, y=360, demand_kg=14.0, priority=PRIORITY_REGULAR,
            item_description="Reagentes e Tubos de Coleta",
            lat=-23.5750, lon=-46.5350
        ),
        DeliveryPoint(
            id=12, name="UBS Pinheiros",
            x=560, y=470, demand_kg=19.0, priority=PRIORITY_REGULAR,
            item_description="Medicamentos de Uso Contínuo (Hipertensão)",
            lat=-23.6120, lon=-46.7250
        ),
        DeliveryPoint(
            id=13, name="Home Care - Paciente 03 (Oxigenoterapia)",
            x=510, y=150, demand_kg=15.0, priority=PRIORITY_CRITICAL,
            item_description="Cilindro Portátil de O2 e Broncodilatadores",
            lat=-23.5080, lon=-46.7480
        ),
        DeliveryPoint(
            id=14, name="Hospital Dia - Geriatria",
            x=1010, y=490, demand_kg=18.0, priority=PRIORITY_REGULAR,
            item_description="Fraldas Hospitalares, Soro e Equipo",
            lat=-23.6190, lon=-46.5420
        ),
    ]

    return depot, deliveries


def generate_random_hospital_scenario(
    n_deliveries: int,
    min_x: int = 480,
    max_x: int = 1060,
    min_y: int = 50,
    max_y: int = 550
) -> Tuple[DeliveryPoint, List[DeliveryPoint]]:
    """
    Gera um cenário hospitalar aleatório com `n_deliveries` pontos de entrega.
    """
    center_x = (min_x + max_x) // 2
    center_y = (min_y + max_y) // 2

    depot = DeliveryPoint(
        id=0,
        name="Hospital Central (Depósito)",
        x=center_x,
        y=center_y,
        demand_kg=0.0,
        priority=PRIORITY_DEPOT,
        item_description="Centro de Distribuição",
        lat=-23.5505,
        lon=-46.6333
    )

    deliveries = []
    priority_choices = [PRIORITY_CRITICAL, PRIORITY_URGENT, PRIORITY_REGULAR]
    priority_weights = [0.25, 0.35, 0.40]

    for i in range(1, n_deliveries + 1):
        px = random.randint(min_x, max_x)
        py = random.randint(min_y, max_y)
        prio = random.choices(priority_choices, weights=priority_weights, k=1)[0]
        demand = float(random.randint(5, 25))

        lat = -23.5505 - ((py - center_y) * 0.0003)
        lon = -46.6333 + ((px - center_x) * 0.0003)

        deliveries.append(
            DeliveryPoint(
                id=i,
                name=f"Unidade/Paciente #{i:02d}",
                x=px,
                y=py,
                demand_kg=demand,
                priority=prio,
                item_description=f"Insumo ({PRIORITY_LABELS[prio]})",
                lat=lat,
                lon=lon
            )
        )

    return depot, deliveries


def normalize_vehicles_specs(
    max_vehicles: int = 3,
    vehicle_capacity_kg: float = 85.0,
    vehicle_max_distance: float = 950.0,
    vehicles_specs: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Normaliza a configuração da frota de veículos.
    - Se `vehicles_specs` for passado (Etapa 2: cada veículo com sua própria capacidade e autonomia),
      utiliza os limites individuais de cada veículo;
    - Caso contrário, gera uma lista uniforme de `max_vehicles` veículos para manter total
      compatibilidade com chamadas antigas (`tsp.py`).
    """
    if vehicles_specs and len(vehicles_specs) > 0:
        normalized = []
        for idx, spec in enumerate(vehicles_specs, start=1):
            normalized.append({
                "vehicle_id": int(spec.get("vehicle_id", idx)),
                "name": str(spec.get("name", f"Veículo {idx}")),
                "capacity_kg": float(spec.get("capacity_kg", vehicle_capacity_kg)),
                "max_distance": float(spec.get("max_distance", vehicle_max_distance))
            })
        return normalized

    return [
        {
            "vehicle_id": idx,
            "name": f"Veículo {idx}",
            "capacity_kg": float(vehicle_capacity_kg),
            "max_distance": float(vehicle_max_distance)
        }
        for idx in range(1, max(1, max_vehicles) + 1)
    ]


# ==============================================================================
# 2. CÁLCULO DE DISTÂNCIA E DIVISÃO DE ROTAS POR VEÍCULO (FROTA HETEROGÊNEA)
# ==============================================================================

def calculate_distance(point1: Any, point2: Any) -> float:
    """
    Calcula a distância euclidiana entre dois pontos (`DeliveryPoint` ou tupla `(x, y)`).
    """
    x1, y1 = (point1.x, point1.y) if isinstance(point1, DeliveryPoint) else (point1[0], point1[1])
    x2, y2 = (point2.x, point2.y) if isinstance(point2, DeliveryPoint) else (point2[0], point2[1])
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def split_route_into_vehicles(
    chromosome: List[DeliveryPoint],
    depot: DeliveryPoint,
    max_vehicles: int = 3,
    vehicle_capacity_kg: float = 85.0,
    vehicle_max_distance: float = 950.0,
    vehicles_specs: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Decodifica uma sequência de entregas (cromossomo) dividindo-a entre os veículos disponíveis,
    respeitando a capacidade de carga (`capacity_kg`) e a autonomia (`max_distance`)
    INDIVIDUAL de cada veículo da frota!
    """
    if not chromosome:
        return []

    specs = normalize_vehicles_specs(
        max_vehicles=max_vehicles,
        vehicle_capacity_kg=vehicle_capacity_kg,
        vehicle_max_distance=vehicle_max_distance,
        vehicles_specs=vehicles_specs
    )
    total_fleet = len(specs)

    routes = []
    current_v_idx = 0
    current_stops: List[DeliveryPoint] = []
    current_load = 0.0
    current_distance = 0.0
    last_point = depot

    for point in chromosome:
        v_spec = specs[current_v_idx]
        v_cap = v_spec["capacity_kg"]
        v_aut = v_spec["max_distance"]

        dist_to_point = calculate_distance(last_point, point)
        dist_back_to_depot = calculate_distance(point, depot)

        would_exceed_capacity = (current_load + point.demand_kg) > v_cap
        would_exceed_autonomy = (current_distance + dist_to_point + dist_back_to_depot) > v_aut

        # Se o veículo atual atingiu seu limite individual de carga ou autonomia e ainda há outro veículo na frota:
        if current_stops and (would_exceed_capacity or would_exceed_autonomy) and (current_v_idx < total_fleet - 1):
            total_route_dist = current_distance + calculate_distance(last_point, depot)
            routes.append({
                "vehicle_id": v_spec["vehicle_id"],
                "vehicle_name": v_spec["name"],
                "capacity_limit_kg": v_cap,
                "autonomy_limit_px": v_aut,
                "stops": current_stops,
                "full_path": [depot] + current_stops + [depot],
                "load_kg": current_load,
                "distance": total_route_dist,
                "capacity_exceeded": max(0.0, current_load - v_cap),
                "autonomy_exceeded": max(0.0, total_route_dist - v_aut)
            })
            # Passa para o próximo veículo da frota (com seus próprios limites de carga e autonomia)
            current_v_idx += 1
            current_stops = [point]
            current_load = point.demand_kg
            current_distance = calculate_distance(depot, point)
            last_point = point
        else:
            current_stops.append(point)
            current_load += point.demand_kg
            current_distance += dist_to_point
            last_point = point

    # Fecha a rota do último veículo utilizado
    if current_stops:
        v_spec = specs[current_v_idx]
        v_cap = v_spec["capacity_kg"]
        v_aut = v_spec["max_distance"]
        total_route_dist = current_distance + calculate_distance(last_point, depot)
        routes.append({
            "vehicle_id": v_spec["vehicle_id"],
            "vehicle_name": v_spec["name"],
            "capacity_limit_kg": v_cap,
            "autonomy_limit_px": v_aut,
            "stops": current_stops,
            "full_path": [depot] + current_stops + [depot],
            "load_kg": current_load,
            "distance": total_route_dist,
            "capacity_exceeded": max(0.0, current_load - v_cap),
            "autonomy_exceeded": max(0.0, total_route_dist - v_aut)
        })

    return routes


# ==============================================================================
# 3. FUNÇÃO FITNESS MULTICRITÉRIO (DISTÂNCIA + PRIORIDADE + CAPACIDADE + AUTONOMIA)
# ==============================================================================

def evaluate_solution_details(
    path: List[Any],
    depot: DeliveryPoint = None,
    max_vehicles: int = 3,
    vehicle_capacity_kg: float = 85.0,
    vehicle_max_distance: float = 950.0,
    vehicles_specs: Optional[List[Dict[str, Any]]] = None,
    priority_penalty_weight: float = 0.35,
    capacity_penalty_weight: float = 40.0,
    autonomy_penalty_weight: float = 15.0
) -> Dict[str, Any]:
    """
    Avalia uma rota completa considerando:
    - Distância total percorrida pela frota;
    - Penalidade de prioridade (entregas críticas e urgentes devem ser visitadas no início das sub-rotas);
    - Penalidade de excesso de carga (comparado ao limite individual de cada veículo);
    - Penalidade de excesso de autonomia (comparado à autonomia individual de cada veículo).
    """
    if depot is None or (len(path) > 0 and not isinstance(path[0], DeliveryPoint)):
        distance = 0.0
        n = len(path)
        for i in range(n):
            distance += calculate_distance(path[i], path[(i + 1) % n])
        return {
            "fitness": distance,
            "total_distance": distance,
            "priority_penalty": 0.0,
            "capacity_penalty": 0.0,
            "autonomy_penalty": 0.0,
            "is_feasible": True,
            "routes": []
        }

    routes = split_route_into_vehicles(
        chromosome=path,
        depot=depot,
        max_vehicles=max_vehicles,
        vehicle_capacity_kg=vehicle_capacity_kg,
        vehicle_max_distance=vehicle_max_distance,
        vehicles_specs=vehicles_specs
    )

    total_distance = 0.0
    priority_penalty = 0.0
    capacity_penalty = 0.0
    autonomy_penalty = 0.0

    for route in routes:
        total_distance += route["distance"]
        capacity_penalty += route["capacity_exceeded"] * capacity_penalty_weight
        autonomy_penalty += route["autonomy_exceeded"] * autonomy_penalty_weight

        cumulative_dist = 0.0
        prev_point = depot
        for stop_index, stop in enumerate(route["stops"], start=1):
            cumulative_dist += calculate_distance(prev_point, stop)
            prev_point = stop

            if stop.priority == PRIORITY_CRITICAL:
                priority_penalty += (cumulative_dist * 1.2 + (stop_index - 1) * 45.0) * priority_penalty_weight
            elif stop.priority == PRIORITY_URGENT:
                priority_penalty += (cumulative_dist * 0.4 + (stop_index - 1) * 15.0) * priority_penalty_weight

    total_fitness = total_distance + priority_penalty + capacity_penalty + autonomy_penalty
    is_feasible = (capacity_penalty == 0.0) and (autonomy_penalty == 0.0)

    return {
        "fitness": total_fitness,
        "total_distance": total_distance,
        "priority_penalty": priority_penalty,
        "capacity_penalty": capacity_penalty,
        "autonomy_penalty": autonomy_penalty,
        "is_feasible": is_feasible,
        "routes": routes
    }


def calculate_fitness(
    path: List[Any],
    depot: DeliveryPoint = None,
    max_vehicles: int = 3,
    vehicle_capacity_kg: float = 85.0,
    vehicle_max_distance: float = 950.0,
    vehicles_specs: Optional[List[Dict[str, Any]]] = None
) -> float:
    """Retorna apenas o valor escalar do Fitness (menor = melhor)."""
    details = evaluate_solution_details(
        path=path,
        depot=depot,
        max_vehicles=max_vehicles,
        vehicle_capacity_kg=vehicle_capacity_kg,
        vehicle_max_distance=vehicle_max_distance,
        vehicles_specs=vehicles_specs
    )
    return details["fitness"]


# ==============================================================================
# 4. INICIALIZAÇÃO E OPERADORES DO ALGORITMO GENÉTICO
# ==============================================================================

def create_nearest_neighbor_individual(
    deliveries: List[DeliveryPoint],
    start_point: DeliveryPoint = None,
    prioritize_critical: bool = True
) -> List[DeliveryPoint]:
    """
    Constrói um indivíduo inicial usando a heurística do Vizinho Mais Próximo (Nearest Neighbor)
    ponderada opcionalmente pela prioridade médica.
    """
    unvisited = list(deliveries)
    individual = []
    current = start_point if start_point is not None else random.choice(unvisited)

    while unvisited:
        def score_candidate(candidate: DeliveryPoint) -> float:
            dist = calculate_distance(current, candidate)
            if prioritize_critical and isinstance(candidate, DeliveryPoint):
                priority_factor = 1.0 / (candidate.priority ** 0.8)
                return dist * priority_factor
            return dist

        next_point = min(unvisited, key=score_candidate)
        individual.append(next_point)
        unvisited.remove(next_point)
        current = next_point

    return individual


def generate_random_population(
    cities_location: List[Any],
    population_size: int,
    depot: DeliveryPoint = None,
    use_heuristic_seed: bool = True
) -> List[List[Any]]:
    """
    Gera a população inicial de rotas (aleatória ou semeada com Nearest Neighbor).
    """
    population = []

    if use_heuristic_seed and len(cities_location) >= 2 and isinstance(cities_location[0], DeliveryPoint):
        population.append(create_nearest_neighbor_individual(cities_location, depot, prioritize_critical=True))
        if population_size > 2:
            population.append(create_nearest_neighbor_individual(cities_location, depot, prioritize_critical=False))

    while len(population) < population_size:
        population.append(random.sample(cities_location, len(cities_location)))

    return population


def tournament_selection(
    population: List[List[Any]],
    fitness_values: List[float],
    tournament_size: int = 4
) -> List[Any]:
    """Seleção por Torneio: escolhe o melhor indivíduo dentre `tournament_size` sorteados."""
    indices = random.sample(range(len(population)), min(tournament_size, len(population)))
    best_idx = min(indices, key=lambda idx: fitness_values[idx])
    return population[best_idx]


def order_crossover(parent1: List[Any], parent2: List[Any]) -> List[Any]:
    """Operador Order Crossover (OX) que preserva permutações válidas sem repetição."""
    length = len(parent1)
    if length < 2:
        return copy.deepcopy(parent1)

    start_index = random.randint(0, length - 1)
    end_index = random.randint(start_index + 1, length)

    child = parent1[start_index:end_index]
    remaining_positions = [i for i in range(length) if i < start_index or i >= end_index]
    remaining_genes = [gene for gene in parent2 if gene not in child]

    for position, gene in zip(remaining_positions, remaining_genes):
        child.insert(position, gene)

    return child


def mutate(
    solution: List[Any],
    mutation_probability: float,
    mutation_intensity: int = 1
) -> List[Any]:
    """
    Operador de Mutação Híbrido:
    - 55%: Inversão de segmento (2-opt) para descruzar arestas;
    - 30%: Swap entre duas posições aleatórias;
    - 15%: Avanço de uma entrega crítica para o início da rota.
    """
    mutated_solution = list(solution)
    n = len(mutated_solution)

    if n < 2:
        return mutated_solution

    if random.random() < mutation_probability:
        for _ in range(max(1, mutation_intensity)):
            mutation_type = random.random()

            if mutation_type < 0.55:
                i = random.randint(0, n - 2)
                j = random.randint(i + 1, n - 1)
                mutated_solution[i:j + 1] = reversed(mutated_solution[i:j + 1])

            elif mutation_type < 0.85:
                i, j = random.sample(range(n), 2)
                mutated_solution[i], mutated_solution[j] = mutated_solution[j], mutated_solution[i]

            else:
                critical_indices = [
                    idx for idx, pt in enumerate(mutated_solution)
                    if isinstance(pt, DeliveryPoint) and pt.priority == PRIORITY_CRITICAL and idx > 0
                ]
                if critical_indices:
                    idx = random.choice(critical_indices)
                    prev_idx = random.randint(0, idx - 1)
                    mutated_solution[prev_idx], mutated_solution[idx] = mutated_solution[idx], mutated_solution[prev_idx]
                else:
                    index = random.randint(0, n - 2)
                    mutated_solution[index], mutated_solution[index + 1] = (
                        mutated_solution[index + 1],
                        mutated_solution[index]
                    )

    return mutated_solution


def sort_population(
    population: List[List[Any]],
    fitness: List[float]
) -> Tuple[List[List[Any]], List[float]]:
    """Ordena a população do menor Fitness (melhor solução) para o maior."""
    combined_lists = list(zip(population, fitness))
    sorted_combined_lists = sorted(combined_lists, key=lambda x: x[1])
    sorted_population, sorted_fitness = zip(*sorted_combined_lists)
    return list(sorted_population), list(sorted_fitness)


def run_genetic_algorithm(
    depot: DeliveryPoint,
    deliveries: List[DeliveryPoint],
    vehicles_specs: List[Dict[str, Any]],
    population_size: int = 120,
    n_generations: int = 160,
    mutation_probability: float = 0.45,
    mutation_intensity: int = 1,
    use_heuristic_seed: bool = True
) -> Generator[Dict[str, Any], None, None]:
    """
    Executa o Algoritmo Genético como um gerador (yield), emitindo o estado a cada geração
    para permitir visualização em tempo real na interface Web.
    """
    population = generate_random_population(
        cities_location=deliveries,
        population_size=population_size,
        depot=depot,
        use_heuristic_seed=use_heuristic_seed
    )

    for gen in range(1, n_generations + 1):
        pop_fitness = [
            calculate_fitness(ind, depot=depot, vehicles_specs=vehicles_specs)
            for ind in population
        ]
        population, pop_fitness = sort_population(population, pop_fitness)

        best_solution = population[0]
        second_best = population[1] if len(population) > 1 else population[0]

        if gen == 1 or gen % 2 == 0 or gen == n_generations:
            eval_details = evaluate_solution_details(
                path=best_solution,
                depot=depot,
                vehicles_specs=vehicles_specs
            )
            yield {
                "algorithm_name": "Algoritmo Genético (GA)",
                "step": gen,
                "total_steps": n_generations,
                "done": (gen == n_generations),
                "eval_details": eval_details,
                "second_best_coords": [[pt.x, pt.y] for pt in second_best]
            }

        if gen < n_generations:
            new_population = [population[0], population[1]] if len(population) > 1 else [population[0]]
            probability = 1.0 / (np.array(pop_fitness) + 1e-6)

            while len(new_population) < population_size:
                if random.random() < 0.7:
                    p1 = tournament_selection(population, pop_fitness, tournament_size=4)
                    p2 = tournament_selection(population, pop_fitness, tournament_size=4)
                else:
                    p1, p2 = random.choices(population, weights=probability, k=2)

                child = order_crossover(p1, p2)
                child = mutate(child, mutation_probability, mutation_intensity=mutation_intensity)
                new_population.append(child)

            population = new_population
