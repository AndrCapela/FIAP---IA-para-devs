# FIAP — Pós-Tech em Inteligência Artificial para Desenvolvedores
## Tech Challenge — Fase 2: Caixeiro Viajante Médico
### Otimização de Rotas para Distribuição de Medicamentos e Insumos Hospitalares

---

**Autor:** André Capela 
**RM**  rm376905
**E-mail:** andr.capela@gmail.com  
**Data:** 02 de Novembro de 2026  
**Instituição:** FIAP
**Curso:** Pós-Tech: IA para DEVs

---

<div style="page-break-after: always;"></div>

# Sumário Executivo e Links do Projeto

Este relatório técnico documenta a concepção, desenvolvimento, validação e implantação da solução para o **Tech Challenge — Fase 2 (Projeto 2: Otimização de Rotas para Distribuição de Medicamentos e Insumos)**. 

A solução aborda o problema do Caixeiro Viajante Médico ampliado para Roteamento de Múltiplos Veículos Heterogêneos (VRP — *Vehicle Routing Problem*), combinando algoritmos bioinspirados de otimização combinatória (com ênfase no **Algoritmo Genético**) e integração com Modelos de Linguagem de Grande Porte (**Google Gemini LLM**) para assistência operacional de motoristas e geração de relatórios gerenciais de eficiência.

### Links Oficiais de Entrega

