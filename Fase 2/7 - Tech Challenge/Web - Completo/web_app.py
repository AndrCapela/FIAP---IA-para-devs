# -*- coding: utf-8 -*-
"""
Aplicação Web Interativa (Etapas 1, 2 e 3) - Sistema de Otimização de Rotas Hospitalares
Tech Challenge - Fase 2 (Projeto 2: Otimização de Rotas para Distribuição de Medicamentos e Insumos)

Funcionalidades implementadas:
- Etapa 1: Interface Web em tempo real com Streaming (Server-Sent Events), Canvas 2D (estilo Pygame),
  Gráfico de Convergência ao vivo e Mapa Geográfico Interativo (Leaflet / OpenStreetMap);
- Etapa 2: Configuração individual de cada veículo da frota (capacidade em kg e autonomia máxima em px
  para cada veículo separadamente) + edição/adição de pontos de entrega;
- Etapa 3: Seleção do algoritmo/heurística de otimização (Algoritmo Genético, Ant Colony Optimization,
  Simulated Annealing, Nearest Neighbor, Convex Hull) através do orquestrador `route_optimizer_dispatcher.py`,
  com painel dinâmico de parâmetros específicos para cada método.
"""

import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, send_file

from vrp_core import (
    DeliveryPoint,
    PRIORITY_LABELS,
    DEFAULT_PRIORITY_PENALTY_WEIGHT,
    DEFAULT_CAPACITY_PENALTY_WEIGHT,
    DEFAULT_AUTONOMY_PENALTY_WEIGHT,
    get_hospital_scenario,
    generate_random_hospital_scenario,
    normalize_vehicles_specs
)
from route_optimizer_dispatcher import (
    get_available_algorithms,
    dispatch_optimization
)
from llm_driver_assistant import ask_driver_assistant

app = Flask(__name__)

# Caminho onde o arquivo JSON da solução gerada será salvo
SOLUTION_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "melhor_rota_hospitalar.json")

# Estado atual do cenário e da última solução em memória
CURRENT_SCENARIO = {
    "depot": None,
    "deliveries": [],
    "last_solution": None
}


def serialize_point(pt: DeliveryPoint) -> dict:
    """Converte um `DeliveryPoint` em dicionário JSON para envio ao frontend."""
    return {
        "id": pt.id,
        "name": pt.name,
        "x": pt.x,
        "y": pt.y,
        "demand_kg": pt.demand_kg,
        "priority": pt.priority,
        "priority_label": PRIORITY_LABELS.get(pt.priority, "Regular"),
        "item_description": pt.item_description,
        "lat": pt.lat,
        "lon": pt.lon
    }


def serialize_evaluation(eval_details: dict, depot: DeliveryPoint, penalty_weights: dict = None) -> dict:
    """Formata os detalhes de avaliação da rota (incluindo limites individuais por veículo e pesos de penalidade)."""
    routes_serialized = []
    for r in eval_details["routes"]:
        routes_serialized.append({
            "vehicle_id": r["vehicle_id"],
            "vehicle_name": r.get("vehicle_name", f"Veículo {r['vehicle_id']}"),
            "capacity_limit_kg": round(r.get("capacity_limit_kg", 85.0), 1),
            "autonomy_limit_px": round(r.get("autonomy_limit_px", 950.0), 1),
            "load_kg": round(r["load_kg"], 1),
            "distance": round(r["distance"], 1),
            "capacity_exceeded": round(r["capacity_exceeded"], 1),
            "autonomy_exceeded": round(r["autonomy_exceeded"], 1),
            "stops": [serialize_point(pt) for pt in r["stops"]],
            "full_path": [serialize_point(pt) for pt in r["full_path"]]
        })

    return {
        "fitness": round(eval_details["fitness"], 2),
        "total_distance": round(eval_details["total_distance"], 1),
        "priority_penalty": round(eval_details["priority_penalty"], 1),
        "capacity_penalty": round(eval_details["capacity_penalty"], 1),
        "autonomy_penalty": round(eval_details["autonomy_penalty"], 1),
        "penalty_weights": penalty_weights or {
            "priority": DEFAULT_PRIORITY_PENALTY_WEIGHT,
            "capacity": DEFAULT_CAPACITY_PENALTY_WEIGHT,
            "autonomy": DEFAULT_AUTONOMY_PENALTY_WEIGHT
        },
        "is_feasible": eval_details["is_feasible"],
        "depot": serialize_point(depot),
        "routes": routes_serialized
    }


