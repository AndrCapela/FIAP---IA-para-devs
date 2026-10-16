# -*- coding: utf-8 -*-
"""
Orquestrador Principal de Algoritmos de Otimização de Rotas (Dispatcher / Selector)
Tech Challenge - Fase 2 (Projeto 2: Otimização de Rotas para Distribuição de Medicamentos e Insumos)

Este módulo centraliza a escolha e invocação dos diferentes algoritmos e heurísticas
de roteamento implementados em arquivos separados:
1. `genetic_algorithm.py`       -> Algoritmo Genético (GA)
2. `algo_ant_colony.py`         -> Ant Colony Optimization (ACO - Colônia de Formigas)
3. `algo_simulated_annealing.py`-> Simulated Annealing (Têmpera Simulada)
4. `algo_nearest_neighbor.py`   -> Nearest Neighbor (Vizinho Mais Próximo Multi-Start + 2-opt)
5. `algo_convex_hull.py`        -> Convex Hull Insertion (Envoltória Convexa + Busca Local)
"""

from typing import List, Dict, Any, Generator
from vrp_core import (
    DeliveryPoint,
    DEFAULT_PRIORITY_PENALTY_WEIGHT,
    DEFAULT_CAPACITY_PENALTY_WEIGHT,
    DEFAULT_AUTONOMY_PENALTY_WEIGHT
)
from genetic_algorithm import run_genetic_algorithm
from algo_nearest_neighbor import run_nearest_neighbor
from algo_convex_hull import run_convex_hull
from algo_ant_colony import run_ant_colony
from algo_simulated_annealing import run_simulated_annealing


AVAILABLE_ALGORITHMS: Dict[str, Dict[str, Any]] = {
    "genetic_algorithm": {
        "key": "genetic_algorithm",
        "title": "Algoritmo Genético (GA - Evolucionário)",
        "description": (
            "Evolui uma população de rotas usando Seleção por Torneio/Roleta, Order Crossover (OX) "
            "e Mutação Híbrida (2-opt + Swap + Prioridade Médica)."
        ),
        "module_file": "genetic_algorithm.py"
    },
    "ant_colony": {
        "key": "ant_colony",
        "title": "Ant Colony Optimization (ACO - Colônia de Formigas)",
        "description": (
            "Simula formigas artificiais que constroem rotas guiadas por trilhas de feromônio (tau) "
            "e visibilidade heurística ponderada pela urgência médica (eta)."
        ),
        "module_file": "algo_ant_colony.py"
    },
    "simulated_annealing": {
        "key": "simulated_annealing",
        "title": "Simulated Annealing (Têmpera Simulada + 2-opt)",
        "description": (
            "Meta-heurística inspirada no resfriamento térmico que explora a vizinhança 2-opt/Swap "
            "e aceita movimentos probabilísticos para escapar de ótimos locais."
        ),
        "module_file": "algo_simulated_annealing.py"
    },
    "nearest_neighbor": {
        "key": "nearest_neighbor",
        "title": "Nearest Neighbor (Vizinho Mais Próximo + 2-opt)",
        "description": (
            "Heurística construtiva Multi-Start que visita a entrega viável mais próxima "
            "ponderada pela prioridade médica e evolui ao longo das gerações com refinamento 2-opt."
        ),
        "module_file": "algo_nearest_neighbor.py"
    },
    "convex_hull": {
        "key": "convex_hull",
        "title": "Convex Hull (Envoltória Convexa + Inserção)",
        "description": (
            "Heurística geométrica que parte do polígono convexo externo e testa inserções "
            "e refinamentos locais ao longo das gerações."
        ),
        "module_file": "algo_convex_hull.py"
    }
}


def get_available_algorithms() -> List[Dict[str, Any]]:
    """Retorna a lista de algoritmos disponíveis e suas descrições."""
    return list(AVAILABLE_ALGORITHMS.values())


