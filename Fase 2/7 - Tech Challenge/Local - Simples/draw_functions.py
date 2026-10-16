# -*- coding: utf-8 -*-
"""
Funções de Visualização (Pygame, Matplotlib e Mapa Interativo HTML/Leaflet)
Tech Challenge - Fase 2 (Projeto 2: Otimização de Rotas para Distribuição de Medicamentos e Insumos)

Baseado no arquivo `draw_functions.py` original de Sérgio Polimante, este módulo foi
expandido e comentado para:
1. Desenhar o gráfico de convergência no Pygame (`draw_plot`);
2. Desenhar os pontos de entrega hospitalares diferenciando a prioridade por cores
   (Crítico = Vermelho, Urgente = Laranja, Regular = Verde) e destacando o Hospital Central (`draw_cities`);
3. Desenhar as sub-rotas de múltiplos veículos (VRP) com cores distintas (`draw_vehicle_routes` e `draw_paths`);
4. Exibir um painel lateral informativo em tempo real com carga, autonomia e status de cada veículo (`draw_status_panel`);
5. Exportar ao final da execução:
   - Um gráfico/mapa estático em PNG (`save_final_static_map`);
   - Um mapa geográfico interativo em HTML com coordenadas reais (`save_interactive_html_map`).
"""

import json
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
import pygame
from typing import List, Tuple, Dict, Any

from genetic_algorithm import (
    DeliveryPoint,
    PRIORITY_DEPOT,
    PRIORITY_REGULAR,
    PRIORITY_URGENT,
    PRIORITY_CRITICAL,
    PRIORITY_LABELS
)

matplotlib.use("Agg")

# ==============================================================================
# PALETA DE CORES PARA PRIORIDADES E VEÍCULOS
# ==============================================================================

# Cores RGB por nível de prioridade da entrega
PRIORITY_COLORS = {
    PRIORITY_DEPOT: (20, 40, 90),      # Azul Marinho Escuro (Hospital Central / Depósito)
    PRIORITY_CRITICAL: (220, 38, 38),  # Vermelho (Medicamentos Críticos / Emergência / UTI)
    PRIORITY_URGENT: (234, 138, 0),    # Laranja (Medicamentos Urgentes / Refrigerados)
    PRIORITY_REGULAR: (22, 163, 74),   # Verde (Insumos Regulares)
}

# Cores RGB distintas para identificar a rota de cada veículo da frota
VEHICLE_COLORS = [
    (37, 99, 235),   # Veículo 1: Azul Royal
    (147, 51, 234),  # Veículo 2: Roxo / Violeta
    (8, 145, 178),   # Veículo 3: Ciano Escuro / Turquesa
    (219, 39, 119),  # Veículo 4: Magenta
    (101, 163, 13),  # Veículo 5: Verde Oliva
]

VEHICLE_HEX_COLORS = ["#2563eb", "#9333ea", "#0891b2", "#db2777", "#65a30d"]


