# -*- coding: utf-8 -*-
"""
Meta-heurística Bioinspirada: Otimização por Colônia de Formigas (Ant Colony Optimization - ACO)
Tech Challenge - Fase 2 (Projeto 2: Otimização de Rotas Hospitalares)

Como funciona o ACO para o Roteamento Hospitalar (VRP):
1. Matriz de Feromônios (tau[i][j]):
   - Representa a "memória coletiva" da colônia sobre o quão vantajoso é ir do ponto `i` para o ponto `j`.
2. Visibilidade Heurística (eta[i][j]):
   - Combina a proximidade geográfica (1 / distância) com a prioridade médica do destino (`priority ^ 0.9`),
     incentivando as formigas a priorizarem entregas Críticas (UTI/Emergência) logo no início das sub-rotas.
3. Construção Probabilística por Formiga:
   - Em cada iteração, `n_ants` formigas constroem soluções completas escolhendo o próximo ponto
     com probabilidade proporcional a: `(tau[i][j] ^ alpha) * (eta[i][j] ^ beta)`.
4. Evaporação e Reforço Elitista de Feromônios:
   - Todos os feromônios evaporam a uma taxa `evaporation_rate` (evitando estagnação em ótimos locais);
   - As melhores formigas da iteração e a melhor formiga global depositam feromônio nas arestas visitadas
     proporcionalmente à qualidade (inverso do Fitness VRP).
"""

import random
import numpy as np
from typing import List, Dict, Any, Generator, Optional
from vrp_core import (
    DeliveryPoint,
    DEFAULT_PRIORITY_PENALTY_WEIGHT,
    calculate_distance,
    evaluate_solution_details
)


