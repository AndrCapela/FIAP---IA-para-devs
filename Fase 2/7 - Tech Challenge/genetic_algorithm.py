# -*- coding: utf-8 -*-
"""
Módulo de Algoritmo Genético para Otimização de Rotas Médicas (TSP / VRP Hospitalar)
Tech Challenge - Fase 2 (Projeto 2: Otimização de Rotas para Distribuição de Medicamentos e Insumos)

Este módulo foi construído a partir do arquivo `genetic_algorithm.py` original fornecido na disciplina,
sendo expandido e comentado detalhadamente para atender aos requisitos do hospital universitário:
1. Representação genética adequada para pontos de entrega hospitalares;
2. Restrições realistas:
   - Diferentes prioridades de entrega (Crítico, Urgente, Regular);
   - Capacidade máxima de carga por veículo (em kg);
   - Autonomia máxima por veículo (distância máxima percorrida por viagem);
   - Múltiplos veículos saindo e retornando ao Hospital Central (VRP - Vehicle Routing Problem);
3. Operadores genéticos especializados:
   - Inicialização híbrida (Aleatória + Heurística Nearest Neighbor com Prioridade);
   - Seleção por Torneio e Seleção por Roleta (proporcional ao inverso do Fitness);
   - Cruzamento Order Crossover (OX) preservando a validade das rotas sem repetir cidades;
   - Mutação combinada (Swap + Inversão de segmento / 2-opt com intensidade configurável).
"""

import random
import math
import copy
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any


# ==============================================================================
# 1. REPRESENTAÇÃO DOS PONTOS DE ENTREGA E ESTRUTURAS DE DADOS
# ==============================================================================

# Constantes de Níveis de Prioridade para facilitar a leitura do código
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
    no operador de Order Crossover (`gene not in child`), exatamente como as tuplas `(x, y)`
    do código original `tsp.py`.
    """
    id: int                       # Identificador único (0 = Hospital Central)
    name: str                     # Nome da unidade de saúde ou paciente domiciliar
    x: int                        # Coordenada X na tela do Pygame (em pixels)
    y: int                        # Coordenada Y na tela do Pygame (em pixels)
    demand_kg: float              # Peso da entrega em quilogramas (kg)
    priority: int                 # Nível de prioridade: 1 (Regular), 2 (Urgente), 3 (Crítico)
    item_description: str = ""    # Descrição do medicamento/insumo entregue
    lat: float = -23.5505         # Latitude real aproximada (para geração de mapa interativo)
    lon: float = -46.6333         # Longitude real aproximada (para geração de mapa interativo)

    @property
    def pos(self) -> Tuple[int, int]:
        """Retorna a tupla (x, y) para compatibilidade direta com funções de desenho."""
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
    - 14 pontos de entrega entre Unidades de Pronto Atendimento (UPAs), UTIs,
      Unidades Básicas de Saúde (UBS) e pacientes em atendimento domiciliar (Home Care).

    As coordenadas (x, y) estão mapeadas para a área de mapa do Pygame (X entre 480 e 1060, Y entre 50 e 550),
    enquanto (lat, lon) representam coordenadas reais na região metropolitana de São Paulo.
    """
    # Ponto 0: Hospital Central (Depósito) posicionado estrategicamente próximo ao centro do mapa
    depot = DeliveryPoint(
        id=0,
        name="Hospital Universitário Central (CD)",
        x=760, y=300,
        demand_kg=0.0,
        priority=PRIORITY_DEPOT,
        item_description="Centro de Distribuição Farmacêutica",
        lat=-23.5587, lon=-46.6623  # Região Clínicas / Pinheiros
    )

    # Lista de entregas que precisam ser realizadas pelos veículos da frota
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
    Gera um cenário hospitalar aleatório caso o usuário deseje testar com diferentes
    quantidades de pontos ou disposições geográficas aleatórias.
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
    # Distribuição realista de prioridades: 25% Crítico, 35% Urgente, 40% Regular
    priority_choices = [PRIORITY_CRITICAL, PRIORITY_URGENT, PRIORITY_REGULAR]
    priority_weights = [0.25, 0.35, 0.40]

    for i in range(1, n_deliveries + 1):
        px = random.randint(min_x, max_x)
        py = random.randint(min_y, max_y)
        prio = random.choices(priority_choices, weights=priority_weights, k=1)[0]
        demand = float(random.randint(5, 25))

        # Converte deslocamento de pixels em deslocamento aproximado de lat/lon para o mapa
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


