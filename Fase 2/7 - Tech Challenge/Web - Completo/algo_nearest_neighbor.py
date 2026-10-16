# -*- coding: utf-8 -*-
"""
Heurística Iterativa: Vizinho Mais Próximo (Nearest Neighbor) + Evolução Local (2-opt / Perturbação)
Tech Challenge - Fase 2 (Projeto 2: Otimização de Rotas Hospitalares)

Como funciona este método:
1. Geração Inicial (Construtiva Gulosa por Veículo e Prioridade):
   - Começando no Hospital Central (Depósito), cada veículo escolhe como próxima parada o ponto
     ainda não visitado que minimiza a razão `distância / (prioridade ^ peso_prioridade)` com um
     leve fator estocástico para explorar diferentes construções gulosas, respeitando a capacidade (kg)
     e autonomia (px) daquele veículo.
2. Evolução ao longo de `n_generations` Gerações:
   - A cada geração configurada pelo usuário, o algoritmo:
     a) Testa uma nova construção Multi-Start Nearest Neighbor com ruído controlado;
     b) Aplica operadores de busca local 2-opt (inversão de segmentos para descruzar arestas) e
        Swap de prioridades na melhor rota encontrada até o momento, evoluindo o Fitness geração a geração!
"""

import random
from typing import List, Dict, Any, Generator, Optional
from vrp_core import (
    DeliveryPoint,
    calculate_distance,
    evaluate_solution_details,
    perturb_route
)


def build_greedy_nn_route(
    depot: DeliveryPoint,
    deliveries: List[DeliveryPoint],
    vehicles_specs: List[Dict[str, Any]],
    priority_factor_weight: float = 0.85,
    noise_level: float = 0.0
) -> List[DeliveryPoint]:
    """
    Constrói uma rota completa usando a regra do Vizinho Mais Próximo (Nearest Neighbor)
    ponderada pela prioridade médica e pelos limites individuais de cada veículo.
    Se `noise_level > 0`, adiciona uma pequena variação aleatória nas distâncias (Multi-Start Greedy / GRASP)
    para permitir descobrir rotas gulosas alternativas ao longo das gerações.
    """
    unvisited = list(deliveries)
    constructed_route: List[DeliveryPoint] = []

    current_v_idx = 0
    current_load = 0.0
    current_dist = 0.0
    last_pt = depot

    while unvisited:
        v_spec = vehicles_specs[min(current_v_idx, len(vehicles_specs) - 1)]
        v_cap = float(v_spec["capacity_kg"])
        v_aut = float(v_spec["max_distance"])

        # Filtra candidatos que cabem na capacidade e autonomia do veículo atual
        feasible_candidates = []
        for cand in unvisited:
            d_to_cand = calculate_distance(last_pt, cand)
            d_back = calculate_distance(cand, depot)
            if (current_load + cand.demand_kg <= v_cap) and (current_dist + d_to_cand + d_back <= v_aut):
                feasible_candidates.append(cand)

        # Se nenhum candidato cabe no veículo atual e há próximo veículo disponível na frota, troca de veículo
        if not feasible_candidates and current_v_idx < len(vehicles_specs) - 1:
            current_v_idx += 1
            current_load = 0.0
            current_dist = 0.0
            last_pt = depot
            feasible_candidates = list(unvisited)

        pool = feasible_candidates if feasible_candidates else unvisited

        def candidate_cost(pt: DeliveryPoint) -> float:
            dist = calculate_distance(last_pt, pt)
            prio_bonus = (pt.priority ** priority_factor_weight) if pt.priority > 0 else 1.0
            noise = random.uniform(1.0 - noise_level, 1.0 + noise_level) if noise_level > 0 else 1.0
            return (dist / prio_bonus) * noise

        chosen = min(pool, key=candidate_cost)
        constructed_route.append(chosen)
        unvisited.remove(chosen)

        current_load += chosen.demand_kg
        current_dist += calculate_distance(last_pt, chosen)
        last_pt = chosen

    return constructed_route


def run_nearest_neighbor(
    depot: DeliveryPoint,
    deliveries: List[DeliveryPoint],
    vehicles_specs: List[Dict[str, Any]],
    n_generations: int = 100,
    priority_factor_weight: float = 0.85,
    perturbation_rate: float = 0.35,
    apply_2opt: bool = True,
    penalty_weights: Optional[Dict[str, float]] = None
) -> Generator[Dict[str, Any], None, None]:
    """
    Executa o algoritmo Nearest Neighbor de forma iterativa ao longo de `n_generations` gerações,
    permitindo configurar número de gerações, peso de prioridade, taxa de perturbação e 2-opt.
    """
    if not deliveries:
        return

    # Geração 1: Construção Nearest Neighbor determinística (sem ruído)
    best_route = build_greedy_nn_route(
        depot=depot,
        deliveries=deliveries,
        vehicles_specs=vehicles_specs,
        priority_factor_weight=priority_factor_weight,
        noise_level=0.0
    )
    best_eval = evaluate_solution_details(
        best_route, depot=depot, vehicles_specs=vehicles_specs, penalty_weights=penalty_weights
    )
    best_fitness = best_eval["fitness"]

    n = len(best_route)

    for gen in range(1, n_generations + 1):
        candidate_coords = [[pt.x, pt.y] for pt in best_route]

        if gen > 1:
            # 1) Testa uma nova construção gulosa com ruído (GRASP / Multi-Start Nearest Neighbor)
            greedy_cand = build_greedy_nn_route(
                depot=depot,
                deliveries=deliveries,
                vehicles_specs=vehicles_specs,
                priority_factor_weight=priority_factor_weight,
                noise_level=perturbation_rate
            )
            greedy_eval = evaluate_solution_details(
                greedy_cand, depot=depot, vehicles_specs=vehicles_specs, penalty_weights=penalty_weights
            )
            candidate_coords = [[pt.x, pt.y] for pt in greedy_cand]

            if greedy_eval["fitness"] < best_fitness:
                best_fitness = greedy_eval["fitness"]
                best_route = greedy_cand
                best_eval = greedy_eval

            # 2) Se o refinamento 2-opt estiver ativo, explora inversões de segmentos e trocas locais
            if apply_2opt and n >= 3:
                for _ in range(12):
                    # Perturba/inverte um trecho da melhor rota atual
                    local_cand = perturb_route(best_route, probability=1.0, intensity=1)
                    local_eval = evaluate_solution_details(
                        local_cand, depot=depot, vehicles_specs=vehicles_specs, penalty_weights=penalty_weights
                    )
                    if local_eval["fitness"] < best_fitness:
                        best_fitness = local_eval["fitness"]
                        best_route = local_cand
                        best_eval = local_eval

        if gen == 1 or gen % 2 == 0 or gen == n_generations:
            yield {
                "algorithm_name": "Nearest Neighbor (Multi-Start + 2-opt)",
                "step": gen,
                "total_steps": n_generations,
                "done": (gen == n_generations),
                "eval_details": best_eval,
                "second_best_coords": candidate_coords
            }