def dispatch_optimization(
    algorithm_key: str,
    depot: DeliveryPoint,
    deliveries: List[DeliveryPoint],
    vehicles_specs: List[Dict[str, Any]],
    params: Dict[str, Any]
) -> Generator[Dict[str, Any], None, None]:
    """
    Recebe a chave do algoritmo selecionado pelo usuário (`algorithm_key`), a configuração
    individual dos veículos (`vehicles_specs`) e os hiperparâmetros (`params`),
    monta os pesos de penalidade (`penalty_weights`) e invoca o gerador do algoritmo correspondente.
    """
    algo = algorithm_key.strip().lower()

    # Pesos configuráveis das penalidades na Função Fitness (repassados para qualquer um dos 5 algoritmos)
    penalty_weights = {
        "priority": max(0.0, float(params.get("priority_penalty_weight", DEFAULT_PRIORITY_PENALTY_WEIGHT))),
        "capacity": max(0.0, float(params.get("capacity_penalty_weight", DEFAULT_CAPACITY_PENALTY_WEIGHT))),
        "autonomy": max(0.0, float(params.get("autonomy_penalty_weight", DEFAULT_AUTONOMY_PENALTY_WEIGHT)))
    }

    # 1. ALGORITMO GENÉTICO
    if algo == "genetic_algorithm":
        pop_size = max(20, min(300, int(params.get("population_size", 120))))
        n_generations = max(10, min(500, int(params.get("n_generations", 160))))
        mutation_prob = float(params.get("mutation_probability", 0.45))
        mutation_intensity = max(1, min(5, int(params.get("mutation_intensity", 1))))
        use_seed = bool(params.get("use_heuristic_seed", True))

        yield from run_genetic_algorithm(
            depot=depot,
            deliveries=deliveries,
            vehicles_specs=vehicles_specs,
            population_size=pop_size,
            n_generations=n_generations,
            mutation_probability=mutation_prob,
            mutation_intensity=mutation_intensity,
            use_heuristic_seed=use_seed,
            penalty_weights=penalty_weights
        )

    # 2. ANT COLONY OPTIMIZATION (Colônia de Formigas)
    elif algo == "ant_colony":
        n_ants = max(5, min(100, int(params.get("n_ants", 35))))
        n_iterations = max(10, min(300, int(params.get("n_iterations", 80))))
        alpha = float(params.get("alpha", 1.0))
        beta = float(params.get("beta", 2.5))
        evaporation_rate = float(params.get("evaporation_rate", 0.15))

        yield from run_ant_colony(
            depot=depot,
            deliveries=deliveries,
            vehicles_specs=vehicles_specs,
            n_ants=n_ants,
            n_iterations=n_iterations,
            alpha=alpha,
            beta=beta,
            evaporation_rate=evaporation_rate,
            penalty_weights=penalty_weights
        )

    # 3. SIMULATED ANNEALING (Têmpera Simulada)
    elif algo == "simulated_annealing":
        n_iterations = max(20, min(500, int(params.get("n_iterations", 160))))
        initial_temp = float(params.get("initial_temp", 1200.0))
        cooling_rate = float(params.get("cooling_rate", 0.96))

        yield from run_simulated_annealing(
            depot=depot,
            deliveries=deliveries,
            vehicles_specs=vehicles_specs,
            n_iterations=n_iterations,
            initial_temp=initial_temp,
            cooling_rate=cooling_rate,
            penalty_weights=penalty_weights
        )

    # 4. NEAREST NEIGHBOR (Vizinho Mais Próximo + Evolução 2-opt)
    elif algo == "nearest_neighbor":
        nn_generations = max(10, min(500, int(params.get("nn_generations", 100))))
        nn_priority_weight = float(params.get("nn_priority_weight", 0.85))
        nn_perturbation = float(params.get("nn_perturbation", 0.35))
        apply_2opt = bool(params.get("apply_2opt", True))

        yield from run_nearest_neighbor(
            depot=depot,
            deliveries=deliveries,
            vehicles_specs=vehicles_specs,
            n_generations=nn_generations,
            priority_factor_weight=nn_priority_weight,
            perturbation_rate=nn_perturbation,
            apply_2opt=apply_2opt,
            penalty_weights=penalty_weights
        )

    # 5. CONVEX HULL INSERTION (Envoltória Convexa + Evolução Local)
    elif algo == "convex_hull":
        ch_generations = max(10, min(500, int(params.get("ch_generations", 100))))
        ch_perturbation = float(params.get("ch_perturbation", 0.35))
        apply_local = bool(params.get("apply_local_search", True))

        yield from run_convex_hull(
            depot=depot,
            deliveries=deliveries,
            vehicles_specs=vehicles_specs,
            n_generations=ch_generations,
            perturbation_rate=ch_perturbation,
            apply_local_search=apply_local,
            penalty_weights=penalty_weights
        )

    else:
        raise ValueError(f"Algoritmo desconhecido: '{algorithm_key}'")