# ==============================================================================
# 2. CÁLCULO DE DISTÂNCIA E DIVISÃO DE ROTAS POR VEÍCULO (VRP)
# ==============================================================================

def calculate_distance(point1: Any, point2: Any) -> float:
    """
    Calcula a distância euclidiana entre dois pontos.
    Aceita tanto objetos `DeliveryPoint` quanto tuplas `(x, y)` do código original.
    """
    x1, y1 = (point1.x, point1.y) if isinstance(point1, DeliveryPoint) else (point1[0], point1[1])
    x2, y2 = (point2.x, point2.y) if isinstance(point2, DeliveryPoint) else (point2[0], point2[1])
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def split_route_into_vehicles(
    chromosome: List[DeliveryPoint],
    depot: DeliveryPoint,
    max_vehicles: int = 3,
    vehicle_capacity_kg: float = 85.0,
    vehicle_max_distance: float = 950.0
) -> List[Dict[str, Any]]:
    """
    Decodifica um cromossomo (sequência permutada de entregas) dividindo-o em rotas
    para múltiplos veículos (VRP - Vehicle Routing Problem).

    Como funciona a divisão:
    - Cada veículo parte do `depot` (Hospital Central) e começa a atender os pontos na ordem
      definida pelo cromossomo.
    - Antes de adicionar a próxima entrega ao veículo atual, verificamos:
      1) Se o peso acumulado (`current_load + point.demand_kg`) ultrapassaria a capacidade do veículo;
      2) Se a distância total da viagem (incluindo o retorno obrigatório ao Hospital Central)
         ultrapassaria a autonomia máxima (`vehicle_max_distance`).
    - Se algum limite for excedido e ainda houver veículos disponíveis na frota (`len(routes) < max_vehicles`),
      o veículo atual retorna ao Hospital Central e o próximo veículo assume a partir dali!
    - Caso todos os veículos da frota já estejam em uso, o último veículo é forçado a absorver
      as entregas restantes, e o excesso de carga/distância será fortemente penalizado na função Fitness.
    """
    if not chromosome:
        return []

    routes = []
    current_stops: List[DeliveryPoint] = []
    current_load = 0.0
    current_distance = 0.0
    last_point = depot

    for point in chromosome:
        dist_to_point = calculate_distance(last_point, point)
        dist_back_to_depot = calculate_distance(point, depot)

        # Verifica se adicionar este ponto excede a capacidade de carga ou a autonomia do veículo atual
        would_exceed_capacity = (current_load + point.demand_kg) > vehicle_capacity_kg
        would_exceed_autonomy = (current_distance + dist_to_point + dist_back_to_depot) > vehicle_max_distance

        # Se já temos paradas no veículo atual, algum limite foi atingido e ainda há veículos livres na frota:
        if current_stops and (would_exceed_capacity or would_exceed_autonomy) and (len(routes) < max_vehicles - 1):
            # Fecha a rota do veículo atual retornando ao Hospital Central
            total_route_dist = current_distance + calculate_distance(last_point, depot)
            routes.append({
                "vehicle_id": len(routes) + 1,
                "stops": current_stops,
                "full_path": [depot] + current_stops + [depot],
                "load_kg": current_load,
                "distance": total_route_dist,
                "capacity_exceeded": max(0.0, current_load - vehicle_capacity_kg),
                "autonomy_exceeded": max(0.0, total_route_dist - vehicle_max_distance)
            })
            # Inicia um novo veículo saindo do Hospital Central
            current_stops = [point]
            current_load = point.demand_kg
            current_distance = calculate_distance(depot, point)
            last_point = point
        else:
            # Continua no mesmo veículo
            current_stops.append(point)
            current_load += point.demand_kg
            current_distance += dist_to_point
            last_point = point

    # Fecha a rota do último veículo utilizado
    if current_stops:
        total_route_dist = current_distance + calculate_distance(last_point, depot)
        routes.append({
            "vehicle_id": len(routes) + 1,
            "stops": current_stops,
            "full_path": [depot] + current_stops + [depot],
            "load_kg": current_load,
            "distance": total_route_dist,
            "capacity_exceeded": max(0.0, current_load - vehicle_capacity_kg),
            "autonomy_exceeded": max(0.0, total_route_dist - vehicle_max_distance)
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
    priority_penalty_weight: float = 0.35,
    capacity_penalty_weight: float = 40.0,
    autonomy_penalty_weight: float = 15.0
) -> Dict[str, Any]:
    """
    Avalia detalhadamente um indivíduo (solução), retornando tanto o valor final de Fitness
    quanto cada componente de custo separadamente (para exibição no painel e relatórios).

    Componentes do Fitness (problema de MINIMIZAÇÃO — quanto menor o valor, melhor a rota):
    1. `total_distance`: Soma das distâncias percorridas por todos os veículos (saindo e voltando ao Hospital Central).
    2. `priority_penalty`: Penaliza entregas Críticas (prioridade 3) e Urgentes (prioridade 2) que demoram
       para ser atendidas. Quanto maior a distância acumulada do veículo até chegar a um ponto crítico/urgente,
       maior a penalidade. Isso faz o Algoritmo Genético priorizar hospitais/pacientes críticos no início da rota!
    3. `capacity_penalty`: Penalidade pesada caso algum veículo exceda `vehicle_capacity_kg`.
    4. `autonomy_penalty`: Penalidade pesada caso algum veículo exceda `vehicle_max_distance`.
    """
    # Modo de compatibilidade simples caso `path` seja apenas uma lista de tuplas (x, y) sem depósito
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

    # Divide o cromossomo nas sub-rotas dos veículos disponíveis
    routes = split_route_into_vehicles(
        chromosome=path,
        depot=depot,
        max_vehicles=max_vehicles,
        vehicle_capacity_kg=vehicle_capacity_kg,
        vehicle_max_distance=vehicle_max_distance
    )

    total_distance = 0.0
    priority_penalty = 0.0
    capacity_penalty = 0.0
    autonomy_penalty = 0.0

    for route in routes:
        total_distance += route["distance"]
        capacity_penalty += route["capacity_exceeded"] * capacity_penalty_weight
        autonomy_penalty += route["autonomy_exceeded"] * autonomy_penalty_weight

        # Calcula a penalidade de prioridade ao longo da viagem deste veículo
        # Entregas críticas devem ser as primeiras paradas após sair do Hospital Central!
        cumulative_dist = 0.0
        prev_point = depot
        for stop_index, stop in enumerate(route["stops"], start=1):
            cumulative_dist += calculate_distance(prev_point, stop)
            prev_point = stop

            if stop.priority == PRIORITY_CRITICAL:
                # Peso elevado para entregas críticas: penaliza tanto a distância acumulada quanto a posição tardia
                priority_penalty += (cumulative_dist * 1.2 + (stop_index - 1) * 45.0) * priority_penalty_weight
            elif stop.priority == PRIORITY_URGENT:
                # Peso intermediário para entregas urgentes
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
    vehicle_max_distance: float = 950.0
) -> float:
    """
    Função principal de Fitness chamada pelo loop do Algoritmo Genético.
    Retorna um único número float representando o custo total da solução (menor = melhor).
    """
    details = evaluate_solution_details(
        path=path,
        depot=depot,
        max_vehicles=max_vehicles,
        vehicle_capacity_kg=vehicle_capacity_kg,
        vehicle_max_distance=vehicle_max_distance
    )
    return details["fitness"]


