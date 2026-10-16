# -*- coding: utf-8 -*-
"""
Heurística Geométrica Iterativa: Envoltória Convexa (Convex Hull Insertion) + Evolução Local
Tech Challenge - Fase 2 (Projeto 2: Otimização de Rotas Hospitalares)

Como funciona este método:
1. Fecho Convexo Inicial (Algoritmo Monotone Chain):
   - Identifica os pontos mais externos que formam o polígono convexo ao redor de todas as unidades.
2. Inserção Mais Barata Iterativa (Cheapest Insertion):
   - Insere os pontos internos restantes na posição da rota que gera o menor aumento no Fitness VRP
     (considerando distância, prioridades médicas e os limites individuais de carga e autonomia dos veículos).
3. Evolução ao longo de `n_generations` Gerações:
   - A cada geração configurada pelo usuário, o algoritmo:
     a) Testa novas ordens de inserção dos pontos internos sobre o fecho convexo (com taxa de perturbação
        configurável `perturbation_rate`), pois a ordem em que os nós internos entram no polígono altera
        a divisão entre veículos;
     b) Aplica operadores de re-inserção e refinamento local (2-opt + ajuste de prioridades críticas)
        se `apply_local_search=True`.
"""

import random
from typing import List, Dict, Any, Generator, Optional
from vrp_core import (
    DeliveryPoint,
    evaluate_solution_details,
    perturb_route
)


def compute_convex_hull(points: List[DeliveryPoint]) -> List[DeliveryPoint]:
    """
    Calcula o fecho convexo (Convex Hull) de uma lista de `DeliveryPoint`
    usando o algoritmo Monotone Chain de Andrew — complexidade O(N log N).
    """
    sorted_pts = sorted(points, key=lambda p: (p.x, p.y))
    if len(sorted_pts) <= 2:
        return list(sorted_pts)

    def cross_product(o: DeliveryPoint, a: DeliveryPoint, b: DeliveryPoint) -> float:
        return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)

    lower: List[DeliveryPoint] = []
    for p in sorted_pts:
        while len(lower) >= 2 and cross_product(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper: List[DeliveryPoint] = []
    for p in reversed(sorted_pts):
        while len(upper) >= 2 and cross_product(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    return lower[:-1] + upper[:-1]


def build_hull_insertion_route(
    hull_base: List[DeliveryPoint],
    internal_points: List[DeliveryPoint],
    depot: DeliveryPoint,
    vehicles_specs: List[Dict[str, Any]],
    perturbation_rate: float = 0.0,
    penalty_weights: Optional[Dict[str, float]] = None
) -> List[DeliveryPoint]:
    """
    Parte do polígono convexo (`hull_base`) e insere cada ponto de `internal_points`
    na posição que minimiza o Fitness VRP.
    Se `perturbation_rate > 0`, embaralha parcialmente a ordem de inserção dos pontos internos
    e permite escolher posições quase-ótimas para explorar diferentes divisões de veículos.
    """
    route = list(hull_base)
    if perturbation_rate > 0 and random.random() < 0.35:
        route.reverse()  # Testa também percorrer o polígono convexo no sentido horário/anti-horário

    ordered_internals = list(internal_points)
    if perturbation_rate > 0:
        # Ordena por prioridade mas adiciona variação aleatória proporcional à taxa de perturbação
        ordered_internals.sort(
            key=lambda pt: pt.priority + random.uniform(-perturbation_rate * 2.5, perturbation_rate * 2.5),
            reverse=True
        )
    else:
        ordered_internals.sort(key=lambda pt: pt.priority, reverse=True)

    for pt in ordered_internals:
        best_pos_route = None
        best_pos_fitness = float("inf")

        for insert_pos in range(len(route) + 1):
            candidate = route[:insert_pos] + [pt] + route[insert_pos:]
            cand_eval = evaluate_solution_details(
                candidate, depot=depot, vehicles_specs=vehicles_specs, penalty_weights=penalty_weights
            )
            fit = cand_eval["fitness"]
            if perturbation_rate > 0:
                fit *= random.uniform(1.0 - perturbation_rate * 0.15, 1.0 + perturbation_rate * 0.15)

            if fit < best_pos_fitness:
                best_pos_fitness = fit
                best_pos_route = candidate

        route = best_pos_route

    return route


def run_convex_hull(
    depot: DeliveryPoint,
    deliveries: List[DeliveryPoint],
    vehicles_specs: List[Dict[str, Any]],
    n_generations: int = 100,
    perturbation_rate: float = 0.35,
    apply_local_search: bool = True,
    penalty_weights: Optional[Dict[str, float]] = None
) -> Generator[Dict[str, Any], None, None]:
    """
    Executa a heurística Convex Hull Insertion de forma iterativa ao longo de `n_generations` gerações,
    permitindo configurar número de gerações, taxa de perturbação e busca local.
    """
    if len(deliveries) <= 2:
        eval_res = evaluate_solution_details(
            deliveries, depot=depot, vehicles_specs=vehicles_specs, penalty_weights=penalty_weights
        )
        yield {
            "algorithm_name": "Convex Hull (Envoltória Convexa)",
            "step": 1,
            "total_steps": 1,
            "done": True,
            "eval_details": eval_res,
            "second_best_coords": []
        }
        return

    # 1. Calcula o fecho convexo externo e separa os pontos internos
    hull_route = compute_convex_hull(deliveries)
    remaining = [pt for pt in deliveries if pt not in hull_route]

    # Geração 1: Inserção gulosa determinística sobre o fecho convexo
    best_route = build_hull_insertion_route(
        hull_base=hull_route,
        internal_points=remaining,
        depot=depot,
        vehicles_specs=vehicles_specs,
        perturbation_rate=0.0,
        penalty_weights=penalty_weights
    )
    best_eval = evaluate_solution_details(
        best_route, depot=depot, vehicles_specs=vehicles_specs, penalty_weights=penalty_weights
    )
    best_fitness = best_eval["fitness"]

    for gen in range(1, n_generations + 1):
        candidate_coords = [[pt.x, pt.y] for pt in best_route]

        if gen > 1:
            # 1) Testa uma nova construção de inserção sobre o fecho convexo com perturbação
            hull_cand = build_hull_insertion_route(
                hull_base=hull_route,
                internal_points=remaining,
                depot=depot,
                vehicles_specs=vehicles_specs,
                perturbation_rate=perturbation_rate,
                penalty_weights=penalty_weights
            )
            hull_eval = evaluate_solution_details(
                hull_cand, depot=depot, vehicles_specs=vehicles_specs, penalty_weights=penalty_weights
            )
            candidate_coords = [[pt.x, pt.y] for pt in hull_cand]

            if hull_eval["fitness"] < best_fitness:
                best_fitness = hull_eval["fitness"]
                best_route = hull_cand
                best_eval = hull_eval

            # 2) Se o refinamento local estiver ativado, aplica re-inserção e 2-opt/Swap na melhor rota
            if apply_local_search:
                for _ in range(12):
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
                "algorithm_name": "Convex Hull (Inserção + Busca Local)",
                "step": gen,
                "total_steps": n_generations,
                "done": (gen == n_generations),
                "eval_details": best_eval,
                "second_best_coords": candidate_coords
            }
