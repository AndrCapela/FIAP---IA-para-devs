# -*- coding: utf-8 -*-
"""
Sistema de Otimização de Rotas para Distribuição de Medicamentos e Insumos (TSP / VRP Hospitalar)
Tech Challenge - Fase 2 (Projeto 2 - Item 1: Otimização de Rotas via Algoritmos Genéticos)

Este arquivo foi criado a partir de uma cópia do arquivo `tsp.py` original da disciplina e
modificado com diversos comentários explicativos para resolver o problema do "Caixeiro Viajante Médico"
ampliado para Múltiplos Veículos (VRP) com restrições realistas:
- Prioridades de entrega (Crítico/UTI, Urgente, Regular);
- Capacidade máxima de carga dos veículos (em kg);
- Autonomia máxima de distância por veículo (em pixels/km equivalentes);
- Múltiplos veículos partindo e retornando ao Hospital Universitário Central (Depósito);
- Visualização em tempo real no Pygame + exportação de mapa estático (.png), mapa interativo (.html)
  e arquivo estruturado da melhor solução (.json).
"""

import os
import sys
import json
import random
import itertools
import numpy as np
import pygame
from pygame.locals import *

# Importa as funções e estruturas do nosso módulo de Algoritmo Genético Hospitalar
from genetic_algorithm import (
    DeliveryPoint,
    PRIORITY_LABELS,
    get_hospital_scenario,
    generate_random_hospital_scenario,
    generate_random_population,
    calculate_fitness,
    evaluate_solution_details,
    order_crossover,
    mutate,
    sort_population,
    tournament_selection,
    default_problems
)

# Importa as funções de desenho em tempo real e exportação de mapas
from draw_functions import (
    draw_paths,
    draw_plot,
    draw_cities,
    draw_vehicle_routes,
    draw_status_panel,
    save_final_static_map,
    save_interactive_html_map
)
from benchmark_att48 import *


# ==============================================================================
# 1. DEFINIÇÃO DE CONSTANTES E HIPERPARÂMETROS DO PROBLEMA
# ==============================================================================

# Configurações da Janela do Pygame
WIDTH, HEIGHT = 1100, 600   # Ampliado de 800x400 para acomodar o painel da frota + mapa detalhado
NODE_RADIUS = 9             # Raio dos círculos que representam cada unidade hospitalar
FPS = 30                    # Taxa de atualização de quadros por segundo
PLOT_X_OFFSET = 450         # Deslocamento horizontal onde começa a área do mapa à direita

# Hiperparâmetros do Algoritmo Genético (GA)
USE_PREDEFINED_SCENARIO = True  # True = usa o cenário hospitalar pré-definido; False = gera pontos aleatórios
N_CITIES = 14                   # Número de pontos de entrega (além do Hospital Central) se for aleatório
POPULATION_SIZE = 120           # Tamanho da população em cada geração
N_GENERATIONS = 200             # Limite de gerações (coloque None para rodar infinitamente até apertar 'Q')
MUTATION_PROBABILITY = 0.45     # Probabilidade de um novo indivíduo sofrer mutação (45%)
MUTATION_INTENSITY = 1          # Quantidade de operações de mutação (2-opt / swap) por indivíduo mutado
ELITISM_COUNT = 2               # Quantidade dos melhores indivíduos preservados intactos a cada geração

# Restrições Realistas da Frota Hospitalar (VRP)
MAX_VEHICLES = 3                # Quantidade de veículos disponíveis na frota do hospital
VEHICLE_CAPACITY_KG = 85.0      # Capacidade máxima de carga por veículo (em kg)
VEHICLE_MAX_DISTANCE = 950.0    # Autonomia máxima de cada veículo por viagem (em pixels equivalentes)

# Definição de cores básicas (RGB)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 38, 38)
BLUE = (37, 99, 235)
GRAY = (190, 198, 210)


# ==============================================================================
# 2. INICIALIZAÇÃO DO CENÁRIO HOSPITALAR
# ==============================================================================

if USE_PREDEFINED_SCENARIO:
    # Cenário hospitalar realista pré-definido (1 Hospital Central + 14 Unidades/Pacientes)
    depot_location, cities_locations = get_hospital_scenario()
else:
    # Alternativa: Geração aleatória de unidades/pacientes com demandas e prioridades sorteadas
    depot_location, cities_locations = generate_random_hospital_scenario(
        n_deliveries=N_CITIES,
        min_x=PLOT_X_OFFSET + 30,
        max_x=WIDTH - 35,
        min_y=40,
        max_y=HEIGHT - 40
    )


# ==============================================================================
# 3. FUNÇÃO AUXILIAR PARA SALVAR A MELHOR ROTA E GERAR OS MAPAS FINAIS
# ==============================================================================