# ==============================================================================
# 4. INICIALIZAÇÃO DA POPULAÇÃO (ALEATÓRIA + HEURÍSTICA NEAREST NEIGHBOR)
# ==============================================================================

def create_nearest_neighbor_individual(
    deliveries: List[DeliveryPoint],
    start_point: DeliveryPoint = None,
    prioritize_critical: bool = True
) -> List[DeliveryPoint]:
    """
    Implementa a heurística do Vizinho Mais Próximo (Nearest Neighbor) combinada com
    prioridade médica (resolvendo o TODO deixado no `tsp.py` original!).

    Quando `prioritize_critical=True`, o construtor busca pontos que sejam próximos
    e tenham alta prioridade médica, gerando um indivíduo inicial de boa qualidade.
    """
    unvisited = list(deliveries)
    individual = []
    current = start_point if start_point is not None else random.choice(unvisited)

    while unvisited:
        def score_candidate(candidate: DeliveryPoint) -> float:
            dist = calculate_distance(current, candidate)
            if prioritize_critical and isinstance(candidate, DeliveryPoint):
                # Reduz a "distância percebida" de itens críticos para que sejam escolhidos antes
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
    Gera a população inicial de rotas.
    Por padrão, 95% da população é gerada de forma totalmente aleatória (garantindo diversidade genética)
    e até 5% (ou 2 indivíduos) utilizam a heurística Nearest Neighbor para acelerar a convergência inicial.
    """
    population = []

    # Se solicitado e estivermos trabalhando com DeliveryPoints, injeta sementes heurísticas
    if use_heuristic_seed and len(cities_location) >= 2 and isinstance(cities_location[0], DeliveryPoint):
        # Indivíduo 1: Vizinho mais próximo considerando prioridade crítica
        population.append(create_nearest_neighbor_individual(cities_location, depot, prioritize_critical=True))
        if population_size > 2:
            # Indivíduo 2: Vizinho mais próximo puramente por distância
            population.append(create_nearest_neighbor_individual(cities_location, depot, prioritize_critical=False))

    # Preenche o restante da população com permutações aleatórias
    while len(population) < population_size:
        population.append(random.sample(cities_location, len(cities_location)))

    return population


# ==============================================================================
# 5. OPERADORES GENÉTICOS: SELEÇÃO, CROSSOVER (OX) E MUTAÇÃO (SWAP + INVERSÃO)
# ==============================================================================

def tournament_selection(
    population: List[List[Any]],
    fitness_values: List[float],
    tournament_size: int = 4
) -> List[Any]:
    """
    Operador de Seleção por Torneio:
    Sorteia `tournament_size` indivíduos aleatoriamente da população e retorna aquele
    que possuir o menor (melhor) Fitness. É muito eficiente porque evita que um único
    super-indivíduo domine toda a roleta precocemente.
    """
    indices = random.sample(range(len(population)), min(tournament_size, len(population)))
    best_idx = min(indices, key=lambda idx: fitness_values[idx])
    return population[best_idx]


def order_crossover(parent1: List[Any], parent2: List[Any]) -> List[Any]:
    """
    Realiza o cruzamento Order Crossover (OX) entre dois pais para gerar um filho válido.
    O OX é ideal para problemas de roteamento (TSP/VRP) porque preserva a ordem relativa
    das paradas e garante que nenhuma unidade de saúde seja visitada duas vezes ou esquecida.
    """
    length = len(parent1)
    if length < 2:
        return copy.deepcopy(parent1)

    # Escolhe dois índices aleatórios que definem o segmento herdado do Pai 1
    start_index = random.randint(0, length - 1)
    end_index = random.randint(start_index + 1, length)

    # Inicializa o filho com a subsequência contínua do Pai 1
    child = parent1[start_index:end_index]

    # Preenche as posições restantes mantendo a ordem em que os genes aparecem no Pai 2
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
    Operador de Mutação Especializado para Roteamento (resolve o TODO do código original!).

    Implementa dois tipos complementares de mutação quando `random.random() < mutation_probability`:
    1. **Inversão de Segmento (2-opt / Inversion Mutation)**: Escolhe dois pontos da rota e inverte
       a ordem de todas as paradas entre eles. É excelente para "descruzar" linhas no mapa!
    2. **Troca de Posições (Swap Mutation)**: Escolhe duas paradas da rota (com destaque para
       adiantar paradas críticas) e troca suas posições.

    O parâmetro `mutation_intensity` controla quantas operações de mutação são aplicadas.
    """
    mutated_solution = list(solution)
    n = len(mutated_solution)

    if n < 2:
        return mutated_solution

    if random.random() < mutation_probability:
        for _ in range(max(1, mutation_intensity)):
            mutation_type = random.random()

            if mutation_type < 0.55:
                # Tipo 1 (55% das vezes): Inversão de segmento (2-opt) para eliminar cruzamentos na rota
                i = random.randint(0, n - 2)
                j = random.randint(i + 1, n - 1)
                mutated_solution[i:j + 1] = reversed(mutated_solution[i:j + 1])

            elif mutation_type < 0.85:
                # Tipo 2 (30% das vezes): Swap geral entre quaisquer duas paradas da rota
                i, j = random.sample(range(n), 2)
                mutated_solution[i], mutated_solution[j] = mutated_solution[j], mutated_solution[i]

            else:
                # Tipo 3 (15% das vezes): Mutação guiada por prioridade (puxa um item crítico uma posição para frente)
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
    """
    Ordena a população em ordem crescente de Fitness (do menor custo/melhor rota para o maior).
    """
    combined_lists = list(zip(population, fitness))
    sorted_combined_lists = sorted(combined_lists, key=lambda x: x[1])
    sorted_population, sorted_fitness = zip(*sorted_combined_lists)
    return list(sorted_population), list(sorted_fitness)


