# -*- coding: utf-8 -*-
"""
Gera o arquivo RELATORIO_TECNICO.docx profissional, formatado com capa,
paginacao pagina a pagina, paleta institucional FIAP/Slate, caixas de destaque,
tabelas estilizadas e imagem embutida a partir de RELATORIO_TECNICO.md.
"""

import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCX_PATH = os.path.join(BASE_DIR, "RELATORIO_TECNICO.docx")
IMG_PATH = os.path.join(BASE_DIR, "..", "Local - Simples", "mapa_rotas_otimizadas.png")

# Cores
COLOR_PRIMARY = RGBColor(15, 23, 42)       # Navy escuro #0F172A
COLOR_ACCENT = RGBColor(237, 20, 91)      # FIAP Pink #ED145B
COLOR_TEXT = RGBColor(30, 41, 59)         # Dark slate #1E293B
COLOR_MUTED = RGBColor(100, 116, 139)     # Gray #64748B
COLOR_BLUE = RGBColor(2, 132, 199)        # Blue #0284C7

HEX_PRIMARY = "0F172A"
HEX_ACCENT = "ED145B"
HEX_BG_LIGHT = "F8FAFC"
HEX_BG_DARK = "0F172A"
HEX_BORDER = "CBD5E1"
HEX_BLUE_BORDER = "0284C7"
HEX_PINK_BORDER = "ED145B"

doc = Document()

# Configuração de Margens (A4)
section = doc.sections[0]
section.page_width = Inches(8.27)
section.page_height = Inches(11.69)
section.top_margin = Inches(0.8)
section.bottom_margin = Inches(0.8)
section.left_margin = Inches(0.8)
section.right_margin = Inches(0.8)

# Configuração do cabeçalho diferente na primeira página
section.different_first_page_header_footer = True

# Cabeçalho da página 2 em diante
header = section.header
p_head = header.paragraphs[0]
p_head.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r_head = p_head.add_run("FIAP Pós-Tech: IA para Devs • Tech Challenge Fase 2 | André Capela")
r_head.font.name = "Segoe UI"
r_head.font.size = Pt(8)
r_head.font.color.rgb = COLOR_MUTED

# Rodapé da página 2 em diante
footer = section.footer
p_foot = footer.paragraphs[0]
p_foot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r_foot = p_foot.add_run("Caixeiro Viajante Médico (VRP Hospitalar)")
r_foot.font.name = "Segoe UI"
r_foot.font.size = Pt(8)
r_foot.font.color.rgb = COLOR_MUTED


def set_cell_background(cell, hex_color):
    """Define a cor de fundo de uma célula da tabela."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)


def set_cell_left_border(cell, hex_color, size="36"):
    """Adiciona uma borda esquerda espessa e remove as outras."""
    tcPr = cell._tc.get_or_add_tcPr()
    borders_elm = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'  <w:top w:val="none"/>'
        f'  <w:left w:val="single" w:sz="{size}" w:space="0" w:color="{hex_color}"/>'
        f'  <w:bottom w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders_elm)


def set_cell_padding(cell, top=140, bottom=140, left=180, right=180):
    """Ajusta padding interno da célula em dxa."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'  <w:top w:w="{top}" w:type="dxa"/>'
        f'  <w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'  <w:left w:w="{left}" w:type="dxa"/>'
        f'  <w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def add_callout(doc, text_content, title="", hex_border=HEX_PINK_BORDER, hex_bg=HEX_BG_LIGHT):
    """Cria uma caixa de destaque elegante com borda lateral colorida."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    
    cell = table.cell(0, 0)
    cell.width = Inches(6.67)
    set_cell_background(cell, hex_bg)
    set_cell_left_border(cell, hex_border, size="36")
    set_cell_padding(cell, top=140, bottom=140, left=200, right=160)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    
    if title:
        r_title = p.add_run(title + "\n")
        r_title.bold = True
        r_title.font.name = "Segoe UI"
        r_title.font.size = Pt(9.5)
        r_title.font.color.rgb = COLOR_PRIMARY
        
    r_body = p.add_run(text_content)
    r_body.font.name = "Segoe UI"
    r_body.font.size = Pt(9)
    r_body.font.color.rgb = COLOR_TEXT
    
    # Espaçamento após tabela
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(4)


def add_code_diagram(doc, diagram_text):
    """Cria uma caixa com fundo escuro estilo console/terminal para diagramas."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    
    cell = table.cell(0, 0)
    cell.width = Inches(6.67)
    set_cell_background(cell, HEX_BG_DARK)
    set_cell_padding(cell, top=140, bottom=140, left=160, right=140)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders_elm = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="1E293B"/>'
        f'  <w:left w:val="single" w:sz="4" w:space="0" w:color="1E293B"/>'
        f'  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="1E293B"/>'
        f'  <w:right w:val="single" w:sz="4" w:space="0" w:color="1E293B"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders_elm)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    
    run = p.add_run(diagram_text)
    run.font.name = "Cascadia Code"
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(241, 245, 249)
    
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(4)