def run_ant_colony(
    depot: DeliveryPoint,
    deliveries: List[DeliveryPoint],
    vehicles_specs: List[Dict[str, Any]],
    n_ants: int = 35,
    n_iterations: int = 80,
    alpha: float = 1.0,
    beta: float = 2.5,
    evaporation_rate: float = 0.15,
    q_deposit: float = 2500.0,
    penalty_weights: Optional[Dict[str, float]] = None
) -> Generator[Dict[str, Any], None, None]:
    """
    Executa o algoritmo Ant Colony Optimization (ACO) iteração por iteração,
    emitindo a melhor solução encontrada para visualização ao vivo no navegador.
    """
    n_points = len(deliveries)
    if n_points == 0:
        return

    # Lista indexada: índice 0 = Hospital Central (depot), índices 1..N = entregas
    all_nodes = [depot] + list(deliveries)
    total_nodes = len(all_nodes)

    # Inicializa a matriz de feromônios (tau) com valor uniforme positivo
    pheromone = np.ones((total_nodes, total_nodes), dtype=float) * 1.0

    # Fator de prioridade da visibilidade ajustado conforme o peso configurado na Web
    prio_penalty_w = float((penalty_weights or {}).get("priority", DEFAULT_PRIORITY_PENALTY_WEIGHT))
    prio_exponent = min(2.0, 0.85 * (prio_penalty_w / max(0.05, DEFAULT_PRIORITY_PENALTY_WEIGHT))) if prio_penalty_w > 0 else 0.0

    # Pré-calcula a matriz de visibilidade heurística (eta = prioridade / distância)
    visibility = np.zeros((total_nodes, total_nodes), dtype=float)
    for i in range(total_nodes):
        for j in range(total_nodes):
            if i != j:
                dist = max(1.0, calculate_distance(all_nodes[i], all_nodes[j]))
                prio_weight = (all_nodes[j].priority ** prio_exponent) if (all_nodes[j].priority > 0 and prio_exponent > 0) else 1.0
                visibility[i, j] = prio_weight / dist

    best_global_solution: List[DeliveryPoint] = []
    best_global_eval: Dict[str, Any] = {}
    best_global_fitness = float("inf")

    for iteration in range(1, n_iterations + 1):
        ants_solutions: List[List[DeliveryPoint]] = []
        ants_fitness: List[float] = []

        # Cada formiga constrói uma sequência de visitas para todas as entregas
        for _ in range(n_ants):
            unvisited_indices = list(range(1, total_nodes))
            current_idx = 0  # Parte do Hospital Central
            ant_indices: List[int] = []

            while unvisited_indices:
                # Calcula a atratividade (tau^alpha * eta^beta) para cada ponto ainda não visitado
                weights = []
                for cand_idx in unvisited_indices:
                    tau = pheromone[current_idx, cand_idx] ** alpha
                    eta = visibility[current_idx, cand_idx] ** beta
                    weights.append(max(1e-12, tau * eta))

                # Sorteia o próximo ponto proporcionalmente aos pesos
                chosen_idx = random.choices(unvisited_indices, weights=weights, k=1)[0]
                ant_indices.append(chosen_idx)
                unvisited_indices.remove(chosen_idx)
                current_idx = chosen_idx

            # Pequeno refinamento 2-opt rápido em 25% das formigas para acelerar descruzamento
            if len(ant_indices) >= 4 and random.random() < 0.25:
                i_cut = random.randint(0, len(ant_indices) - 2)
                j_cut = random.randint(i_cut + 1, len(ant_indices) - 1)
                candidate_indices = (
                    ant_indices[:i_cut]
                    + list(reversed(ant_indices[i_cut:j_cut + 1]))
                    + ant_indices[j_cut + 1:]
                )
                sol_orig = [all_nodes[idx] for idx in ant_indices]
                sol_cand = [all_nodes[idx] for idx in candidate_indices]
                fit_orig = evaluate_solution_details(
                    sol_orig, depot=depot, vehicles_specs=vehicles_specs, penalty_weights=penalty_weights
                )["fitness"]
                fit_cand = evaluate_solution_details(
                    sol_cand, depot=depot, vehicles_specs=vehicles_specs, penalty_weights=penalty_weights
                )["fitness"]
                if fit_cand < fit_orig:
                    ant_indices = candidate_indices

            ant_solution = [all_nodes[idx] for idx in ant_indices]
            eval_res = evaluate_solution_details(
                ant_solution, depot=depot, vehicles_specs=vehicles_specs, penalty_weights=penalty_weights
            )

            ants_solutions.append(ant_solution)
            ants_fitness.append(eval_res["fitness"])

            if eval_res["fitness"] < best_global_fitness:
                best_global_fitness = eval_res["fitness"]
                best_global_solution = list(ant_solution)
                best_global_eval = eval_res

        # Ordena as formigas da iteração atual para pegar a melhor e a 2ª melhor
        sorted_pairs = sorted(zip(ants_solutions, ants_fitness), key=lambda x: x[1])
        best_iter_solution, best_iter_fitness = sorted_pairs[0]
        second_iter_solution = sorted_pairs[1][0] if len(sorted_pairs) > 1 else best_iter_solution

        # Evaporação de feromônio em todas as arestas
        pheromone *= (1.0 - evaporation_rate)
        pheromone = np.clip(pheromone, 1e-4, 100.0)

        # Depósito de feromônio pelas 3 melhores formigas da iteração + reforço elitista da melhor global
        node_to_index = {pt: idx for idx, pt in enumerate(all_nodes)}

        def deposit_on_tour(tour: List[DeliveryPoint], fitness_val: float, multiplier: float = 1.0):
            amount = (q_deposit / max(1.0, fitness_val)) * multiplier
            prev_i = 0  # Começa no Hospital Central
            for pt in tour:
                curr_i = node_to_index[pt]
                pheromone[prev_i, curr_i] += amount
                prev_i = curr_i

        for sol, fit in sorted_pairs[:3]:
            deposit_on_tour(sol, fit, multiplier=1.0)
        if best_global_solution:
            deposit_on_tour(best_global_solution, best_global_fitness, multiplier=2.0)

        # Emite atualização para a interface Web
        yield {
            "algorithm_name": "Ant Colony Optimization (Colônia de Formigas)",
            "step": iteration,
            "total_steps": n_iterations,
            "done": (iteration == n_iterations),
            "eval_details": best_global_eval,
            "second_best_coords": [[pt.x, pt.y] for pt in second_iter_solution]
        }