* **Repositório Git (Código-Fonte Completo e Documentação):**  
  [https://github.com/AndrCapela/FIAP---IA-para-devs/tree/main/Fase%202/7%20-%20Tech%20Challenge/Web%20-%20Completo](https://github.com/AndrCapela/FIAP---IA-para-devs/tree/main/Fase%202/7%20-%20Tech%20Challenge/Web%20-%20Completo)

* **Vídeo Demonstrativo de Apresentação (YouTube):**  
  [https://youtu.be/d2x2oioqB9E](https://youtu.be/d2x2oioqB9E)

* **Demonstração em Nuvem (VPS de Produção com Docker e SSL):**  
  Disponível via Nginx com HTTPS no host configurado na VPS.

---

<div style="page-break-after: always;"></div>

# 1. Introdução e Formulação do Problema

O ambiente de logística hospitalar universitária apresenta desafios operacionais onde a eficiência de transporte transcende a métrica puramente financeira: trata-se de uma questão de salvaguarda de vidas humanas.

No problema clássico do Caixeiro Viajante (TSP — *Travelling Salesperson Problem*), busca-se o circuito fechado de menor custo que visita um conjunto de nós exatamente uma vez. Todavia, a logística de saúde do mundo real impõe severas restrições que tornam o TSP clássico inadequado:

1. **Frota Múltipla Heterogênea:** Um único veículo não comporta a demanda agregada nem possui autonomia física para percorrer todas as unidades. A frota é composta por $V$ veículos com capacidades volumétricas/pesos distintos e limites individuais de alcance (bateria ou combustível).
2. **Prioridades Clínicas Diferenciadas:** Entregas de bolsas de sangue, kits cirúrgicos de intubação e quimioterápicos para UTIs (Nível 3 — Crítico) não podem aguardar no final de uma rota longa. Devem ser atendidas preferencialmente nos primeiros momentos após a saída do hospital.
3. **Ponto Focal de Distribuição (Depósito Central):** Todos os veículos iniciam suas viagens no Hospital Universitário Central (Depósito `#0`), realizam seus itinerários dedicados e devem obrigatoriamente regressar ao Hospital Central para reposição de estoque e esterilização.

O problema foi formalizado como um **Capacitated and Distance-Constrained Vehicle Routing Problem with Medical Priority Delays (CDVRP-MP)**, modelado matematicamente como uma função de minimização multicritério:

$$\min \quad \text{Fitness} = \text{Distância Total} + \text{Penalidade}_{\text{Prioridade}} + \text{Penalidade}_{\text{Carga}} + \text{Penalidade}_{\text{Autonomia}}$$

---

<div style="page-break-after: always;"></div>

# 2. Implementação do Algoritmo Genético para Roteamento

A partir do código base de TSP fornecido, foi realizada uma reengenharia completa para desacoplar o motor evolucionário da regra de negócio hospitalar, permitindo convergência rápida e robusta.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   CICLO DO ALGORITMO GENÉTICO VRP                      │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                     [ 1. População Inicial ]
            (Permutações Aleatórias + Semente Heurística)
                                    │
                                    ▼
                    [ 2. Decodificação e Fitness ]
            (Cálculo em vrp_core.py com as 3 Penalidades)
                                    │
                                    ▼
                       [ 3. Elitismo (Top 2) ]
             (Preservação dos 2 melhores indivíduos intactos)
                                    │
                                    ▼
                       [ 4. Seleção Híbrida ]
       ┌────────────────────────────┴───────────────────────────┐
       ▼ (70% das vezes)                                        ▼ (30% das vezes)
[ Torneio (k=4) ]                                     [ Roleta Inversa 1/Fit ]
       └────────────────────────────┬───────────────────────────┘
                                    │
                                    ▼
                    [ 5. Order Crossover (OX1) ]
       (Copia segmento contínuo do Pai 1 e completa com Pai 2)
                                    │
                                    ▼
                    [ 6. Mutação Híbrida Guiada ]
       ┌────────────────────────────┼───────────────────────────┐
       ▼ (55% Inversão 2-opt)       ▼ (30% Swap)               ▼ (15% Puxada Crítica)
       └────────────────────────────┴───────────────────────────┘
                                    │
                                    ▼
                     [ 7. Nova Geração Formada ]
```

### 2.1. Representação do Cromossomo
O cromossomo é representado por uma permutação de tamanho $N$ de instâncias imutáveis da classe `DeliveryPoint`:
$$\text{Cromossomo} = [P_{\pi(1)}, P_{\pi(2)}, \dots, P_{\pi(N)}]$$
Cada gene encapsula coordenadas $(x, y)$, demanda em quilogramas ($\text{demand\_kg}$), nível de prioridade clínica ($\text{priority} \in \{1, 2, 3\}$), identificação da unidade e descrição dos insumos médicos.

### 2.2. Inicialização da População e Semente Heurística
Para evitar a estagnação precoce em mínimos locais sem sacrificar a velocidade inicial de convergência, a população de tamanho $P$ (padrão $P = 120$) combina:
* Rotas 100% aleatórias para garantir ampla cobertura do espaço de busca;
* Sementes geradas por uma heurística construtiva de Vizinho Mais Próximo ponderada pela prioridade médica ($c = \frac{\text{dist}}{\text{prioridade}^{0.8}}$).

### 2.3. Estratégia Híbrida de Seleção de Pais
Para balancear a exploração (*exploration*) e a intensificação (*exploitation*), a seleção de reprodutores alterna estocasticamente entre duas modalidades:
1. **Seleção por Torneio ($k = 4$, 70% das ocorrências):** Sorteia 4 candidatos da população e elege o de menor Fitness. Proporciona pressão seletiva vigorosa sem sofrer com distorções de escala.
2. **Seleção por Roleta Inversa (30% das ocorrências):** A probabilidade de escolha de um indivíduo $i$ é calculada proporcionalmente ao inverso de seu custo:
   $$P(i) = \frac{\frac{1}{\text{Fitness}(i) + 10^{-6}}}{\sum_{j=1}^{P} \frac{1}{\text{Fitness}(j) + 10^{-6}}}$$
   Isso permite que indivíduos medianos, que portam sub-rotas promissoras, tenham oportunidade de recombinação.

### 2.4. Cruzamento Ordenado (Order Crossover — OX1)
O operador OX1 preserva a viabilidade intrínseca de permutações:
1. Sorteiam-se aleatoriamente dois índices de corte $[i_1, i_2]$ no Pai 1;
2. A subsequência intermediária é copiada diretamente para o filho na mesma posição;
3. As posições restantes são preenchidas iterativamente pelos genes do Pai 2, seguindo a ordem de aparição no Pai 2 e ignorando os nós já incorporados.

### 2.5. Operador de Mutação Híbrida Guiada
Com probabilidade $p_m = 0.45$, o indivíduo sofre perturbação baseada em três ramos complementares:
* **Inversão de Segmento 2-opt (55% de chance):** Inverte uma sequência contígua de entregas, eliminando cruzamentos geométricos de arestas no plano;
* **Troca Aleatória / Swap (30% de chance):** Permuta a posição de duas unidades hospitalares, permitindo que nós mudem de veículo após a decodificação;
* **Avanço de Prioridade Crítica (15% de chance):** Localiza uma entrega de Nível 3 (UTI/Emergência) situada na porção final do itinerário e a transfere para o início da rota, forçando atendimento expedito.

---

<div style="page-break-after: always;"></div>

# 3. Estratégias para Lidar com Restrições Adicionais

Toda a lógica de restrições do domínio hospitalar foi isolada no módulo [`vrp_core.py`](file:///C:/Users/KABUM/Documents/Workspace/FIAP 2.0/FIAP---IA-para-devs/Fase 2/7 - Tech Challenge/Web - Completo/vrp_core.py).

### 3.1. Algoritmo de Decodificação de Frota (`split_route_into_vehicles`)
A partir da sequência cromossômica, o particionamento em múltiplos veículos opera como um empacotamento guloso condicionado:
1. O Veículo 1 parte do Depósito Central ($P_0$) com carga e distância acumuladas zeradas;
2. Antes de incorporar o próximo ponto $P_i$, testa-se preventivamente se a inclusão de $P_i$ viola:
   * A capacidade de peso do veículo ($\text{carga\_atual} + \text{peso}_i > C_v$);
   * A autonomia de viagem considerando o retorno ao depósito ($\text{dist\_atual} + d(P_{\text{ant}}, P_i) + d(P_i, P_0) > A_v$);
3. Se qualquer restrição for violada e ainda existirem veículos disponíveis na frota, o veículo atual encerra seu ciclo retornando a $P_0$, e o próximo veículo ($v+1$) assume com seus próprios limites individuais;
4. **Garantia de 100% de Atendimento:** Caso a frota termine e ainda existam unidades não visitadas, as paradas excedentes são forçosamente atribuídas ao último veículo, aplicando pesadas multas financeiras/virtuais na função objetivo.

```
       [ Depósito Central - Hospital #0 ]
             │                  │
   ┌─────────┴─────────┐        │
   │ Veículo 1         │        │ Veículo 2
   ▼                   ▼        ▼
[ Parada 1 ] ──► [ Parada 2 ] ──► [ Parada 3 ]
   │                               │
   └─────────► Retorno ◄───────────┘
```

### 3.2. Formulação das Penalidades da Função Fitness

#### 1. Penalidade por Atraso de Prioridade Clínica
A penalidade penaliza a distância percorrida e a quantidade de paradas anteriores até o atendimento de unidades graves:
$$\text{Penalidade}_{\text{Prioridade}} = \sum_{v \in \text{Frota}} \sum_{k=1}^{S_v} \Phi(\text{prioridade}_k, \text{dist\_acum}_k, k) \times W_{\text{prio}}$$
Onde:
$$\Phi = \begin{cases} 
(\text{dist\_acum}_k \times 1.2 + (k - 1) \times 45.0), & \text{se Prioridade} = 3 \text{ (Crítico/UTI)} \\
(\text{dist\_acum}_k \times 0.4 + (k - 1) \times 15.0), & \text{se Prioridade} = 2 \text{ (Urgente)} \\
0, & \text{se Prioridade} = 1 \text{ (Regular)}
\end{cases}$$

#### 2. Penalidade por Sobrecarga de Peso
$$\text{Penalidade}_{\text{Carga}} = \sum_{v \in \text{Frota}} \max(0, \text{CargaTotal}_v - C_v) \times W_{\text{carga}}$$
Com peso padrão $W_{\text{carga}} = 40.0$, inviabilizando qualquer solução com veículos sobrecarregados.

#### 3. Penalidade por Excesso de Autonomia
$$\text{Penalidade}_{\text{Autonomia}} = \sum_{v \in \text{Frota}} \max(0, \text{DistânciaTotal}_v - A_v) \times W_{\text{autonomia}}$$
Com peso padrão $W_{\text{autonomia}} = 15.0$, garantindo que os veículos consigam retornar com segurança ao depósito sem esgotamento de combustível ou bateria.

---

<div style="page-break-after: always;"></div>

# 4. Integração com LLMs para Geração de Instruções e Relatórios

A integração com inteligência artificial generativa foi implementada no módulo [`llm_driver_assistant.py`](file:///C:/Users/KABUM/Documents/Workspace/FIAP 2.0/FIAP---IA-para-devs/Fase 2/7 - Tech Challenge/Web - Completo/llm_driver_assistant.py), utilizando o SDK oficial `google-genai` (versão 2.30+) e a **Interactions API** (`client.interactions.create`) conectada ao modelo **Gemini 3 Flash**.

```
┌─────────────────────────────────┐
│ melhor_rota_hospitalar.json     │
│ (Métricas, Veículos e Paradas)  │
└────────────────┬────────────────┘
                 │ (Injeção Contextual via System Instruction)
                 ▼
┌────────────────────────────────────────────────────────┐
│             GOOGLE GEMINI INTERACTIONS API             │
│   (Histórico de Conversação Multi-Turno Preservado)    │
└────────────────────────┬───────────────────────────────┘
                         │
     ┌───────────────────┼───────────────────┐
     ▼                   ▼                   ▼
[ Instruções ao ]   [ Relatórios de ]   [ Sugestões de ]
[   Motorista   ]   [   Eficiência  ]   [   Melhoria   ]
```

### 4.1. Injeção de Contexto Estruturado (Grounding)
Diferente de abordagens genéricas baseadas em texto livre, o sistema injeta integralmente a solução ótima persistida no arquivo `melhor_rota_hospitalar.json` diretamente nas instruções de sistema (`system_instruction`). Isso fornece ao modelo:
* Quilometragem exata percorrida por cada veículo;
* Taxa de ocupação de carga em kg em relação à capacidade nominal;
* Sequência cronológica de paradas com identificação de insumos e graus de criticidade;
* Status de viabilidade matemática (penalidades zeradas).

### 4.2. Três Frentes Operacionais Atendidas:
1. **Copiloto Operacional do Motorista:** Permite ao condutor de ambulância ou van selecionar seu veículo e consultar em linguagem natural seu próximo destino, peso do pacote a ser descarregado e orientações de manuseio térmico/farmacológico (ex.: transporte de quimioterápicos ou bolsas de sangue).
2. **Relatórios Gerenciais Diários e Semanais:** Síntese automatizada para a diretoria logística, consolidando consumo de autonomia, balanceamento de carga entre veículos e tempo estimado de ciclo.
3. **Sugestões de Otimização de Processos:** Análise prescritiva que identifica pontos de gargalo operacional, sugerindo remanejamento de veículos ou alteração nas janelas de expedição do centro de distribuição.
4. **Memória de Diálogo Multi-Turno:** Por meio do parâmetro `previous_interaction_id`, o condutor pode conduzir diálogos contextuais sequenciais sem necessidade de reexplicar o veículo em que se encontra.

---

<div style="page-break-after: always;"></div>

# 5. Comparativo de Desempenho entre Abordagens de Roteamento

Para validar a superioridade e as características do Algoritmo Genético, foram implementados e integrados ao mesmo motor VRP (`vrp_core.py`) outros 4 algoritmos de otimização:

| Algoritmo | Paradigma | Fitness Médio Típico | Tempo / Velocidade | Comportamento e Casos de Uso |
| :--- | :--- | :---: | :---: | :--- |
| **Algoritmo Genético (GA)** | Evolucionário Populacional | **1.960 — 2.040** | Rápida (160 ger.) | **Melhor equilíbrio global.** Otimiza simultaneamente o trajeto físico e a priorização de entregas de UTI no início das rotas. |
| **Ant Colony Optimization (ACO)** | Inteligência de Enxame | **1.980 — 2.080** | Moderada | Excelente aprendizado de conectividade espacial por feromônio, com convergência gradual guiada pela matriz de visibilidade médica. |
| **Simulated Annealing (SA)** | Meta-heurística de Trajetória | **1.990 — 2.110** | Muito Rápida | Capacidade ímpar de escapar de ótimos locais na fase de alta temperatura ($P = e^{-\Delta/T}$); converge bem no resfriamento. |
| **Nearest Neighbor Multi-Start + 2-opt (NN)** | Heurística Construtiva Gulosa | **1.970 — 2.060** | Quase Instantânea | Gera uma rota viável excelente já no primeiro milissegundo e usa 2-opt ao longo das gerações para eliminar cruzamentos. |
| **Convex Hull + Inserção Mais Barata (CH)** | Heurística Geométrica | **2.010 — 2.130** | Rápida | Constrói o anel perimetral externo sem auto-interseções e insere nós internos com menor acréscimo de custo. |

---

<div style="page-break-after: always;"></div>

# 6. Visualizações e Análises das Rotas Otimizadas

O sistema disponibiliza duas camadas complementares de visualização e análise de dados:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CAMADA DE INTERFACE                           │
├──────────────────────────────────┬─────────────────────────────────────┤
│      Ambiente Web Interativo     │       Módulo Desktop / Export       │
│     (HTML5 Canvas 2D + SSE)      │        (Pygame + Matplotlib)        │
├──────────────────────────────────┼─────────────────────────────────────┤
│ • Setas direcionais de fluxo     │ • Gráfico estático (.png)           │
│ • Cores temáticas por veículo    │ • Mapa geográfico Leaflet (.html)   │
│ • Gráfico de convergência real   │ • Exportação estruturada (.json)    │
│ • Popover de multas e métricas   │ • Execução independente de rede     │
└──────────────────────────────────┴─────────────────────────────────────┘
```

1. **Simulador Web Interativo com Canvas 2D:**
   * Renderização com **setas direcionais de fluxo** ao longo dos segmentos, evidenciando o sentido do percurso (saída do Hospital Central, paradas intermediárias e retorno);
   * Diferenciação visual com halos de cor: Vermelho para Nível 3 (UTI/Crítico), Âmbar para Nível 2 (Urgente) e Azul para Nível 1 (Regular);
   * Gráfico dinâmico de convergência com eixos graduados via Chart.js, alimentado por *Server-Sent Events (SSE)* a cada geração do algoritmo;
   * Popover expansível por toque/hover para auditoria analítica da decomposição das 3 penalidades.
2. **Exportação Estruturada em JSON (`melhor_rota_hospitalar.json`):**
   * Persistência do itinerário completo contendo identificação de veículos, lista de paradas com quilometragem parcial, peso embarcado e status de conformidade operacional, viabilizando integração direta com sistemas hospitalares legados (ERP / HIS).

---

<div style="page-break-after: always;"></div>

# 7. Arquitetura da Solução e Implementação em Nuvem

Seguindo as premissas da metodologia *The Twelve-Factor App*, a aplicação foi concebida para execução em contêineres e deploy automatizado em infraestrutura de nuvem:

```
[ Usuário / Navegador / Smartphone ]
                 │ (HTTPS - Porta 443 com Certificado SSL Let's Encrypt)
                 ▼
┌────────────────────────────────────────────────────────────────┐
│                   VPS LINUX (HOSTGATOR)                        │
│                                                                │
│  [ Nginx Proxy Reverso ] ── Host: app.143.95.175.167.nip.io   │
│            │                                                   │
│            ▼ (HTTP Local - 127.0.0.1:5000)                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Container Docker: vrp_hospital_web                       │  │
│  │                                                          │  │
│  │   • Servidor WSGI Gunicorn (2 Workers assíncronos)       │  │
│  │   • Backend Flask (web_app.py)                           │  │
│  │   • Motor de Domínio (vrp_core.py)                       │  │
│  │   • Orquestrador (route_optimizer_dispatcher.py)         │  │
│  │   • Volume Persistente: melhor_rota_hospitalar.json      │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                             │ (Chamada Segura com .env)        │
│                             ▼                                  │
│             [ Google Gemini Interactions API ]                 │
│                                                                │
│  [ Portainer Community Edition ] ── Monitoramento e Métricas   │
└────────────────────────────────────────────────────────────────┘
```

### Componentes de Infraestrutura:
* **Dockerfile & Docker Compose:** Imagem minimalista baseada em `python:3.11-slim` com flags de otimização de bytecode e buffer desativado, orquestrada via `docker-compose.yml` com política de reinicialização automática (`restart: unless-stopped`) e verificação nativa de integridade (*healthcheck*);
* **Servidor de Produção WSGI:** Execução por meio de **Gunicorn** com múltiplos workers assíncronos, garantindo alta vazão e tolerância a conexões persistentes de longa duração para o streaming de SSE;
* **Segurança e Proxy Reverso Nginx:** Tráfego criptografado de ponta a ponta via certificados SSL gratuitos e renováveis da Let's Encrypt sobre domínio DNS wildcard (`nip.io`);
* **Isolamento de Credenciais:** As chaves de acesso à API do Google Gemini residem exclusivamente no arquivo `.env` do servidor, protegido por permissões restritas e excluído do controle de versão pelo `.gitignore`;
* **Observabilidade com Portainer CE:** Painel de controle dedicado com métricas contínuas de CPU/RAM, inspeção de logs ao vivo e gestão de ciclo de vida do contêiner.

---

<div style="page-break-after: always;"></div>

# 8. Conclusão

O desenvolvimento deste Tech Challenge permitiu demonstrar na prática que o problema do Caixeiro Viajante Médico em ambientes hospitalares transcende a simples busca de menor distância euclidiana. A modelagem precisa incorporar as restrições humanas, clínicas e físicas que governam a rotina de um hospital universitário.

A dissociação arquitetural entre as regras de negócio em `vrp_core.py` e os motores de busca permitiu comparar de forma isonômica 5 abordagens clássicas e modernas de otimização. Dentre elas, o **Algoritmo Genético** destacou-se pela robustez do cruzamento ordenado (OX1) e pela eficácia da mutação híbrida guiada pelo domínio, entregando rotas eficientes e com total respeito às prioridades de UTI e emergência.

Por fim, a união da otimização evolucionária clássica com Modelos de Linguagem de Grande Porte (**Google Gemini**) estabeleceu uma ponte entre o rigor da matemática aplicada e a usabilidade humana na ponta da operação: transformou tabelas complexas de coordenadas em orientações operacionais claras e acessíveis para motoristas e em inteligência de negócios para a gestão hospitalar.

---

**São Paulo, 02 de Novembro de 2026**  
**André Capela**  
*Pós-Tech em IA para DEVs — FIAP*
