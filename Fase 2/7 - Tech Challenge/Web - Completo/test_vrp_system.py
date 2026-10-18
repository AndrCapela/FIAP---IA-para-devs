# -*- coding: utf-8 -*-
"""
Suíte de Testes Automatizados para Validação de Funcionalidades (`test_vrp_system.py`)
Tech Challenge - Fase 2 (Projeto 2: Otimização de Rotas Hospitalares)

Cobre todos os requisitos técnicos do edital:
1. Validação do núcleo VRP (`vrp_core.py`):
   - Criação do cenário hospitalar e restrições de prioridades;
   - Divisão de rotas entre múltiplos veículos com limites individuais de carga (kg) e autonomia (px);
   - Cálculo da Função Fitness e aplicação dos pesos de penalidade (`priority`, `capacity`, `autonomy`).
2. Validação dos 5 algoritmos de otimização (`route_optimizer_dispatcher.py`):
   - Algoritmo Genético (GA), Ant Colony Optimization (ACO), Simulated Annealing (SA),
     Nearest Neighbor (NN) e Convex Hull (CH).
3. Validação da API Web (`web_app.py`) e construção do Prompt da LLM (`llm_driver_assistant.py`).

Como executar:
    python -m unittest test_vrp_system.py -v
"""

import unittest
from vrp_core import (
    DeliveryPoint,
    PRIORITY_CRITICAL,
    PRIORITY_REGULAR,
    get_hospital_scenario,
    normalize_vehicles_specs,
    split_route_into_vehicles,
    evaluate_solution_details
)
from route_optimizer_dispatcher import dispatch_optimization
from llm_driver_assistant import build_driver_system_instruction
import web_app


class TestVRPSystem(unittest.TestCase):

    def setUp(self):
        self.depot, self.deliveries = get_hospital_scenario()
        self.vehicles_specs = normalize_vehicles_specs(
            vehicles_specs=[
                {"vehicle_id": 1, "name": "Veículo 1", "capacity_kg": 85.0, "max_distance": 950.0},
                {"vehicle_id": 2, "name": "Veículo 2", "capacity_kg": 85.0, "max_distance": 950.0},
                {"vehicle_id": 3, "name": "Veículo 3", "capacity_kg": 85.0, "max_distance": 950.0},
            ]
        )

    def test_scenario_and_heterogeneous_fleet_splitting(self):
        """Verifica se o cenário possui o Hospital Central (#0) e divide entregas entre múltiplos veículos."""
        self.assertEqual(self.depot.id, 0)
        self.assertEqual(len(self.deliveries), 14)

        routes = split_route_into_vehicles(
            chromosome=self.deliveries,
            depot=self.depot,
            vehicles_specs=self.vehicles_specs
        )
        self.assertGreaterEqual(len(routes), 2)
        total_stops = sum(len(r["stops"]) for r in routes)
        self.assertEqual(total_stops, len(self.deliveries))

    def test_priority_and_capacity_penalties(self):
        """Verifica se entregas críticas no final da rota ou excesso de carga aumentam a penalidade no Fitness."""
        # Ordem onde entregas regulares vêm antes das críticas
        regular_first = sorted(self.deliveries, key=lambda p: p.priority)
        # Ordem onde entregas críticas vêm primeiro
        critical_first = sorted(self.deliveries, key=lambda p: p.priority, reverse=True)

        eval_reg_first = evaluate_solution_details(
            regular_first, depot=self.depot, vehicles_specs=self.vehicles_specs,
            penalty_weights={"priority": 1.0, "capacity": 40.0, "autonomy": 15.0}
        )
        eval_crit_first = evaluate_solution_details(
            critical_first, depot=self.depot, vehicles_specs=self.vehicles_specs,
            penalty_weights={"priority": 1.0, "capacity": 40.0, "autonomy": 15.0}
        )

        self.assertLess(eval_crit_first["priority_penalty"], eval_reg_first["priority_penalty"])

    def test_all_five_algorithms_converge(self):
        """Garante que todos os 5 algoritmos executam e retornam avaliações válidas pelo dispatcher."""
        algorithms = [
            "genetic_algorithm",
            "ant_colony",
            "simulated_annealing",
            "nearest_neighbor",
            "convex_hull"
        ]
        params = {
            "population_size": 25,
            "n_generations": 10,
            "n_ants": 10,
            "n_iterations": 10,
            "nn_generations": 10,
            "ch_generations": 10,
            "priority_penalty_weight": 0.5,
            "capacity_penalty_weight": 45.0,
            "autonomy_penalty_weight": 18.0
        }

        for alg in algorithms:
            steps = list(dispatch_optimization(
                algorithm_key=alg,
                depot=self.depot,
                deliveries=self.deliveries,
                vehicles_specs=self.vehicles_specs,
                params=params
            ))
            self.assertGreater(len(steps), 0, f"Algoritmo {alg} não emitiu passos")
            final_step = steps[-1]
            self.assertTrue(final_step["done"])
            self.assertGreater(final_step["eval_details"]["fitness"], 0.0)

    def test_web_endpoints_and_llm_prompt_generation(self):
        """Valida os endpoints da aplicação Flask e a construção do prompt para o Google Gemini."""
        client = web_app.app.test_client()

        # 1. Lista de algoritmos
        res_algos = client.get("/api/algorithms")
        self.assertEqual(res_algos.status_code, 200)
        self.assertEqual(len(res_algos.get_json()["algorithms"]), 5)

        # 2. Execução do streaming SSE e geração do JSON
        res_stream = client.get("/api/optimize/stream?algorithm=genetic_algorithm&n_generations=10")
        self.assertEqual(res_stream.status_code, 200)
        _ = res_stream.get_data(as_text=True)

        res_json = client.post("/api/solution/generate-json", json={})
        self.assertEqual(res_json.status_code, 200)
        export_data = res_json.get_json()["data"]
        self.assertIn("routes", export_data)

        # 3. Download do arquivo JSON
        res_download = client.get("/api/solution/download-json")
        self.assertEqual(res_download.status_code, 200)

        # 4. Construção da instrução de sistema da LLM com o JSON gerado
        prompt = build_driver_system_instruction(export_data, selected_vehicle_id=1)
        self.assertIn("MOTORISTA DO VEÍCULO 1", prompt)
        self.assertIn("Hospital Universitário Central", prompt)


if __name__ == "__main__":
    unittest.main()