def build_export_json_from_payload(solution_payload: dict) -> dict:
    """Constrói o dicionário estruturado de exportação JSON (`melhor_rota_hospitalar.json`)."""
    eval_data = solution_payload["evaluation"]
    export_data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "algorithm_key": solution_payload.get("algorithm_key", "genetic_algorithm"),
        "algorithm_name": solution_payload.get("algorithm_name", "Algoritmo Genético"),
        "generation_reached": solution_payload.get("generation", 0),
        "total_generations": solution_payload.get("total_generations", 0),
        "depot": eval_data.get("depot", {}),
        "penalty_weights": eval_data.get("penalty_weights", {
            "priority": DEFAULT_PRIORITY_PENALTY_WEIGHT,
            "capacity": DEFAULT_CAPACITY_PENALTY_WEIGHT,
            "autonomy": DEFAULT_AUTONOMY_PENALTY_WEIGHT
        }),
        "summary": {
            "fitness": eval_data.get("fitness", 0.0),
            "total_distance_px": eval_data.get("total_distance", 0.0),
            "priority_penalty": eval_data.get("priority_penalty", 0.0),
            "capacity_penalty": eval_data.get("capacity_penalty", 0.0),
            "autonomy_penalty": eval_data.get("autonomy_penalty", 0.0),
            "is_feasible": eval_data.get("is_feasible", False),
            "active_vehicles": len(eval_data.get("routes", []))
        },
        "routes": []
    }

    for r in eval_data.get("routes", []):
        export_data["routes"].append({
            "vehicle_id": r["vehicle_id"],
            "vehicle_name": r.get("vehicle_name", f"Veículo {r['vehicle_id']}"),
            "capacity_limit_kg": r.get("capacity_limit_kg", 85.0),
            "autonomy_limit_px": r.get("autonomy_limit_px", 950.0),
            "load_kg": r.get("load_kg", 0.0),
            "distance_px": r.get("distance", 0.0),
            "capacity_exceeded_kg": r.get("capacity_exceeded", 0.0),
            "autonomy_exceeded_px": r.get("autonomy_exceeded", 0.0),
            "stops": [
                {
                    "sequence_order": idx + 1,
                    "id": pt["id"],
                    "name": pt["name"],
                    "priority": pt["priority"],
                    "priority_label": pt["priority_label"],
                    "demand_kg": pt["demand_kg"],
                    "item_description": pt["item_description"],
                    "x": pt["x"],
                    "y": pt["y"],
                    "lat": pt["lat"],
                    "lon": pt["lon"]
                }
                for idx, pt in enumerate(r.get("stops", []))
            ]
        })

    return export_data


# Carrega o cenário hospitalar padrão ao iniciar
depot_init, deliveries_init = get_hospital_scenario()
CURRENT_SCENARIO["depot"] = depot_init
CURRENT_SCENARIO["deliveries"] = deliveries_init


@app.route("/")
def index():
    """Renderiza a interface Web principal."""
    return render_template("index.html")


@app.route("/api/algorithms", methods=["GET"])
def list_algorithms():
    """Retorna o catálogo de algoritmos/heurísticas disponíveis no dispatcher."""
    return jsonify({"algorithms": get_available_algorithms()})


@app.route("/api/scenario", methods=["GET", "POST"])
def handle_scenario():
    """
    Gerencia os pontos de entrega do cenário:
    - mode == 'predefined': carrega as 14 unidades hospitalares pré-definidas;
    - mode == 'random': sorteia `n_deliveries` pontos aleatórios;
    - mode == 'custom': atualiza os pontos com as coordenadas/pesos/prioridades editados pelo usuário.
    """
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        mode = data.get("mode", "predefined")

        if mode == "random":
            n_deliveries = max(4, min(40, int(data.get("n_deliveries", 14))))
            depot, deliveries = generate_random_hospital_scenario(
                n_deliveries=n_deliveries,
                min_x=480, max_x=1040,
                min_y=50, max_y=550
            )
            CURRENT_SCENARIO["depot"] = depot
            CURRENT_SCENARIO["deliveries"] = deliveries

        elif mode == "custom" and "deliveries" in data:
            depot = CURRENT_SCENARIO["depot"]
            custom_list = []
            for idx, item in enumerate(data["deliveries"], start=1):
                px = max(460, min(1070, int(float(item.get("x", 700)))))
                py = max(35, min(565, int(float(item.get("y", 300)))))
                prio = int(item.get("priority", 1))
                prio = prio if prio in (1, 2, 3) else 1
                demand = max(1.0, float(item.get("demand_kg", 10.0)))
                name = str(item.get("name", f"Unidade #{idx:02d}")).strip() or f"Unidade #{idx:02d}"
                desc = str(item.get("item_description", f"Insumo ({PRIORITY_LABELS[prio]})"))

                lat = -23.5587 - ((py - depot.y) * 0.0003)
                lon = -46.6623 + ((px - depot.x) * 0.0003)

                custom_list.append(
                    DeliveryPoint(
                        id=idx,
                        name=name,
                        x=px,
                        y=py,
                        demand_kg=demand,
                        priority=prio,
                        item_description=desc,
                        lat=lat,
                        lon=lon
                    )
                )
            if custom_list:
                CURRENT_SCENARIO["deliveries"] = custom_list

        else:
            depot, deliveries = get_hospital_scenario()
            CURRENT_SCENARIO["depot"] = depot
            CURRENT_SCENARIO["deliveries"] = deliveries

    return jsonify({
        "depot": serialize_point(CURRENT_SCENARIO["depot"]),
        "deliveries": [serialize_point(pt) for pt in CURRENT_SCENARIO["deliveries"]]
    })