def save_best_solution_and_maps(
    depot: DeliveryPoint,
    best_solution: list,
    best_fitness_values: list,
    base_dir: str
) -> None:
    """
    Salva a melhor solução encontrada em arquivo JSON (caso seja melhor que a anterior salva),
    além de exportar o gráfico/mapa estático (.png) e o mapa interativo (.html).
    Atende ao requisito `# TODO: save the best individual in a file if it is better than the one saved`
    do código `tsp.py` original.
    """
    if not best_solution:
        return

    details = evaluate_solution_details(
        path=best_solution,
        depot=depot,
        max_vehicles=MAX_VEHICLES,
        vehicle_capacity_kg=VEHICLE_CAPACITY_KG,
        vehicle_max_distance=VEHICLE_MAX_DISTANCE
    )

    json_path = os.path.join(base_dir, "melhor_rota_hospitalar.json")
    png_path = os.path.join(base_dir, "mapa_rotas_otimizadas.png")
    html_path = os.path.join(base_dir, "mapa_interativo_rotas.html")

    # Verifica se já existe uma solução salva anteriormente e compara o Fitness
    should_save_json = True
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                previous_data = json.load(f)
            prev_fitness = previous_data.get("fitness_total", float("inf"))
            if details["fitness"] >= prev_fitness:
                should_save_json = False
                print(
                    f"\n[INFO] Solução atual (Fitness {details['fitness']:.2f}) não superou "
                    f"o recorde salvo anteriormente ({prev_fitness:.2f}). Mantendo recorde no JSON."
                )
        except Exception:
            should_save_json = True

    if should_save_json:
        export_payload = {
            "cenario": "Distribuição Hospitalar de Medicamentos e Insumos (Projeto 2)",
            "geracoes_executadas": len(best_fitness_values),
            "fitness_total": round(details["fitness"], 2),
            "distancia_total_px": round(details["total_distance"], 2),
            "penalidade_prioridade": round(details["priority_penalty"], 2),
            "solucao_viavel": details["is_feasible"],
            "restricoes_frota": {
                "max_veiculos": MAX_VEHICLES,
                "capacidade_veiculo_kg": VEHICLE_CAPACITY_KG,
                "autonomia_maxima_px": VEHICLE_MAX_DISTANCE
            },
            "deposito_central": {
                "id": depot.id,
                "nome": depot.name,
                "coordenadas_tela": [depot.x, depot.y],
                "coordenadas_geo": [depot.lat, depot.lon]
            },
            "rotas_veiculos": [
                {
                    "veiculo_id": r["vehicle_id"],
                    "carga_total_kg": r["load_kg"],
                    "distancia_percorrida_px": round(r["distance"], 2),
                    "paradas": [
                        {
                            "ordem_parada": idx + 1,
                            "id": pt.id,
                            "nome": pt.name,
                            "prioridade": PRIORITY_LABELS[pt.priority],
                            "peso_kg": pt.demand_kg,
                            "insumo": pt.item_description,
                            "coordenadas_tela": [pt.x, pt.y],
                            "coordenadas_geo": [pt.lat, pt.lon]
                        }
                        for idx, pt in enumerate(r["stops"])
                    ]
                }
                for r in details["routes"]
            ]
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(export_payload, f, indent=4, ensure_ascii=False)
        print(f"\n[SUCESSO] Novo recorde salvo em: {json_path}")

    # Sempre atualiza as visualizações estática (PNG) e interativa (HTML) da execução
    save_final_static_map(depot, details, best_fitness_values, png_path)
    save_interactive_html_map(depot, details, html_path)
    print(f"[SUCESSO] Mapa estático salvo em: {png_path}")
    print(f"[SUCESSO] Mapa interativo salvo em: {html_path}")


# ==============================================================================
# 4. EXECUÇÃO PRINCIPAL DO ALGORITMO GENÉTICO COM PYGAME
# ==============================================================================

def main():
    # Inicializa o Pygame e configura a janela de visualização
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Tech Challenge Fase 2 - Otimização de Rotas Hospitalares (AG + VRP)")
    clock = pygame.time.Clock()
    generation_counter = itertools.count(start=1)  # Contador de gerações iniciando em 1

    # Cria a população inicial combinando indivíduos aleatórios e heurística Nearest Neighbor + Prioridade
    population = generate_random_population(
        cities_location=cities_locations,
        population_size=POPULATION_SIZE,
        depot=depot_location,
        use_heuristic_seed=True
    )

    best_fitness_values = []
    best_solutions = []
    best_overall_solution = None
    best_overall_fitness = float("inf")

    # Loop principal de evolução e visualização
    running = True
    while running:
        # Captura eventos do teclado e fechamento da janela
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    running = False

        generation = next(generation_counter)

        # Limpa a tela com fundo branco
        screen.fill(WHITE)

        # 1. AVALIAÇÃO (FITNESS): Calcula o custo de cada indivíduo considerando:
        #    Distância + Prioridade Médica + Capacidade de Carga + Autonomia + Múltiplos Veículos
        population_fitness = [
            calculate_fitness(
                individual,
                depot=depot_location,
                max_vehicles=MAX_VEHICLES,
                vehicle_capacity_kg=VEHICLE_CAPACITY_KG,
                vehicle_max_distance=VEHICLE_MAX_DISTANCE
            )
            for individual in population
        ]

        # 2. ORDENAÇÃO: Ordena a população do menor custo (melhor rota) para o maior
        population, population_fitness = sort_population(population, population_fitness)

        # Obtém os detalhes completos da melhor solução da geração atual
        best_fitness = population_fitness[0]
        best_solution = population[0]
        eval_details = evaluate_solution_details(
            path=best_solution,
            depot=depot_location,
            max_vehicles=MAX_VEHICLES,
            vehicle_capacity_kg=VEHICLE_CAPACITY_KG,
            vehicle_max_distance=VEHICLE_MAX_DISTANCE
        )

        # Registra no histórico para o gráfico de convergência
        best_fitness_values.append(best_fitness)
        best_solutions.append(best_solution)

        if best_fitness < best_overall_fitness:
            best_overall_fitness = best_fitness
            best_overall_solution = list(best_solution)

        # 3. DESENHO NA TELA (PYGAME):
        # 3.1 Desenha o gráfico de evolução do Fitness por geração
        draw_plot(
            screen,
            list(range(1, len(best_fitness_values) + 1)),
            best_fitness_values,
            y_label="Fitness (Dist. + Penalidades)"
        )

        # 3.2 Desenha o painel informativo de status da frota e legenda de prioridades
        draw_status_panel(
            screen=screen,
            generation=generation,
            eval_details=eval_details,
            max_vehicles=MAX_VEHICLES,
            vehicle_capacity_kg=VEHICLE_CAPACITY_KG,
            vehicle_max_distance=VEHICLE_MAX_DISTANCE
        )

        # 3.3 Desenha o mapa de fundo e a 2ª melhor solução em cinza claro (como no `tsp.py` original)
        draw_cities(screen, cities_locations, RED, NODE_RADIUS, depot=depot_location)
        if len(population) > 1:
            draw_paths(screen, population[1], rgb_color=GRAY, width=1)

        # 3.4 Desenha as rotas otimizadas de cada veículo com cores distintas
        draw_vehicle_routes(screen, eval_details["routes"], width=3)

        # 3.5 Redesenha os nós por cima das linhas para que os círculos e textos fiquem sempre legíveis
        draw_cities(screen, cities_locations, RED, NODE_RADIUS, depot=depot_location)

        # Exibe log resumido no terminal a cada 10 gerações (ou na 1ª geração)
        if generation == 1 or generation % 10 == 0:
            print(
                f"Geração {generation:03d}: Melhor Fitness = {best_fitness:.2f} | "
                f"Distância = {eval_details['total_distance']:.1f}px | "
                f"Penalidade Prioridade = {eval_details['priority_penalty']:.1f} | "
                f"Veículos = {len(eval_details['routes'])}/{MAX_VEHICLES}"
            )

        # Verifica se atingiu o número máximo configurado de gerações
        if N_GENERATIONS is not None and generation >= N_GENERATIONS:
            print(f"\n[CONCLUÍDO] Limite de {N_GENERATIONS} gerações atingido!")
            pygame.display.flip()
            break

        # 4. CRIAÇÃO DA NOVA GERAÇÃO (ELITISMO + SELEÇÃO + CROSSOVER + MUTAÇÃO)
        # Mantém os melhores indivíduos intactos (Elitismo)
        new_population = [population[i] for i in range(min(ELITISM_COUNT, len(population)))]

        # Calcula probabilidades inversamente proporcionais ao Fitness (para Seleção por Roleta)
        probability = 1.0 / (np.array(population_fitness) + 1e-6)

        while len(new_population) < POPULATION_SIZE:
            # Hibridiza Seleção por Torneio (70% das vezes) e Seleção por Roleta (30% das vezes)
            if random.random() < 0.7:
                parent1 = tournament_selection(population, population_fitness, tournament_size=4)
                parent2 = tournament_selection(population, population_fitness, tournament_size=4)
            else:
                parent1, parent2 = random.choices(population, weights=probability, k=2)

            # Cruzamento Order Crossover (OX) preservando a validade das paradas
            child1 = order_crossover(parent1, parent2)

            # Mutação (2-opt Inversão de Segmento + Swap + Avanço de Prioridade Crítica)
            child1 = mutate(child1, MUTATION_PROBABILITY, mutation_intensity=MUTATION_INTENSITY)

            new_population.append(child1)

        population = new_population

        # Atualiza a tela do Pygame e controla a taxa de FPS
        pygame.display.flip()
        clock.tick(FPS)

    # Ao sair do loop, salva a melhor solução em JSON e exporta os mapas estático (.png) e interativo (.html)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    save_best_solution_and_maps(
        depot=depot_location,
        best_solution=best_overall_solution,
        best_fitness_values=best_fitness_values,
        base_dir=base_dir
    )

    pygame.quit()


if __name__ == "__main__":
    main()