# ==============================================================================
# BLOCO DE TESTE RÁPIDO VIA TERMINAL (SEM PYGAME)
# ==============================================================================
if __name__ == '__main__':
    print("=== Teste Rápido do Algoritmo Genético Hospitalar (VRP) ===")
    depot_point, delivery_points = get_hospital_scenario()

    POP_SIZE = 100
    GENERATIONS = 120
    MUTATION_PROB = 0.4

    pop = generate_random_population(delivery_points, POP_SIZE, depot=depot_point)

    for gen in range(1, GENERATIONS + 1):
        pop_fitness = [calculate_fitness(ind, depot=depot_point) for ind in pop]
        pop, pop_fitness = sort_population(pop, pop_fitness)

        if gen == 1 or gen % 20 == 0 or gen == GENERATIONS:
            info = evaluate_solution_details(pop[0], depot=depot_point)
            print(
                f"Geração {gen:03d} | Fitness Total: {info['fitness']:.2f} | "
                f"Distância: {info['total_distance']:.1f} px | "
                f"Penalidade Prioridade: {info['priority_penalty']:.1f} | "
                f"Viável: {info['is_feasible']}"
            )

        # Elitismo: preserva os 2 melhores indivíduos intactos
        new_pop = [pop[0], pop[1]]
        while len(new_pop) < POP_SIZE:
            p1 = tournament_selection(pop, pop_fitness, tournament_size=4)
            p2 = tournament_selection(pop, pop_fitness, tournament_size=4)
            child = order_crossover(p1, p2)
            child = mutate(child, MUTATION_PROB, mutation_intensity=1)
            new_pop.append(child)

        pop = new_pop