@app.route("/api/optimize/stream", methods=["GET"])
def optimize_stream():
    """
    Endpoint de Streaming SSE que lê:
    1) A configuração individual de cada veículo (`vehicles_json`);
    2) Os pesos de penalidade da função Fitness (`priority_penalty_weight`, `capacity_penalty_weight`, `autonomy_penalty_weight`);
    3) O algoritmo escolhido pelo usuário (`algorithm`);
    4) Os hiperparâmetros do método selecionado;
    e transmite cada passo de evolução em tempo real para o navegador.
    """
    algorithm_key = request.args.get("algorithm", "genetic_algorithm")

    # Decodifica a lista individual de veículos enviada pelo frontend (Etapa 2)
    vehicles_json_str = request.args.get("vehicles_json", "")
    parsed_vehicles = None
    if vehicles_json_str:
        try:
            parsed_vehicles = json.loads(vehicles_json_str)
        except Exception:
            parsed_vehicles = None

    vehicles_specs = normalize_vehicles_specs(
        max_vehicles=int(request.args.get("max_vehicles", 3)),
        vehicle_capacity_kg=float(request.args.get("vehicle_capacity_kg", 85.0)),
        vehicle_max_distance=float(request.args.get("vehicle_max_distance", 950.0)),
        vehicles_specs=parsed_vehicles
    )

    # Pesos de penalidade customizáveis na Web
    priority_w = float(request.args.get("priority_penalty_weight", DEFAULT_PRIORITY_PENALTY_WEIGHT))
    capacity_w = float(request.args.get("capacity_penalty_weight", DEFAULT_CAPACITY_PENALTY_WEIGHT))
    autonomy_w = float(request.args.get("autonomy_penalty_weight", DEFAULT_AUTONOMY_PENALTY_WEIGHT))
    penalty_weights = {
        "priority": priority_w,
        "capacity": capacity_w,
        "autonomy": autonomy_w,
    }

    # Coleta todos os hiperparâmetros possíveis para repassar ao dispatcher (Etapa 3)
    params = {
        # Pesos de Penalidade da Função Fitness
        "priority_penalty_weight": priority_w,
        "capacity_penalty_weight": capacity_w,
        "autonomy_penalty_weight": autonomy_w,
        # Parâmetros do Algoritmo Genético (GA)
        "population_size": request.args.get("population_size", 120),
        "n_generations": request.args.get("n_generations", 160),
        "mutation_probability": request.args.get("mutation_probability", 0.45),
        "mutation_intensity": request.args.get("mutation_intensity", 1),
        "use_heuristic_seed": request.args.get("use_heuristic_seed", "true").lower() == "true",
        # Parâmetros do Ant Colony Optimization (ACO)
        "n_ants": request.args.get("n_ants", 35),
        "n_iterations": request.args.get("n_iterations", 80),
        "alpha": request.args.get("alpha", 1.0),
        "beta": request.args.get("beta", 2.5),
        "evaporation_rate": request.args.get("evaporation_rate", 0.15),
        # Parâmetros do Simulated Annealing (SA)
        "initial_temp": request.args.get("initial_temp", 1200.0),
        "cooling_rate": request.args.get("cooling_rate", 0.96),
        # Parâmetros de Nearest Neighbor e Convex Hull
        "nn_generations": request.args.get("nn_generations", 100),
        "nn_priority_weight": request.args.get("nn_priority_weight", 0.85),
        "nn_perturbation": request.args.get("nn_perturbation", 0.35),
        "apply_2opt": request.args.get("apply_2opt", "true").lower() == "true",
        "ch_generations": request.args.get("ch_generations", 100),
        "ch_perturbation": request.args.get("ch_perturbation", 0.35),
        "apply_local_search": request.args.get("apply_local_search", "true").lower() == "true",
    }

    depot = CURRENT_SCENARIO["depot"]
    deliveries = CURRENT_SCENARIO["deliveries"]

    def event_generator():
        for step_data in dispatch_optimization(
            algorithm_key=algorithm_key,
            depot=depot,
            deliveries=deliveries,
            vehicles_specs=vehicles_specs,
            params=params
        ):
            eval_serialized = serialize_evaluation(step_data["eval_details"], depot, penalty_weights)
            payload = {
                "algorithm_key": algorithm_key,
                "algorithm_name": step_data["algorithm_name"],
                "generation": step_data["step"],
                "total_generations": step_data["total_steps"],
                "done": step_data["done"],
                "evaluation": eval_serialized,
                "second_best_coords": step_data.get("second_best_coords", [])
            }
            # Atualiza em memória a última solução avaliada para exportação JSON
            CURRENT_SCENARIO["last_solution"] = payload
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return Response(
        event_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@app.route("/api/solution/generate-json", methods=["POST"])
def generate_solution_json():
    """
    Gera e salva em disco o arquivo `melhor_rota_hospitalar.json` com a melhor solução
    encontrada na simulação (preparado para auditoria e integração com o Gemini na Etapa 4).
    """
    body = request.get_json(silent=True) or {}
    solution_payload = body.get("solution") or CURRENT_SCENARIO.get("last_solution")

    if not solution_payload or "evaluation" not in solution_payload:
        return jsonify({
            "error": "Nenhuma solução de rota foi gerada ainda. Execute a otimização primeiro."
        }), 400

    export_data = build_export_json_from_payload(solution_payload)

    with open(SOLUTION_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    return jsonify({
        "status": "ok",
        "message": "Arquivo melhor_rota_hospitalar.json gerado com sucesso!",
        "file_name": "melhor_rota_hospitalar.json",
        "download_url": "/api/solution/download-json",
        "data": export_data
    })


@app.route("/api/solution/download-json", methods=["GET"])
def download_solution_json():
    """Permite ao usuário baixar o arquivo `melhor_rota_hospitalar.json` gerado."""
    if not os.path.exists(SOLUTION_JSON_PATH):
        return jsonify({
            "error": "O arquivo JSON ainda não foi gerado. Clique em 'Gerar JSON da Solução' primeiro."
        }), 404

    return send_file(
        SOLUTION_JSON_PATH,
        mimetype="application/json",
        as_attachment=True,
        download_name="melhor_rota_hospitalar.json"
    )


@app.route("/api/llm/chat", methods=["POST"])
def llm_driver_chat():
    """
    Etapa 4: Endpoint de Chat do Motorista conectado ao Google Gemini (`gemini-3.8-flash`).
    Usa o JSON da solução (`melhor_rota_hospitalar.json` ou a solução atual em memória)
    como base para responder perguntas sobre a rota, próximo destino, pesos e prioridades.
    """
    body = request.get_json(silent=True) or {}
    user_message = str(body.get("message", "")).strip()
    api_key = str(body.get("api_key", "")).strip() or None
    previous_interaction_id = str(body.get("previous_interaction_id", "")).strip() or None
    vehicle_id_raw = body.get("vehicle_id")
    selected_vehicle_id = int(vehicle_id_raw) if vehicle_id_raw not in (None, "", "all", 0, "0") else None

    if not user_message:
        return jsonify({"error": "Digite uma pergunta para o assistente de rota."}), 400

    # Prioriza a solução atual em memória (ou lê o arquivo melhor_rota_hospitalar.json do disco)
    route_json_data = None
    if CURRENT_SCENARIO.get("last_solution"):
        route_json_data = build_export_json_from_payload(CURRENT_SCENARIO["last_solution"])
        # Salva/atualiza também em disco para manter o JSON sincronizado
        with open(SOLUTION_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(route_json_data, f, ensure_ascii=False, indent=2)
    elif os.path.exists(SOLUTION_JSON_PATH):
        with open(SOLUTION_JSON_PATH, "r", encoding="utf-8") as f:
            route_json_data = json.load(f)

    if not route_json_data:
        return jsonify({
            "error": "Nenhuma rota foi gerada ainda. Execute a otimização primeiro antes de perguntar ao Gemini."
        }), 400

    try:
        result = ask_driver_assistant(
            user_message=user_message,
            route_json_data=route_json_data,
            selected_vehicle_id=selected_vehicle_id,
            previous_interaction_id=previous_interaction_id,
            api_key=api_key
        )
        return jsonify({
            "status": "ok",
            "reply": result["reply"],
            "interaction_id": result["interaction_id"],
            "model": result["model"]
        })
    except Exception as exc:
        return jsonify({
            "error": f"Erro ao consultar o Gemini: {str(exc)}"
        }), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Servidor Web iniciado! Acesse no navegador: http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