def draw_plot(
    screen: pygame.Surface,
    x: list,
    y: list,
    x_label: str = 'Geração',
    y_label: str = 'Fitness (Custo Total)'
) -> None:
    """
    Desenha o gráfico de evolução do Fitness no canto superior esquerdo da janela do Pygame.
    Mantém a estrutura original utilizando Matplotlib + FigureCanvasAgg.
    """
    fig, ax = plt.subplots(figsize=(4.2, 2.7), dpi=100)
    ax.plot(x, y, color="#2563eb", linewidth=1.8)
    ax.set_ylabel(y_label, fontsize=9)
    ax.set_xlabel(x_label, fontsize=9)
    ax.set_title("Evolução do Algoritmo Genético", fontsize=10, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()

    canvas = FigureCanvasAgg(fig)
    canvas.draw()

    size = canvas.get_width_height()
    if hasattr(canvas, "buffer_rgba"):
        raw_data = canvas.buffer_rgba()
        surf = pygame.image.frombuffer(raw_data, size, "RGBA")
    else:
        renderer = canvas.get_renderer()
        raw_data = renderer.tostring_rgb()
        surf = pygame.image.fromstring(raw_data, size, "RGB")

    screen.blit(surf, (10, 10))
    plt.close(fig)


def draw_cities(
    screen: pygame.Surface,
    cities_locations: List[Any],
    rgb_color: Tuple[int, int, int],
    node_radius: int,
    depot: DeliveryPoint = None
) -> None:
    """
    Desenha os pontos de entrega e o Hospital Central na tela do Pygame.
    Se os elementos forem objetos `DeliveryPoint`, aplica automaticamente a cor
    correspondente à prioridade médica e exibe o ID e peso (em kg) ao lado do ponto.
    """
    pygame.font.init()
    font_small = pygame.font.SysFont("Arial", 12, bold=True)
    font_sub = pygame.font.SysFont("Arial", 11, bold=False)

    # Desenha primeiro a grade suave de fundo na área do mapa
    map_rect = pygame.Rect(450, 15, 635, 570)
    pygame.draw.rect(screen, (248, 250, 252), map_rect)
    pygame.draw.rect(screen, (203, 213, 225), map_rect, width=2)

    # Desenha cada ponto de entrega
    for city in cities_locations:
        if isinstance(city, DeliveryPoint):
            pos = city.pos
            color = PRIORITY_COLORS.get(city.priority, rgb_color)

            # Círculo externo branco para dar contraste sobre as linhas de rota
            pygame.draw.circle(screen, (255, 255, 255), pos, node_radius + 3)
            pygame.draw.circle(screen, color, pos, node_radius)
            pygame.draw.circle(screen, (30, 30, 30), pos, node_radius, width=1)

            # Rótulo curto com ID e peso em kg
            label_surf = font_small.render(f"#{city.id} ({int(city.demand_kg)}kg)", True, (20, 20, 20))
            screen.blit(label_surf, (pos[0] + node_radius + 4, pos[1] - 10))
        else:
            pygame.draw.circle(screen, rgb_color, city, node_radius)

    # Desenha o Hospital Central (Depósito) com destaque especial no mapa
    if depot is not None:
        d_pos = depot.pos
        pygame.draw.circle(screen, (250, 204, 21), d_pos, node_radius + 6)       # Anel dourado externo
        pygame.draw.circle(screen, PRIORITY_COLORS[PRIORITY_DEPOT], d_pos, node_radius + 3)
        # Cruz branca simbolizando o Hospital Central
        pygame.draw.line(screen, (255, 255, 255), (d_pos[0] - 5, d_pos[1]), (d_pos[0] + 5, d_pos[1]), width=3)
        pygame.draw.line(screen, (255, 255, 255), (d_pos[0], d_pos[1] - 5), (d_pos[0], d_pos[1] + 5), width=3)

        depot_label = font_small.render("HOSPITAL CENTRAL (CD)", True, (20, 40, 90))
        screen.blit(depot_label, (d_pos[0] - 70, d_pos[1] + node_radius + 6))


def draw_paths(
    screen: pygame.Surface,
    path: List[Any],
    rgb_color: Tuple[int, int, int],
    width: int = 1
) -> None:
    """
    Desenha um caminho contínuo simples no Pygame (usado para exibir a 2ª melhor rota em cinza ao fundo,
    mantendo a funcionalidade original do `tsp.py`).
    """
    if len(path) < 2:
        return
    coords = [pt.pos if isinstance(pt, DeliveryPoint) else pt for pt in path]
    pygame.draw.lines(screen, rgb_color, True, coords, width=width)


def draw_vehicle_routes(
    screen: pygame.Surface,
    routes: List[Dict[str, Any]],
    width: int = 3
) -> None:
    """
    Desenha as rotas de múltiplos veículos (VRP), cada veículo com uma cor distinta,
    incluindo setas/indicadores da ordem de visita em cada sub-rota.
    """
    pygame.font.init()
    font_order = pygame.font.SysFont("Arial", 11, bold=True)

    for idx, route in enumerate(routes):
        color = VEHICLE_COLORS[idx % len(VEHICLE_COLORS)]
        full_path = route["full_path"]
        coords = [pt.pos for pt in full_path]

        if len(coords) >= 2:
            # Desenha as linhas conectando Depósito -> Paradas -> Depósito
            pygame.draw.lines(screen, color, False, coords, width=width)

            # Desenha uma pequena seta na metade de cada trecho para indicar a direção do veículo
            for i in range(len(coords) - 1):
                x1, y1 = coords[i]
                x2, y2 = coords[i + 1]
                mid_x, mid_y = (x1 + x2) // 2, (y1 + y2) // 2
                pygame.draw.circle(screen, color, (mid_x, mid_y), 4)

            # Exibe a ordem de parada do veículo (1º, 2º, 3º...) abaixo do ponto
            for stop_order, stop in enumerate(route["stops"], start=1):
                badge = font_order.render(f"V{route['vehicle_id']}:{stop_order}º", True, color)
                screen.blit(badge, (stop.x + 12, stop.y + 3))


def draw_status_panel(
    screen: pygame.Surface,
    generation: int,
    eval_details: Dict[str, Any],
    max_vehicles: int,
    vehicle_capacity_kg: float,
    vehicle_max_distance: float
) -> None:
    """
    Desenha o painel lateral esquerdo (abaixo do gráfico Matplotlib) com todas as métricas
    da solução atual: Geração, Fitness, Distância, Penalidades, uso de carga/autonomia por veículo
    e legenda das cores de prioridade.
    """
    pygame.font.init()
    font_title = pygame.font.SysFont("Arial", 14, bold=True)
    font_text = pygame.font.SysFont("Arial", 12)
    font_small = pygame.font.SysFont("Arial", 11)

    x0 = 15
    y = 290

    # Bloco 1: Resumo Geral da Geração
    title_surf = font_title.render(f"Geração: {generation}  |  Fitness Total: {eval_details['fitness']:.1f}", True, (15, 23, 42))
    screen.blit(title_surf, (x0, y))
    y += 20

    dist_text = (
        f"Distância Total: {eval_details['total_distance']:.1f} px   |   "
        f"Penalidade Prioridade: {eval_details['priority_penalty']:.1f}"
    )
    screen.blit(font_text.render(dist_text, True, (51, 65, 85)), (x0, y))
    y += 18

    status_str = "VIÁVEL (Todas as restrições atendidas)" if eval_details["is_feasible"] else "ATENÇÃO: Limite excedido!"
    status_color = (22, 163, 74) if eval_details["is_feasible"] else (220, 38, 38)
    screen.blit(font_text.render(f"Status da Frota: {status_str}", True, status_color), (x0, y))
    y += 22

    # Bloco 2: Detalhamento por Veículo
    screen.blit(font_title.render(f"Frota de Veículos ({len(eval_details['routes'])}/{max_vehicles} em operação):", True, (15, 23, 42)), (x0, y))
    y += 19

    for idx, route in enumerate(eval_details["routes"]):
        v_color = VEHICLE_COLORS[idx % len(VEHICLE_COLORS)]
        pygame.draw.rect(screen, v_color, (x0, y + 3, 12, 12))

        stops_str = " -> ".join([f"#{pt.id}" for pt in route["stops"]])
        v_line1 = (
            f"Veículo {route['vehicle_id']}: Carga {route['load_kg']:.0f}/{vehicle_capacity_kg:.0f}kg | "
            f"Dist. {route['distance']:.0f}/{vehicle_max_distance:.0f}px"
        )
        screen.blit(font_text.render(v_line1, True, (30, 41, 59)), (x0 + 18, y))
        y += 15
        screen.blit(font_small.render(f"   Rota: CD -> {stops_str} -> CD", True, (71, 85, 105)), (x0 + 18, y))
        y += 18

    # Bloco 3: Legenda de Prioridades Médicas
    y = max(y + 4, 515)
    screen.blit(font_title.render("Legenda de Prioridades Médicas:", True, (15, 23, 42)), (x0, y))
    y += 18

    legend_items = [
        (PRIORITY_COLORS[PRIORITY_CRITICAL], "Crítico (UTI/Emergência)"),
        (PRIORITY_COLORS[PRIORITY_URGENT], "Urgente (Refrigerados/UPA)"),
        (PRIORITY_COLORS[PRIORITY_REGULAR], "Regular (Insumos Básicos)"),
    ]
    lx = x0
    for color, label in legend_items:
        pygame.draw.circle(screen, color, (lx + 6, y + 7), 6)
        lbl_surf = font_small.render(label, True, (30, 41, 59))
        screen.blit(lbl_surf, (lx + 15, y))
        lx += lbl_surf.get_width() + 26

    y += 20
    screen.blit(font_small.render("Dica: Pressione [Q] ou feche a janela para encerrar e salvar os mapas/relatórios.", True, (100, 116, 139)), (x0, y))


def save_final_static_map(
    depot: DeliveryPoint,
    eval_details: Dict[str, Any],
    best_fitness_history: List[float],
    output_path: str
) -> None:
    """
    Salva uma figura PNG de alta resolução contendo:
    - Painel esquerdo: Curva de convergência do Algoritmo Genético;
    - Painel direito: Mapa das rotas otimizadas por veículo e prioridades de entrega.
    """
    fig, (ax_conv, ax_map) = plt.subplots(1, 2, figsize=(14, 6), dpi=150)

    # 1. Gráfico de Convergência
    ax_conv.plot(range(1, len(best_fitness_history) + 1), best_fitness_history, color="#2563eb", linewidth=2)
    ax_conv.set_title("Convergência do Algoritmo Genético", fontsize=12, fontweight="bold")
    ax_conv.set_xlabel("Geração")
    ax_conv.set_ylabel("Fitness (Distância + Penalidades)")
    ax_conv.grid(True, linestyle="--", alpha=0.5)

    # 2. Mapa das Rotas Otimizadas
    for idx, route in enumerate(eval_details["routes"]):
        hex_color = VEHICLE_HEX_COLORS[idx % len(VEHICLE_HEX_COLORS)]
        xs = [pt.x for pt in route["full_path"]]
        ys = [pt.y for pt in route["full_path"]]
        ax_map.plot(
            xs, ys,
            color=hex_color,
            linewidth=2.2,
            marker="",
            label=f"Veículo {route['vehicle_id']} ({route['load_kg']:.0f}kg, {route['distance']:.0f}px)"
        )

        # Numera a ordem de visita de cada parada
        for order_idx, stop in enumerate(route["stops"], start=1):
            ax_map.annotate(
                f"#{stop.id} ({order_idx}º)",
                (stop.x, stop.y),
                textcoords="offset points",
                xytext=(6, 6),
                fontsize=8,
                fontweight="bold",
                color=hex_color
            )

    # Desenha os pontos conforme sua prioridade médica
    all_stops = [stop for route in eval_details["routes"] for stop in route["stops"]]
    for prio, color_hex, label in [
        (PRIORITY_CRITICAL, "#dc2626", "Prioridade Crítica"),
        (PRIORITY_URGENT, "#ea8a00", "Prioridade Urgente"),
        (PRIORITY_REGULAR, "#16a34a", "Prioridade Regular")
    ]:
        pts = [p for p in all_stops if p.priority == prio]
        if pts:
            ax_map.scatter(
                [p.x for p in pts],
                [p.y for p in pts],
                c=color_hex,
                s=90,
                zorder=5,
                edgecolors="black",
                label=label
            )

    # Destaca o Hospital Central
    ax_map.scatter([depot.x], [depot.y], c="#14285a", s=180, marker="s", zorder=6, edgecolors="#facc15", linewidths=2, label="Hospital Central (CD)")
    ax_map.invert_yaxis()  # Mantém a mesma orientação vertical do Pygame
    ax_map.set_title("Mapa de Rotas Otimizadas por Veículo (VRP Hospitalar)", fontsize=12, fontweight="bold")
    ax_map.set_xlabel("Coordenada X (px)")
    ax_map.set_ylabel("Coordenada Y (px)")
    ax_map.legend(loc="best", fontsize=8)
    ax_map.grid(True, linestyle=":", alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close(fig)


def save_interactive_html_map(
    depot: DeliveryPoint,
    eval_details: Dict[str, Any],
    output_html_path: str
) -> None:
    """
    Gera um mapa geográfico interativo em HTML utilizando Leaflet.js (OpenStreetMap).
    Não requer instalação de pacotes externos extras e permite dar zoom, clicar nos
    hospitais/pacientes para ver os medicamentos entregues, prioridade, peso e qual
    veículo realiza o atendimento.
    """
    markers_data = [{
        "id": depot.id,
        "name": depot.name,
        "lat": depot.lat,
        "lon": depot.lon,
        "priority": PRIORITY_LABELS[depot.priority],
        "color": "#14285a",
        "demand_kg": 0,
        "item": depot.item_description,
        "vehicle": "Todos (Ponto de Partida/Retorno)",
        "stop_order": 0
    }]

    polylines_data = []

    for idx, route in enumerate(eval_details["routes"]):
        hex_color = VEHICLE_HEX_COLORS[idx % len(VEHICLE_HEX_COLORS)]
        coords = [[pt.lat, pt.lon] for pt in route["full_path"]]
        polylines_data.append({
            "vehicle_id": route["vehicle_id"],
            "color": hex_color,
            "load_kg": route["load_kg"],
            "distance": round(route["distance"], 1),
            "coords": coords
        })

        for stop_order, stop in enumerate(route["stops"], start=1):
            p_color = (
                "#dc2626" if stop.priority == PRIORITY_CRITICAL
                else "#ea8a00" if stop.priority == PRIORITY_URGENT
                else "#16a34a"
            )
            markers_data.append({
                "id": stop.id,
                "name": stop.name,
                "lat": stop.lat,
                "lon": stop.lon,
                "priority": PRIORITY_LABELS[stop.priority],
                "color": p_color,
                "demand_kg": stop.demand_kg,
                "item": stop.item_description,
                "vehicle": f"Veículo {route['vehicle_id']}",
                "stop_order": stop_order
            })

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Mapa Interativo de Rotas Hospitalares - Tech Challenge Fase 2</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; font-family: Arial, sans-serif; display: flex; height: 100vh; }}
        #sidebar {{ width: 360px; padding: 16px; background: #f8fafc; border-right: 1px solid #cbd5e1; overflow-y: auto; }}
        #map {{ flex: 1; height: 100vh; }}
        h2 {{ margin-top: 0; color: #0f172a; font-size: 18px; }}
        .card {{ background: white; padding: 12px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 12px; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; color: white; font-size: 12px; font-weight: bold; }}
        ul {{ padding-left: 18px; margin: 6px 0; font-size: 13px; }}
    </style>
</head>
<body>
    <div id="sidebar">
        <h2>Logística Hospitalar (AG + VRP)</h2>
        <div class="card">
            <strong>Resumo da Solução Otimizada</strong><br><br>
            Fitness Total: <b>{eval_details['fitness']:.2f}</b><br>
            Distância Total: <b>{eval_details['total_distance']:.1f} px</b><br>
            Penalidade de Prioridade: <b>{eval_details['priority_penalty']:.1f}</b><br>
            Status: <b style="color: {'#16a34a' if eval_details['is_feasible'] else '#dc2626'}">
                {'Viável (Dentro dos limites)' if eval_details['is_feasible'] else 'Com violação'}
            </b>
        </div>
        <div id="routes-summary"></div>
    </div>
    <div id="map"></div>
    <script>
        const markers = {json.dumps(markers_data, ensure_ascii=False)};
        const routes = {json.dumps(polylines_data, ensure_ascii=False)};

        const map = L.map('map').setView([{depot.lat}, {depot.lon}], 12);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; OpenStreetMap contributors'
        }}).addTo(map);

        const summaryDiv = document.getElementById('routes-summary');
        routes.forEach(r => {{
            L.polyline(r.coords, {{ color: r.color, weight: 4, opacity: 0.85 }}).addTo(map);
            const card = document.createElement('div');
            card.className = 'card';
            const stopsList = markers
                .filter(m => m.vehicle === 'Veículo ' + r.vehicle_id)
                .sort((a, b) => a.stop_order - b.stop_order)
                .map(m => `<li><b>${{m.stop_order}}º</b> - #${{m.id}} ${{m.name}} (${{m.demand_kg}}kg - ${{m.priority}})</li>`)
                .join('');
            card.innerHTML = `
                <span class="badge" style="background:${{r.color}}">Veículo ${{r.vehicle_id}}</span>
                <span style="font-size:13px; margin-left:6px;">Carga: <b>${{r.load_kg}}kg</b> | Dist: <b>${{r.distance}}px</b></span>
                <ul>${{stopsList}}</ul>
            `;
            summaryDiv.appendChild(card);
        }});

        markers.forEach(m => {{
            const radius = m.id === 0 ? 11 : 8;
            const marker = L.circleMarker([m.lat, m.lon], {{
                radius: radius,
                fillColor: m.color,
                color: m.id === 0 ? '#facc15' : '#1e293b',
                weight: m.id === 0 ? 3 : 1.5,
                opacity: 1,
                fillOpacity: 0.95
            }}).addTo(map);

            marker.bindPopup(`
                <b>#${{m.id}} - ${{m.name}}</b><br>
                <b>Prioridade:</b> ${{m.priority}}<br>
                <b>Insumo/Medicamento:</b> ${{m.item}}<br>
                <b>Peso da Carga:</b> ${{m.demand_kg}} kg<br>
                <b>Atendimento:</b> ${{m.vehicle}} ${{m.stop_order > 0 ? '(' + m.stop_order + 'ª parada)' : ''}}
            `);
        }});
    </script>
</body>
</html>
"""
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