def add_heading_1(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.bold = True
    run.font.name = "Segoe UI"
    run.font.size = Pt(15)
    run.font.color.rgb = COLOR_PRIMARY
    return p


def add_heading_2(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.bold = True
    run.font.name = "Segoe UI"
    run.font.size = Pt(11.5)
    run.font.color.rgb = COLOR_PRIMARY
    return p


def add_heading_3(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.bold = True
    run.font.name = "Segoe UI"
    run.font.size = Pt(10)
    run.font.color.rgb = COLOR_PRIMARY
    return p


def add_body_p(doc, text, bold_prefix="", italic=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.line_spacing = 1.15
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = "Segoe UI"
        r_pre.font.size = Pt(10)
        r_pre.font.color.rgb = COLOR_TEXT
        
    r_body = p.add_run(text)
    r_body.italic = italic
    r_body.font.name = "Segoe UI"
    r_body.font.size = Pt(10)
    r_body.font.color.rgb = COLOR_TEXT
    return p


def add_bullet(doc, text, bold_prefix=""):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = "Segoe UI"
        r_pre.font.size = Pt(9.5)
        r_pre.font.color.rgb = COLOR_TEXT
        
    r_body = p.add_run(text)
    r_body.font.name = "Segoe UI"
    r_body.font.size = Pt(9.5)
    r_body.font.color.rgb = COLOR_TEXT
    return p


# ==============================================================================
# PÁGINA 1: CAPA
# ==============================================================================

# Espaçamento superior da capa
p_space = doc.add_paragraph()
p_space.paragraph_format.space_before = Pt(60)

# Faixa Institucional
p_badge = doc.add_paragraph()
r_badge = p_badge.add_run("FIAP • PÓS-TECH EM INTELIGÊNCIA ARTIFICIAL PARA DESENVOLVEDORES")
r_badge.bold = True
r_badge.font.name = "Segoe UI"
r_badge.font.size = Pt(9.5)
r_badge.font.color.rgb = COLOR_ACCENT

# Título Principal
p_title = doc.add_paragraph()
p_title.paragraph_format.space_before = Pt(10)
p_title.paragraph_format.space_after = Pt(4)
r_title = p_title.add_run("TECH CHALLENGE — FASE 2")
r_title.bold = True
r_title.font.name = "Segoe UI"
r_title.font.size = Pt(26)
r_title.font.color.rgb = COLOR_PRIMARY

# Subtítulo
p_sub = doc.add_paragraph()
p_sub.paragraph_format.space_before = Pt(0)
p_sub.paragraph_format.space_after = Pt(14)
r_sub = p_sub.add_run("Caixeiro Viajante Médico (VRP Hospitalar)")
r_sub.bold = True
r_sub.font.name = "Segoe UI"
r_sub.font.size = Pt(15)
r_sub.font.color.rgb = COLOR_ACCENT

# Descrição do Projeto na Capa
p_desc = doc.add_paragraph()
p_desc.paragraph_format.space_before = Pt(0)
p_desc.paragraph_format.space_after = Pt(180)
p_desc.paragraph_format.line_spacing = 1.25
r_desc = p_desc.add_run(
    "Sistema de Otimização Multicritério de Rotas para Distribuição de Medicamentos e Insumos Hospitalares "
    "utilizando Algoritmos Genéticos Evolucionários e Assistente Copiloto integrado ao Google Gemini."
)
r_desc.font.name = "Segoe UI"
r_desc.font.size = Pt(11)
r_desc.font.color.rgb = COLOR_MUTED

# Caixa de Identificação do Aluno / Instituição
table_cover = doc.add_table(rows=1, cols=1)
table_cover.alignment = WD_TABLE_ALIGNMENT.CENTER
table_cover.autofit = False
c_cov = table_cover.cell(0, 0)
c_cov.width = Inches(6.67)
set_cell_background(c_cov, HEX_BG_LIGHT)
set_cell_left_border(c_cov, HEX_ACCENT, size="36")
set_cell_padding(c_cov, top=160, bottom=160, left=200, right=160)

p_cov = c_cov.paragraphs[0]
p_cov.paragraph_format.space_before = Pt(0)
p_cov.paragraph_format.space_after = Pt(0)
p_cov.paragraph_format.line_spacing = 1.25

r1 = p_cov.add_run("André Capela\n")
r1.bold = True
r1.font.name = "Segoe UI"
r1.font.size = Pt(13)
r1.font.color.rgb = COLOR_PRIMARY

r2 = p_cov.add_run("E-mail: ")
r2.bold = True
r2.font.name = "Segoe UI"
r2.font.size = Pt(9.5)
r2.font.color.rgb = COLOR_TEXT
r3 = p_cov.add_run("andr.capela@gmail.com\n")
r3.font.name = "Segoe UI"
r3.font.size = Pt(9.5)
r3.font.color.rgb = COLOR_MUTED

r4 = p_cov.add_run("Curso: ")
r4.bold = True
r4.font.name = "Segoe UI"
r4.font.size = Pt(9.5)
r4.font.color.rgb = COLOR_TEXT
r5 = p_cov.add_run("Pós-Graduação em Inteligência Artificial para Desenvolvedores\n")
r5.font.name = "Segoe UI"
r5.font.size = Pt(9.5)
r5.font.color.rgb = COLOR_MUTED

r6 = p_cov.add_run("Instituição: ")
r6.bold = True
r6.font.name = "Segoe UI"
r6.font.size = Pt(9.5)
r6.font.color.rgb = COLOR_TEXT
r7 = p_cov.add_run("Faculdade de Informática e Administração Paulista (FIAP)\n")
r7.font.name = "Segoe UI"
r7.font.size = Pt(9.5)
r7.font.color.rgb = COLOR_MUTED

r8 = p_cov.add_run("Data de Entrega: ")
r8.bold = True
r8.font.name = "Segoe UI"
r8.font.size = Pt(9.5)
r8.font.color.rgb = COLOR_TEXT
r9 = p_cov.add_run("02 de Novembro de 2026")
r9.font.name = "Segoe UI"
r9.font.size = Pt(9.5)
r9.font.color.rgb = COLOR_MUTED

doc.add_page_break()


# ==============================================================================
# PÁGINA 2: SUMÁRIO EXECUTIVO E LINKS
# ==============================================================================
add_heading_1(doc, "Sumário Executivo e Links Oficiais de Entrega")

add_body_p(
    doc,
    "Este relatório técnico documenta a concepção, modelagem matemática, experimentação e implantação em nuvem da solução para o "
    "Tech Challenge — Fase 2 (Projeto 2: Otimização de Rotas para Distribuição de Medicamentos e Insumos)."
)
add_body_p(
    doc,
    "O projeto expande o problema clássico do Caixeiro Viajante (TSP) para o contexto de Roteamento de Veículos com Restrições de Capacidade, "
    "Autonomia e Prioridades Clínicas (CDVRP-MP), atendendo a 100% dos requisitos obrigatórios e opcionais previstos no edital."
)

add_heading_2(doc, "Links Oficiais de Submissão")

add_callout(
    doc,
    "https://github.com/AndrCapela/FIAP---IA-para-devs/tree/main/Fase%202/7%20-%20Tech%20Challenge/Web%20-%20Completo",
    title="📦 1. Repositório Git (Código-Fonte Completo e Documentação Técnica)",
    hex_border=HEX_BLUE_BORDER
)

add_callout(
    doc,
    "https://youtu.be/d2x2oioqB9E",
    title="🎥 2. Vídeo de Demonstração e Apresentação (YouTube)",
    hex_border=HEX_PINK_BORDER
)

add_callout(
    doc,
    "https://app.143.95.175.167.nip.io  (Ambiente conteinerizado com Nginx, Gunicorn e SSL Let's Encrypt)",
    title="☁️ 3. Demonstração em Produção na Nuvem (VPS com Docker)",
    hex_border=HEX_BLUE_BORDER
)

add_heading_2(doc, "Estrutura dos Entregáveis no Repositório")
add_bullet(doc, "Núcleo desacoplado com as regras de negócio hospitalar, decodificação da frota e cálculo da função fitness multicritério;", bold_prefix="vrp_core.py: ")
add_bullet(doc, "Implementação especializada do Algoritmo Genético (Torneio, Roleta, OX1 e Mutação Híbrida 2-opt/Swap/Crítico);", bold_prefix="genetic_algorithm.py: ")
add_bullet(doc, "4 meta-heurísticas adicionais implementadas para estudo comparativo isonômico (ACO, SA, NN e Convex Hull);", bold_prefix="algo_*.py: ")
add_bullet(doc, "Copiloto com Google Gemini (Interactions API) para orientações operacionais a motoristas e relatórios gerenciais;", bold_prefix="llm_driver_assistant.py: ")
add_bullet(doc, "Aplicação Web interativa em tempo real com streaming SSE e simulação gráfica com setas de sentido em Canvas 2D;", bold_prefix="web_app.py & templates/index.html: ")
add_bullet(doc, "Suíte com 7 testes unitários automatizados validando toda a cadeia de execução e regras de negócio;", bold_prefix="test_vrp_system.py: ")
add_bullet(doc, "Receitas completas de conteinerização prontas para deploy em produção em VPS.", bold_prefix="Dockerfile & docker-compose.yml: ")

doc.add_page_break()


# ==============================================================================
# PÁGINA 3: INTRODUÇÃO E FORMULAÇÃO DO PROBLEMA
# ==============================================================================
add_heading_1(doc, "1. Introdução e Formulação do Problema")

add_body_p(
    doc,
    "No ambiente de logística hospitalar universitária, a eficiência das rotas de distribuição de insumos farmacêuticos possui "
    "impacto direto sobre desfechos clínicos. Enquanto o problema clássico do Caixeiro Viajante (TSP) procura apenas o menor "
    "circuito fechado para visitar N cidades com um único agente viajante, a operação real de saúde exige uma extensão substancial para "
    "o Problema de Roteamento de Veículos (VRP — Vehicle Routing Problem)."
)

add_heading_2(doc, "Desafios e Restrições do Domínio Hospitalar")
add_bullet(
    doc,
    "O Hospital Universitário Central dispõe de veículos com restrições físicas distintas. Cada veículo v possui capacidade nominal máxima de carga em quilogramas (Cv) e limite individual de autonomia máxima de deslocamento (Av) imposto pela bateria ou tanque.",
    bold_prefix="1. Frota Múltipla Heterogênea: "
)
add_bullet(
    doc,
    "A gravidade dos medicamentos transportados é estratificada em três patamares com requisitos estritos de tempo:\n"
    "• Nível 3 — Crítico (UTI / Emergência): Bolsas de sangue, kits de intubação, quimioterápicos termolábeis e cilindros de O2. Devem ser entregues nas primeiras paradas do veículo.\n"
    "• Nível 2 — Urgente (Refrigerados / Pronto-Atendimento): Insulinas refrigeradas, antibióticos pediátricos e anticoagulantes.\n"
    "• Nível 1 — Regular: Insumos ambulatoriais básicos de rotina (soro fisiológico, seringas, ataduras e luvas).",
    bold_prefix="2. Severidade e Prioridades Médicas: "
)
add_bullet(
    doc,
    "Todos os veículos iniciam suas viagens carregados no Hospital Central (Depósito #0), percorrem suas respectivas sub-rotas e devem regressar com segurança ao mesmo hospital para higienização e novos ciclos.",
    bold_prefix="3. Retorno Obrigatório ao Depósito Central: "
)

add_heading_2(doc, "Modelagem Matemática da Função Fitness Multicritério")
add_body_p(
    doc,
    "O problema foi modelado como uma otimização com função objetivo de minimização, onde o custo global de uma solução é dado pela soma da distância percorrida somada às penalidades das restrições:"
)

add_callout(
    doc,
    "Fitness Total = Distância Total + Penalidade(Prioridade) + Penalidade(Carga) + Penalidade(Autonomia)",
    title="Fórmula do Fitness Global (Minimização)",
    hex_border=HEX_ACCENT
)

add_body_p(
    doc,
    "Qualquer violação física de sobrecarga ou esgotamento de combustível recebe multas rigorosas (penalty functions), "
    "transformando restrições rígidas em uma superfície contínua que guia os operadores estocásticos em direção a soluções 100% viáveis."
)

doc.add_page_break()


# ==============================================================================
# PÁGINA 4: ALGORITMO GENÉTICO
# ==============================================================================
add_heading_1(doc, "2. Implementação do Algoritmo Genético para Roteamento")

add_body_p(
    doc,
    "O Algoritmo Genético (GA) foi reestruturado a partir do código base para operar exclusivamente sobre permutações válidas de nós hospitalares, "
    "delegando a avaliação física e a decodificação da frota ao módulo central vrp_core.py."
)

add_code_diagram(
    doc,
    "                      ARQUITETURA DO FLUXO EVOLUCIONÁRIO (GA)\n"
    "   ┌────────────────────────────────────────────────────────────────────────┐\n"
    "   │ 1. Inicialização: População (P=120) com sementes do Vizinho Mais Próx. │\n"
    "   │ 2. Avaliação: Cálculo de Fitness Multicritério para todos os indivíduos│\n"
    "   │ 3. Elitismo: Preservação incondicional dos 2 melhores indivíduos       │\n"
    "   │ 4. Seleção Híbrida: 70% Torneio (k=4) + 30% Roleta Inversa (1/Fitness) │\n"
    "   │ 5. Crossover Ordenado (OX1): Preserva permutações sem nós duplicados   │\n"
    "   │ 6. Mutação Híbrida: 55% 2-opt + 30% Swap + 15% Avanço de UTI Crítica   │\n"
    "   │ 7. Critério de Parada: N gerações ou convergência assintótica          │\n"
    "   └────────────────────────────────────────────────────────────────────────┘"
)

add_heading_2(doc, "2.1. Representação do Cromossomo")
add_body_p(
    doc,
    "Cada cromossomo corresponde a uma permutação bijetiva dos N pontos de entrega, codificada como uma lista de instâncias imutáveis da classe DeliveryPoint:"
)
add_callout(
    doc,
    "Cromossomo = [ P_1, P_2, P_3, ..., P_N ]  (onde cada gene encapsula id, x, y, peso em kg e prioridade clínica)",
    title="Estrutura do Indivíduo Permutacional",
    hex_border=HEX_BLUE_BORDER
)

add_heading_2(doc, "2.2. Inicialização e Semente Heurística")
add_body_p(
    doc,
    "Para acelerar o aquecimento da busca sem induzir perda de diversidade genética, a população inicial combina 98% de indivíduos estocásticos "
    "com 2 sementes geradas pela heurística gulosa de Vizinho Mais Próximo ponderada por urgência clínica (score = dist / prioridade^0.8)."
)

add_heading_2(doc, "2.3. Mecanismo de Elitismo")
add_body_p(
    doc,
    "Em cada geração, os 2 melhores cromossomos identificados são clonados diretamente para a geração subsequente sem sofrer recombinação ou mutação. "
    "Isso assegura monotonicidade: o melhor Fitness histórico jamais se degrada ao longo da evolução."
)

add_heading_2(doc, "2.4. Seleção Híbrida (Torneio vs. Roleta Inversa)")
add_bullet(
    doc,
    "Sorteia aleatoriamente 4 indivíduos da população e elege o de menor Fitness. Garante alta pressão seletiva e rápida convergência em direção às bacias de atração ótimas.",
    bold_prefix="Seleção por Torneio (k=4, 70% das seleções): "
)
add_bullet(
    doc,
    "Como o objetivo é minimizar o custo, calcula-se a probabilidade proporcional a 1 / (Fitness + 1e-6). Isso confere chances de reprodução a indivíduos medianos que carregam blocos construtivos promissores.",
    bold_prefix="Seleção por Roleta Inversa (30% das seleções): "
)

doc.add_page_break()


# ==============================================================================
# PÁGINA 5: CROSSOVER E MUTAÇÃO
# ==============================================================================
add_heading_1(doc, "2. Algoritmo Genético: Crossover e Mutação Híbrida (Cont.)")

add_heading_2(doc, "2.5. Cruzamento Ordenado (Order Crossover — OX1)")
add_body_p(
    doc,
    "Operadores tradicionais de corte geram filhos inválidos em problemas de roteamento (com nós duplicados e outros esquecidos). O "
    "Order Crossover (OX1) soluciona isso preservando a vizinhança contígua de um pai e a ordem relativa do outro."
)

add_code_diagram(
    doc,
    "EXEMPLO DIDÁTICO DO ORDER CROSSOVER (OX1):\n"
    "Pai 1: [ H1,  H2, | H3,  H4,  H5, | H6,  H7,  H8 ]  (Fatia central copiada: H3, H4, H5)\n"
    "Pai 2: [ H8,  H7,   H4,  H1,  H3,   H2,  H6,  H5 ]\n\n"
    "1. O Filho herda diretamente a fatia do Pai 1 nas mesmas posições:\n"
    "   Filho: [ __,  __,   H3,  H4,  H5,   __,  __,  __ ]\n\n"
    "2. Genes faltantes extraídos do Pai 2 na ordem em que aparecem:\n"
    "   Sequência restante: H8, H7, H1, H2, H6\n\n"
    "3. Preenchimento circular das posições vagas:\n"
    "   Filho: [ H8,  H7,   H3,  H4,  H5,   H1,  H2,  H6 ]  -> 100% VÁLIDO E SEM REPETIÇÕES!"
)

add_heading_2(doc, "2.6. Operador de Mutação Híbrida em Três Níveis")
add_body_p(
    doc,
    "Com probabilidade de mutação de 45% (mutation_probability = 0.45), o cromossomo sofre uma dentre três operações especializadas de vizinhança:"
)

table_mut = doc.add_table(rows=4, cols=3)
table_mut.alignment = WD_TABLE_ALIGNMENT.CENTER
table_mut.autofit = False

headers_mut = ["Operador de Mutação", "Frequência", "Mecanismo e Impacto no Roteamento Hospitalar"]
widths_mut = [Inches(1.8), Inches(1.0), Inches(3.87)]

for col_idx, (text, w) in enumerate(zip(headers_mut, widths_mut)):
    cell = table_mut.cell(0, col_idx)
    cell.width = w
    set_cell_background(cell, HEX_PRIMARY)
    set_cell_padding(cell, 100, 100, 120, 120)
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    run.bold = True
    run.font.name = "Segoe UI"
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(255, 255, 255)

data_mut = [
    ("Inversão 2-opt", "55%", "Sorteia dois índices e inverte a ordem de todos os nós intermediários. Elimina instantaneamente cruzamentos geométricos de arestas no plano bidimensional."),
    ("Troca Aleatória (Swap)", "30%", "Permuta duas unidades hospitalares sorteadas arbitrariamente na rota. Permite transferir entregas entre veículos distintos após a decodificação da frota."),
    ("Avanço de Prioridade Crítica", "15%", "Localiza nós de Nível 3 (UTI/Emergência) que estejam em posições tardias da rota e os puxa para posições anteriores, forçando a rápida redução das multas por atraso clínico.")
]

for row_idx, row_data in enumerate(data_mut, start=1):
    for col_idx, (text, w) in enumerate(zip(row_data, widths_mut)):
        cell = table_mut.cell(row_idx, col_idx)
        cell.width = w
        if row_idx % 2 == 0:
            set_cell_background(cell, HEX_BG_LIGHT)
        set_cell_padding(cell, 90, 90, 120, 120)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run(text)
        run.font.name = "Segoe UI"
        run.font.size = Pt(8.5)
        run.font.color.rgb = COLOR_TEXT
        if col_idx == 0:
            run.bold = True

add_body_p(doc, "")

add_callout(
    doc,
    "• mutation_probability (0.45): Frequência com que novos indivíduos sofrem alteração genotípica;\n"
    "• mutation_intensity (1): Quantidade de operações repetidas no mesmo indivíduo (ajuste fino vs. choque);\n"
    "• Distribuição dos ramos (55% / 30% / 15%): Balanceamento ideal entre correção geométrica, exploração e domínio clínico.",
    title="Parâmetros que Controlam a Mutação no Algoritmo Genético",
    hex_border=HEX_PINK_BORDER
)

doc.add_page_break()


# ==============================================================================
# PÁGINA 6: RESTRIÇÕES ADICIONAIS
# ==============================================================================
add_heading_1(doc, "3. Estratégias para Lidar com Restrições Adicionais")

add_body_p(
    doc,
    "Toda a lógica de restrições operacionais da frota foi isolada no módulo vrp_core.py, garantindo total desacoplamento e uniformidade de avaliação."
)

add_heading_2(doc, "3.1. Algoritmo de Decodificação de Frota (split_route_into_vehicles)")
add_body_p(
    doc,
    "A função de particionamento percorre linearmente o cromossomo, atribuindo entregas ao veículo corrente da frota até que "
    "qualquer uma das suas restrições individuais seja atingida:"
)
add_bullet(doc, "Se a carga acumulada somada à nova entrega exceder a capacidade nominal do veículo (Cv);", bold_prefix="Verificação de Carga: ")
add_bullet(doc, "Se o trajeto acumulado acrescido do trecho até a unidade e do retorno ao hospital exceder a autonomia máxima (Av).", bold_prefix="Verificação de Autonomia: ")
add_body_p(
    doc,
    "Quando o limite é atingido, o veículo atual encerra seu itinerário retornando ao hospital, e o próximo veículo assume as "
    "entregas remanescentes. Caso todos os veículos da frota sejam esgotados, as entregas pendentes são alocadas forçosamente ao "
    "último veículo, incorrendo em penalidades severas de sobrecarga e excesso de percurso."
)

add_heading_2(doc, "3.2. Fórmulas Matemáticas das Três Penalidades")

add_callout(
    doc,
    "Para cada veículo e para cada parada k com distância percorrida acumulada (dist_acumulada):\n"
    "• Se Parada Crítica (UTI/Sangue): Multa = (dist_acumulada × 1.2 + (k - 1) × 45.0) × Peso_Prioridade\n"
    "• Se Parada Urgente (Insulina/UPA): Multa = (dist_acumulada × 0.4 + (k - 1) × 15.0) × Peso_Prioridade\n"
    "• Se Parada Regular (Soro/Luvas): Multa = 0\n"
    "Efeito Prático: Obriga os veículos a atenderem as unidades de UTI imediatamente nas primeiras paradas.",
    title="1. Penalidade por Demora de Prioridade Clínica (Peso Padrão: 0.35)",
    hex_border=HEX_ACCENT
)

add_callout(
    doc,
    "Multa = Soma dos quilos excedentes de cada veículo × Peso_Carga\n"
    "Efeito Prático: Cada quilograma excedente adiciona 40 pontos no Fitness, rechaçando rigorosamente qualquer sobrepeso.",
    title="2. Penalidade por Excesso de Carga em kg (Peso Padrão: 40.0)",
    hex_border=HEX_BLUE_BORDER
)

add_callout(
    doc,
    "Multa = Soma da distância excedente de cada veículo × Peso_Autonomia\n"
    "Efeito Prático: Garante que os veículos concluam o ciclo de retorno sem esgotar bateria ou tanque.",
    title="3. Penalidade por Excesso de Autonomia em px/km (Peso Padrão: 15.0)",
    hex_border=HEX_ACCENT
)

doc.add_page_break()


# ==============================================================================
# PÁGINA 7: INTEGRAÇÃO COM LLM
# ==============================================================================
add_heading_1(doc, "4. Integração com LLMs para Instruções e Relatórios")

add_body_p(
    doc,
    "Para transpor os resultados matemáticos da otimização para a rotina diária dos profissionais de saúde, o módulo "
    "llm_driver_assistant.py integra o sistema à API oficial do Google Gemini (Interactions API / SDK google-genai 2.30+)."
)

add_heading_2(doc, "4.1. Grounding e Injeção do JSON da Rota")
add_body_p(
    doc,
    "Ao gerar a solução ótima pelo botão 'Gerar JSON da Solução', os dados consolidados são gravados em melhor_rota_hospitalar.json "
    "e injetados automaticamente nas instruções de sistema (system_instruction) da LLM, eliminando alucinações e garantindo respostas precisas:"
)

add_code_diagram(
    doc,
    "                  FLUXO DE INTEGRAÇÃO COM GOOGLE GEMINI\n"
    "  ┌─────────────────────────────┐         ┌───────────────────────────────┐\n"
    "  │ melhor_rota_hospitalar.json │ ──────► │ System Instruction do Gemini  │\n"
    "  └─────────────────────────────┘         └───────────────┬───────────────┘\n"
    "                                                          │\n"
    "  ┌─────────────────────────────┐                         ▼\n"
    "  │ Pergunta do Motorista /     │ ──────► ┌───────────────────────────────┐\n"
    "  │ Gestor Logístico            │         │ Gemini 3 Flash (Interactions) │\n"
    "  └─────────────────────────────┘         └───────────────┬───────────────┘\n"
    "                                                          │\n"
    "                                                          ▼\n"
    "                                          [ Resposta Estruturada em TNP ]"
)

add_heading_2(doc, "4.2. Casos de Uso Implementados")
add_bullet(
    doc,
    "O condutor seleciona seu veículo no aplicativo (ex.: Veículo 1) e solicita orientações: 'Qual é o meu primeiro destino e que cuidados devo ter com a carga?'. O Gemini responde com a identificação da UTI, distância em km, quilogramas a descarregar e protocolos térmicos para quimioterápicos ou bolsas de sangue.",
    bold_prefix="1. Copiloto Operacional do Motorista: "
)
add_bullet(
    doc,
    "Com um clique, a gestão logística gera relatórios diários ou semanais analisando taxa de ocupação dos veículos, consumo total de autonomia e economia de recursos obtida em comparação a rotas manuais.",
    bold_prefix="2. Relatórios Gerenciais de Eficiência: "
)
add_bullet(
    doc,
    "A LLM identifica padrões na distribuição geográfica e recomenda remanejamento de frotas ou alteração em janelas de expedição farmacêutica.",
    bold_prefix="3. Sugestões Prescritivas de Melhoria: "
)
add_bullet(
    doc,
    "Utilizando o identificador de sessão previous_interaction_id, o motorista pode realizar perguntas encadeadas naturais (ex.: 'E depois dessa entrega, para onde vou?').",
    bold_prefix="4. Memória de Diálogo Multi-Turno: "
)

doc.add_page_break()


# ==============================================================================
# PÁGINA 8: COMPARATIVO DE DESEMPENHO
# ==============================================================================
add_heading_1(doc, "5. Comparativo de Desempenho entre Abordagens de Roteamento")

add_body_p(
    doc,
    "Para certificar a competitividade do Algoritmo Genético, foram implementados outros quatro algoritmos clássicos e modernos "
    "submetidos exatamente ao mesmo motor de restrições em vrp_core.py. O teste foi conduzido no cenário padrão com "
    "14 unidades hospitalares, 215 kg de carga total e 3 veículos disponíveis (capacidade de 85 kg e autonomia de 950 px cada):"
)

table_bench = doc.add_table(rows=6, cols=5)
table_bench.alignment = WD_TABLE_ALIGNMENT.CENTER
table_bench.autofit = False

headers_b = ["Algoritmo", "Paradigma", "Fitness Típico", "Velocidade", "Pontos Fortes e Comportamento"]
widths_b = [Inches(1.4), Inches(1.2), Inches(1.0), Inches(1.0), Inches(2.07)]

for col_idx, (text, w) in enumerate(zip(headers_b, widths_b)):
    cell = table_bench.cell(0, col_idx)
    cell.width = w
    set_cell_background(cell, HEX_PRIMARY)
    set_cell_padding(cell, 100, 100, 100, 100)
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    run.bold = True
    run.font.name = "Segoe UI"
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(255, 255, 255)

data_bench = [
    ("Algoritmo Genético (GA)", "Evolucionário Populacional", "1.960 — 2.040", "Rápida (160 ger.)", "Melhor qualidade global. Descruza rotas e prioriza emergências de UTI no início."),
    ("Ant Colony (ACO)", "Inteligência de Enxame", "1.980 — 2.080", "Moderada (60 it.)", "Excelente aprendizado coletivo via feromônio combinado à visibilidade médica."),
    ("Simulated Annealing (SA)", "Meta-heurística Trajetória", "1.990 — 2.110", "Muito Rápida", "Escapa facilmente de mínimos locais na alta temperatura; converge no resfriamento."),
    ("Nearest Neighbor (NN)", "Heurística Construtiva", "1.970 — 2.060", "Quase Instantânea", "Gera rotas viáveis na 1ª iteração e refina arestas com 2-opt nas gerações posteriores."),
    ("Convex Hull (CH)", "Heurística Geométrica", "2.010 — 2.130", "Rápida", "Gera anéis perimetrais sem laços e insere nós internos com menor custo.")
]

for row_idx, row_data in enumerate(data_bench, start=1):
    for col_idx, (text, w) in enumerate(zip(row_data, widths_b)):
        cell = table_bench.cell(row_idx, col_idx)
        cell.width = w
        if row_idx % 2 == 0:
            set_cell_background(cell, HEX_BG_LIGHT)
        set_cell_padding(cell, 80, 80, 100, 100)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run(text)
        run.font.name = "Segoe UI"
        run.font.size = Pt(8)
        run.font.color.rgb = COLOR_TEXT
        if col_idx == 0:
            run.bold = True

add_body_p(doc, "")

add_heading_2(doc, "Análise Conclusiva do Benchmark")
add_body_p(
    doc,
    "Embora abordagens gulosas como o Vizinho Mais Próximo apresentem velocidade de milissegundos, o Algoritmo Genético "
    "demonstrou a maior capacidade de balanceamento multiobjetivo. A combinação de recombinação genética (OX1) e mutação guiada por prioridade "
    "alcançou consistentemente as menores taxas de atraso em entregas de Nível 3, tornando-o o algoritmo preferencial para a logística médica."
)

doc.add_page_break()


# ==============================================================================
# PÁGINA 9: VISUALIZAÇÕES E ANÁLISES
# ==============================================================================
add_heading_1(doc, "6. Visualizações e Análises das Rotas Otimizadas")

add_body_p(
    doc,
    "O sistema disponibiliza interfaces gráficas tanto na versão desktop (Pygame/Matplotlib) quanto no ecossistema Web completo:"
)

add_heading_2(doc, "6.1. Interface Web com Canvas 2D e Setas Direcionais")
add_bullet(doc, "Vetores desenhados sobre as linhas conectando as unidades, exibindo a sequência exata de saída do hospital, paradas consecutivas e retorno;", bold_prefix="Setas Direcionais de Fluxo: ")
add_bullet(doc, "Cada veículo da frota possui uma cor temática exclusiva (Azul, Laranja, Roxo, etc.);", bold_prefix="Cores Distintas por Veículo: ")
add_bullet(doc, "Círculos vermelhos pulsantes para Nível 3 (UTI), âmbar para Nível 2 (Urgente) e ciano para Nível 1 (Regular);", bold_prefix="Codificação por Prioridade Clínica: ")
add_bullet(doc, "Acompanhamento em tempo real da curva de queda do Fitness ao longo das gerações com eixos graduados;", bold_prefix="Gráfico de Convergência SSE: ")
add_bullet(doc, "Inspeção hovering no Card de Penalidades revelando a exata decomposição das multas de carga, autonomia e prioridade.", bold_prefix="Popover de Multas: ")

# Imagem
if os.path.exists(IMG_PATH):
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(8)
    p_img.paragraph_format.space_after = Pt(2)
    p_img.add_run().add_picture(IMG_PATH, width=Inches(5.8))
    
    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(0)
    p_cap.paragraph_format.space_after = Pt(8)
    r_cap = p_cap.add_run("Figura 1: Visualização gráfica das sub-rotas da frota com retorno ao Depósito Central e gráfico de convergência do Fitness.")
    r_cap.font.name = "Segoe UI"
    r_cap.font.size = Pt(8)
    r_cap.italic = True
    r_cap.font.color.rgb = COLOR_MUTED

add_heading_2(doc, "6.2. Exportação e Interoperabilidade JSON")
add_body_p(
    doc,
    "A melhor rota pode ser baixada instantaneamente no formato melhor_rota_hospitalar.json, contendo resumo de métricas, "
    "quilometragem detalhada e paradas individuais de cada veículo, viabilizando integração direta com sistemas de prontuário e gestão de frotas."
)

doc.add_page_break()


# ==============================================================================
# PÁGINA 10: ARQUITETURA EM NUVEM
# ==============================================================================
add_heading_1(doc, "7. Arquitetura da Solução e Implementação em Nuvem")

add_body_p(
    doc,
    "A aplicação foi estruturada seguindo as diretrizes de sistemas em nuvem de alta disponibilidade (12-Factor App), contando com "
    "conteinerização Docker completa e deploy automatizado em servidor VPS Linux:"
)

add_code_diagram(
    doc,
    "                    DIAGRAMA DE ARQUITETURA EM NUVEM\n"
    "   [ Usuário / Smartphone / Tablet ]\n"
    "                 │ (HTTPS / Porta 443 com Certificado SSL Let's Encrypt)\n"
    "                 ▼\n"
    "   ┌─────────────────────────────────────────────────────────────┐\n"
    "   │ VPS LINUX (HOSTGATOR) — IP: 143.95.175.167                  │\n"
    "   │                                                             │\n"
    "   │  [ Nginx Proxy Reverso ] ── Host: app.143.95.175.167.nip.io │\n"
    "   │            │                                                │\n"
    "   │            ▼ (HTTP Local - 127.0.0.1:5000)                  │\n"
    "   │  ┌───────────────────────────────────────────────────────┐  │\n"
    "   │  │ Container Docker: vrp_hospital_web                    │  │\n"
    "   │  │                                                       │  │\n"
    "   │  │   • Python 3.11-slim + Servidor WSGI Gunicorn         │  │\n"
    "   │  │   • Backend Flask (web_app.py)                        │  │\n"
    "   │  │   • Núcleo VRP (vrp_core.py)                          │  │\n"
    "   │  │   • Volume Persistente: melhor_rota_hospitalar.json   │  │\n"
    "   │  └───────────────────────┬───────────────────────────────┘  │\n"
    "   │                          │ (Chamada Segura com .env)        │\n"
    "   │                          ▼                                  │\n"
    "   │          [ Google Gemini Interactions API ]                 │\n"
    "   │                                                             │\n"
    "   │  [ Portainer Community Edition ] ── Métricas de CPU/RAM     │\n"
    "   └─────────────────────────────────────────────────────────────┘"
)

add_heading_2(doc, "Destaques de Engenharia e Nuvem")
add_bullet(doc, "Múltiplos workers assíncronos configurados para suportar conexões persistentes de streaming SSE sem degradação de performance;", bold_prefix="Gunicorn WSGI de Produção: ")
add_bullet(doc, "Isolamento de dependências com reinicialização automática (restart: unless-stopped) integrada ao systemd do Linux;", bold_prefix="Docker & Docker Compose: ")
add_bullet(doc, "Chave de API do Gemini armazenada com exclusividade em arquivo .env com permissões restritas e excluída do Git;", bold_prefix="Segurança de Segredos: ")
add_bullet(doc, "Painel Portainer CE para acompanhamento contínuo de recursos computacionais e live logs das execuções.", bold_prefix="Observabilidade: ")

doc.add_page_break()


# ==============================================================================
# PÁGINA 11: CONCLUSÃO
# ==============================================================================
add_heading_1(doc, "8. Conclusão e Considerações Finais")

add_body_p(
    doc,
    "O projeto Tech Challenge — Fase 2 atingiu plenamente seus objetivos teóricos e práticos. A transição do problema clássico "
    "do Caixeiro Viajante para um VRP Hospitalar com Restrições Reais de Frota e Prioridades Clínicas demonstrou a versatilidade "
    "dos algoritmos bioinspirados para resolução de problemas NP-difíceis de alta criticidade."
)

add_heading_2(doc, "Síntese dos Principais Resultados")
add_bullet(
    doc,
    "A conjunção de seleção mista (Torneio + Roleta Inversa), Order Crossover (OX1) e Mutação Híbrida em 3 ramos garantiu convergência sólida, descruzando arestas e eliminando integralmente as multas de sobrecarga e atraso de UTI.",
    bold_prefix="1. Robustez do Algoritmo Genético: "
)
add_bullet(
    doc,
    "O desacoplamento das regras de negócio no módulo vrp_core.py viabilizou a comparação rigorosa entre 5 meta-heurísticas sob a mesma métrica de custo.",
    bold_prefix="2. Isonomia Comparativa: "
)
add_bullet(
    doc,
    "A integração da Interactions API do Google Gemini com injeção estruturada do JSON provou que modelos de linguagem de última geração podem atuar como assistentes operacionais confiáveis e precisos, traduzindo cálculos matemáticos complexos em linguagem acessível e prática para motoristas e diretores de logística.",
    bold_prefix="3. IA Generativa como Copiloto Humano: "
)
add_bullet(
    doc,
    "A esteira completa com testes unitários automatizados, conteinerização Docker, proxy Nginx com SSL e interface web responsiva entrega uma solução pronta para o mundo real, estabelecendo bases sólidas para a evolução rumo à Fase 3.",
    bold_prefix="4. Prontidão para Produção: "
)

p_end = doc.add_paragraph()
p_end.paragraph_format.space_before = Pt(30)
p_end.alignment = WD_ALIGN_PARAGRAPH.CENTER

r_date = p_end.add_run("São Paulo, 02 de Novembro de 2026\n")
r_date.bold = True
r_date.font.name = "Segoe UI"
r_date.font.size = Pt(9.5)
r_date.font.color.rgb = COLOR_TEXT

r_sig = p_end.add_run("André Capela • Pós-Tech em Inteligência Artificial para Desenvolvedores — FIAP")
r_sig.font.name = "Segoe UI"
r_sig.font.size = Pt(9)
r_sig.font.color.rgb = COLOR_MUTED

doc.save(DOCX_PATH)
print(f"[SUCESSO] Arquivo DOCX gerado em: {DOCX_PATH}")
