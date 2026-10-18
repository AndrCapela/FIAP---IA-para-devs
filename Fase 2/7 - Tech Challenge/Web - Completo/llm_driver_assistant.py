# -*- coding: utf-8 -*-
"""
Etapa 4: Copiloto e Assistente de Rotas para Motoristas com Google Gemini (`llm_driver_assistant.py`)
Tech Challenge - Fase 2 (Projeto 2: Otimização de Rotas para Distribuição de Medicamentos e Insumos)

Como funciona este módulo:
1. Carrega o JSON estruturado da solução (`melhor_rota_hospitalar.json` ou a última solução em memória);
2. Constrói uma instrução de sistema (`system_instruction`) especializada para logística hospitalar,
   contendo todos os detalhes das rotas, paradas sequenciais, prioridades médicas (Crítico/UTI,
   Urgente/Refrigerado, Regular), pesos em kg e limites de cada veículo;
3. Conecta-se à API oficial do Google Gemini usando o SDK `google-genai` (`client.interactions.create`)
   com o modelo `gemini-3.8-flash` e suporte a conversas multi-turno (`previous_interaction_id`),
   permitindo que cada motorista pergunte qual é o seu próximo destino, quais insumos separar,
   cuidados de transporte ou peça um roteiro passo a passo.
"""

import os
import json
from typing import Dict, Any, Optional
from google import genai

# Carrega variáveis de ambiente do arquivo .env (caso exista)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _load_env_fallback():
    """Carregador simples de .env para quando python-dotenv não estiver instalado."""
    for base_dir in [os.path.dirname(os.path.abspath(__file__)), os.getcwd()]:
        env_path = os.path.join(base_dir, ".env")
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip('"').strip("'")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass
            break

_load_env_fallback()

DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"
FALLBACK_GEMINI_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.8-flash",
    "gemma-4-31b-it"
]


def build_driver_system_instruction(
    route_json_data: Dict[str, Any],
    selected_vehicle_id: Optional[int] = None
) -> str:
    """
    Monta o `system_instruction` com os dados completos do JSON de rotas otimizadas
    e foca no veículo do motorista selecionado (se informado).
    """
    json_str = json.dumps(route_json_data, ensure_ascii=False, indent=2)

    vehicle_focus_text = (
        f"O usuário atual no chat é o MOTORISTA DO VEÍCULO {selected_vehicle_id}. "
        f"Priorize responder especificamente sobre a rota, paradas sequenciais, cargas (kg) e "
        f"cuidados médicos do Veículo {selected_vehicle_id}, a menos que ele pergunte sobre outro veículo."
        if selected_vehicle_id
        else "O usuário atual é o Coordenador de Logística / Motorista consultando toda a frota."
    )

    return f"""Você é o Copiloto Inteligente de Logística Hospitalar do Hospital Universitário Central.
Sua função é orientar os motoristas da frota de distribuição de medicamentos e insumos médicos e também gerar
relatórios gerenciais de eficiência logística de forma clara, direta, segura e amigável.

REGRAS DE CONDUTA:
1. Responda SEMPRE em Português do Brasil, utilizando formatação Markdown limpa (listas, negrito para nomes de hospitais, pesos e prioridades).
2. Baseie-se ESTRITAMENTE nos dados do JSON da rota otimizada fornecido abaixo. Nunca invente paradas ou pesos que não estejam no JSON.
3. Quando o motorista perguntar "qual é o meu próximo destino" ou pedir instruções de rota:
   - Indique claramente a ordem da parada (1º, 2º, 3º...), o nome da Unidade/Paciente, o peso a descarregar (em kg), o nível de prioridade (Crítico, Urgente ou Regular) e a descrição do medicamento/insumo.
   - Se o item for Crítico (UTI/Emergência) ou Urgente (ex.: Insulina Refrigerada, Quimioterápicos, Cilindro de O2, Hemoderivados), adicione uma recomendação curta e prática de manuseio/segurança (ex.: manter cadeia de frio, entrega prioritária no balcão da UTI, etc.).
4. Se o motorista informar que já concluiu determinada parada (ex.: "já entreguei na parada 1"), identifique na sequência do veículo qual é a parada seguinte (parada 2) ou se ele deve retornar ao Hospital Universitário Central (Depósito #0).
5. Quando solicitado um RELATÓRIO DIÁRIO/SEMANAL DE EFICIÊNCIA ou SUGESTÕES DE MELHORIA NO PROCESSO:
   - Analise a taxa de ocupação de carga (kg usados vs. limite de cada veículo), o uso da autonomia (distância percorrida vs. limite em px), a viabilidade da rota (`is_feasible`) e o posicionamento das entregas Críticas/Urgentes;
   - Apresente estimativas de economia de tempo/combustível e sugira melhorias práticas no processo (ex.: redistribuição de carga entre veículos, ajuste de janelas de saída, uso de veículos refrigerados dedicados ou ajuste de capacidades).

CONTEXTO DO MOTORISTA ATUAL:
{vehicle_focus_text}

DADOS OFICIAIS DO ARQUIVO JSON DE ROTA (`melhor_rota_hospitalar.json`):
```json
{json_str}
```
"""


def ask_driver_assistant(
    user_message: str,
    route_json_data: Dict[str, Any],
    selected_vehicle_id: Optional[int] = None,
    previous_interaction_id: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_GEMINI_MODEL
) -> Dict[str, Any]:
    """
    Envia a pergunta do motorista (junto com a instrução de sistema contendo o JSON da rota)
    para o Google Gemini usando a Interactions API (`client.interactions.create`).

    Nota importante da Interactions API:
    - `system_instruction` tem escopo por interação, por isso é reenviado a cada turno;
    - `previous_interaction_id` mantém a memória da conversa no servidor para que o motorista
      possa fazer perguntas de acompanhamento ("e depois dessa parada, para onde vou?").
    """
    resolved_key = (api_key or os.environ.get("GEMINI_API_KEY") or "").strip()
    if not resolved_key:
        raise ValueError(
            "Chave da API do Gemini não informada. Configure a variável GEMINI_API_KEY no arquivo .env, "
            "como variável de ambiente ou informe sua chave no campo 'Gemini API Key' na interface Web."
        )

    client = genai.Client(api_key=resolved_key)
    system_instruction = build_driver_system_instruction(
        route_json_data=route_json_data,
        selected_vehicle_id=selected_vehicle_id
    )

    models_to_try = [model_name] + [m for m in FALLBACK_GEMINI_MODELS if m != model_name]
    last_error = None

    for candidate_model in models_to_try:
        try:
            create_kwargs: Dict[str, Any] = {
                "model": candidate_model,
                "system_instruction": system_instruction,
                "input": user_message,
            }
            if previous_interaction_id:
                create_kwargs["previous_interaction_id"] = previous_interaction_id

            interaction = client.interactions.create(**create_kwargs)

            return {
                "reply": interaction.output_text or "Sem resposta gerada pelo modelo.",
                "interaction_id": interaction.id,
                "model": candidate_model
            }
        except Exception as exc:
            last_error = exc
            # Se falhar por previous_interaction_id expirado/inválido, tenta sem previous_interaction_id
            if previous_interaction_id:
                try:
                    interaction = client.interactions.create(
                        model=candidate_model,
                        system_instruction=system_instruction,
                        input=user_message
                    )
                    return {
                        "reply": interaction.output_text or "Sem resposta gerada pelo modelo.",
                        "interaction_id": interaction.id,
                        "model": candidate_model
                    }
                except Exception as inner_exc:
                    last_error = inner_exc
            continue

    raise RuntimeError(str(last_error))
