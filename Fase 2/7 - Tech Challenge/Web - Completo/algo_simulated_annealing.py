# -*- coding: utf-8 -*-
"""
Meta-heurística Clássica: Simulated Annealing (Têmpera Simulada)
Tech Challenge - Fase 2 (Projeto 2: Otimização de Rotas Hospitalares)

Como funciona o Simulated Annealing para o Roteamento Hospitalar (VRP):
1. Inspirado no recozimento térmico da metalurgia:
   - Começa com uma Temperatura Inicial alta (`initial_temp`), permitindo aceitar soluções
     eventualmente piores (Critério de Metropolis: `P = exp(-delta / T)`) para escapar de mínimos locais.
2. Geração de Vizinhos (Perturbação):
   - A cada passo, gera soluções vizinhas aplicando Inversão 2-opt, Swap de paradas ou
     Deslocamento de Prioridade Crítica.
3. Resfriamento Geométrico:
   - A cada iteração, a temperatura cai segundo `T = T * cooling_rate` (ex.: 0.96),
     tornando o algoritmo progressivamente mais seletivo até convergir para uma solução de alta qualidade.
"""

import math
import random
from typing import List, Dict, Any, Generator, Optional
from vrp_core import (
    DeliveryPoint,
    evaluate_solution_details,
    perturb_route
)


def run_simulated_annealing(
    depot: DeliveryPoint,
    deliveries: List[DeliveryPoint],
    vehicles_specs: List[Dict[str, Any]],
    n_iterations: int = 160,
    initial_temp: float = 1200.0,
    cooling_rate: float = 0.96,
    neighbors_per_step: int = 20,
    penalty_weights: Optional[Dict[str, float]] = None
) -> Generator[Dict[str, Any], None, None]:
    """
    Executa o algoritmo Simulated Annealing passo a passo, emitindo atualizações
    em tempo real para o navegador.
    """
    if not deliveries:
        return

    # Inicializa com uma solução construída de forma semi-aleatória ou gulosa
    current_solution = random.sample(deliveries, len(deliveries))
    current_eval = evaluate_solution_details(
        current_solution, depot=depot, vehicles_specs=vehicles_specs, penalty_weights=penalty_weights
    )
    current_fitness = current_eval["fitness"]

    best_solution = list(current_solution)
    best_eval = current_eval
    best_fitness = current_fitness

    temperature = float(initial_temp)

    for step in range(1, n_iterations + 1):
        # Em cada nível de temperatura, explora `neighbors_per_step` vizinhos
        for _ in range(max(1, neighbors_per_step)):
            candidate = perturb_route(current_solution, probability=1.0, intensity=1)
            cand_eval = evaluate_solution_details(
                candidate, depot=depot, vehicles_specs=vehicles_specs, penalty_weights=penalty_weights
            )
            cand_fitness = cand_eval["fitness"]

            delta = cand_fitness - current_fitness

            # Se o vizinho for melhor (delta < 0), aceita imediatamente;
            # Se for pior, aceita com probabilidade de Boltzmann exp(-delta / T)
            if delta < 0 or (temperature > 1e-3 and random.random() < math.exp(-delta / temperature)):
                current_solution = candidate
                current_eval = cand_eval
                current_fitness = cand_fitness

                if current_fitness < best_fitness:
                    best_fitness = current_fitness
                    best_solution = list(current_solution)
                    best_eval = current_eval

        # Resfria a temperatura
        temperature *= cooling_rate

        if step == 1 or step % 2 == 0 or step == n_iterations:
            yield {
                "algorithm_name": f"Simulated Annealing (T={temperature:.1f}°)",
                "step": step,
                "total_steps": n_iterations,
                "done": (step == n_iterations),
                "eval_details": best_eval,
                "second_best_coords": [[pt.x, pt.y] for pt in current_solution]
            }
