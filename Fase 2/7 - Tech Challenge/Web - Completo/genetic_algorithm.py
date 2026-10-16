# -*- coding: utf-8 -*-
"""
Algoritmo 1: Algoritmo Genético (GA - Evolucionário)
Tech Challenge - Fase 2 (Projeto 2: Otimização de Rotas para Distribuição de Medicamentos e Insumos)

Este módulo contém EXCLUSIVAMENTE os operadores evolucionários do Algoritmo Genético:
1. Geração da população inicial (`generate_random_population`);
2. Seleção de pais (`tournament_selection` e Roleta);
3. Cruzamento de permutações (`order_crossover` - OX);
4. Mutação híbrida (`mutate`);
5. Loop evolucionário passo a passo (`run_genetic_algorithm`).

Toda a modelagem VRP, divisão de frota e cálculo de penalidades (Fitness) estão
centralizados no módulo compartilhado `vrp_core.py`.
"""

import random
import copy
import numpy as np
from typing import List, Tuple, Dict, Any, Optional, Generator

from vrp_core import (
    DeliveryPoint,
    calculate_fitness,
    evaluate_solution_details,
    create_nearest_neighbor_seed,
    perturb_route
)


def generate_random_population(
    cities_location: List[Any],
    population_size: int,
    depot: DeliveryPoint = None,
    use_heuristic_seed: bool = True
) -> List[List[Any]]:
    """
    Gera a população inicial de rotas (100% aleatória ou híbrida com semente Nearest Neighbor).
    """
    population = []

    if use_heuristic_seed and len(cities_location) >= 2 and isinstance(cities_location[0], DeliveryPoint):
        population.append(create_nearest_neighbor_seed(cities_location, depot, prioritize_critical=True))
        if population_size > 2:
            population.append(create_nearest_neighbor_seed(cities_location, depot, prioritize_critical=False))

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
    """Aplica o operador de mutação híbrido (2-opt + Swap + Avanço de Prioridade Crítica)."""
    return perturb_route(
        solution=solution,
        probability=mutation_probability,
        intensity=mutation_intensity
    )


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
    use_heuristic_seed: bool = True,
    penalty_weights: Optional[Dict[str, float]] = None
) -> Generator[Dict[str, Any], None, None]:
    """
    Executa o Algoritmo Genético como um gerador (yield), avaliando cada indivíduo
    com `calculate_fitness` / `evaluate_solution_details` de `vrp_core.py` (incluindo `penalty_weights`).
    """
    population = generate_random_population(
        cities_location=deliveries,
        population_size=population_size,
        depot=depot,
        use_heuristic_seed=use_heuristic_seed
    )

    for gen in range(1, n_generations + 1):
        pop_fitness = [
            calculate_fitness(
                ind,
                depot=depot,
                vehicles_specs=vehicles_specs,
                penalty_weights=penalty_weights
            )
            for ind in population
        ]
        population, pop_fitness = sort_population(population, pop_fitness)

        best_solution = population[0]
        second_best = population[1] if len(population) > 1 else population[0]

        if gen == 1 or gen % 2 == 0 or gen == n_generations:
            eval_details = evaluate_solution_details(
                path=best_solution,
                depot=depot,
                vehicles_specs=vehicles_specs,
                penalty_weights=penalty_weights
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
