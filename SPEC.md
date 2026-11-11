# SPEC — Treino em linguagem natural (agente de IA + avaliação)

Prazo: código pronto até sáb 14/11/2026. Inscrição do iFood GEN AI (AI Engineer) até ter 17/11/2026.
Regras fixas de trabalho ficam no `CLAUDE.md`. Este arquivo é a referência: leia só a seção de que precisar.

## 1. Objetivo e critério de sucesso

O usuário escreve em português livre ("supino 4x8 com 80, última até a falha; remada 3x10 com 60"). O sistema:
1. extrai os dados estruturados (exercício, séries, carga, repetições, marcadores) e salva;
2. consulta o histórico;
3. sugere a progressão da próxima sessão por regra determinística.

Entregáveis: repositório público, avaliação reproduzível com tabela de resultados, dataset no Hugging Face, artigo curto.

**Sucesso = um comando roda a avaliação, compara pelo menos 3 configurações e o README mostra a tabela, a análise de erros e as limitações.**

## 2. Fora do escopo (não fazer)

App mobile, login, multiusuário, WhatsApp, reconhecimento de voz próprio (Whisper ou similar), fine-tuning, wearables, dados da loja, qualquer coisa fora desta spec sem perguntar antes.

## 3. Prioridades

- **P0 (obrigatório):** extração estruturada PT-BR, persistência (SQLite), normalização de exercícios, regra de progressão, dataset + harness de avaliação + relatório.
- **P1:** agente com 3 ferramentas (tool calling) e API FastAPI.
- **P2:** página HTML mínima com campo de texto e botão de microfone, `GET /export.csv`, Docker e polimento do README.
  - Voz: Web Speech API do navegador (`lang = "pt-BR"`). O texto transcrito vai para o mesmo `POST /chat`. Funciona no Chrome/Chromium; o Firefox não suporta. A voz é só uma camada de entrada: a avaliação continua sobre texto.
  - Exportação: `GET /export.csv` devolve o histórico para abrir em planilha.
  - Se sobrar tempo, medir o efeito da voz: 10 mensagens digitadas contra as mesmas ditas e transcritas (`tags: ["voz"]`), reportadas à parte.
- **Corte:** se na sexta 13/11 às 18h o P0 não estiver rodando, congelar o P1 e entregar só o P0 mais a CLI.

## 4. Arquitetura

```
app/
  main.py            # FastAPI: POST /chat, GET /history/{exercise}  (P1)
  schemas.py         # Pydantic v2: SetEntry, ExerciseEntry, ExtractionResult
  models.py, db.py   # SQLModel + SQLite
  exercises.py       # lista canônica, aliases, normalização aproximada
  progression.py     # dupla progressão (código puro)
  extract.py         # prompt + chamada ao LLM + validação (1 retry)
  llm/base.py        # interface LLMClient
  llm/ollama_client.py
  llm/gemini_client.py
  agent.py           # P1: laço com 3 ferramentas
eval/
  data/dataset.jsonl
  data/progression_sim.csv   # histórico simulado (marcado como simulado)
  configs/*.yaml     # uma por configuração comparada
  validate.py        # valida o dataset contra o schema
  run.py             # roda uma ou todas as configurações
  report.py          # gera a tabela em markdown a partir de results/
results/
tests/
```

### Contratos de dados

- `SetEntry`: `weight_kg: float | None` (None = peso corporal), `reps: int`, `flag: "failure" | "dropset" | "warmup" | None`.
- `ExerciseEntry`: `exercise_raw: str` (como o modelo leu), `sets: list[SetEntry]`.
- `ExtractionResult`: `entries: list[ExerciseEntry]`, `needs_confirmation: bool`.
- O modelo extrai `exercise_raw`. O código normaliza para o nome canônico via `exercises.py`. Exercício desconhecido: `needs_confirmation = true`, nunca inventar.
- Cada série vira um item em `sets` ("4x8 com 80" = 4 itens).

Lista canônica (30 exercícios reais, em `data/exercises.json` com `slug`, `nome`, `grupo` e `aliases`; `exercises.py` carrega esse arquivo): `supino_reto_barra`, `supino_inclinado_halteres`, `crucifixo_maquina`, `triceps_maquina`, `triceps_unilateral_polia`, `triceps_frances_polia`, `elevacao_lateral_halteres`, `desenvolvimento_maquina`, `puxada_alta_polia`, `remada_serrote`, `crucifixo_inverso_maquina`, `face_pull`, `flexao_punho`, `rosca_inversa`, `rosca_martelo`, `biceps_maquina_alternado`, `lombar_maquina`, `leg_press_inclinado`, `panturrilha_leg_press`, `stiff_barra`, `cadeira_adutora`, `mesa_flexora`, `cadeira_abdutora`, `cadeira_extensora`, `cadeira_abdominal`, `supino_inclinado_maquina`, `elevacao_lateral_polia`, `triceps_corda`, `pull_down_polia`, `biceps_polia`.

### Provedores de LLM

Interface única: `LLMClient.extract(text, schema) -> dict`, com `temperature = 0`.

- **Ollama (local):** modelo `qwen3:8b`, 8 GB de VRAM (RTX 5050). Usar o pacote `ollama` para Python, `think=False` (o modelo pensa por padrão e isso custa latência; se a versão instalada não aceitar `think`, anexar `/no_think` à mensagem), `format` com JSON Schema (saída estruturada) e `options={"num_ctx": 4096}`. Se o prompt com few-shot não couber, testar 8192 e conferir com `ollama ps` que continua em 100% GPU; se sair da GPU, voltar para 4096 e encurtar o prompt.
- **Gemini (API):** SDK oficial `google-genai`, chave em `GEMINI_API_KEY` (arquivo `.env`, nunca no git). O nome do modelo vem de `GEMINI_MODEL`: listar os modelos disponíveis para a chave e escolher um Flash. Saída em JSON com schema. Respeitar limites da faixa gratuita: pausa entre chamadas e retry com backoff em erro 429.
- Em qualquer dúvida sobre API ou nome de modelo, consultar a documentação oficial atual em vez de usar memória.

## 5. Regra de progressão (`progression.py`, código puro, com testes)

Dupla progressão por exercício, com faixa de repetições configurável (padrão 8–12) e passo de carga configurável (padrão 2,5 kg):
- Todas as séries de trabalho (sem `warmup`) atingiram o topo da faixa: subir a carga em um passo e voltar ao piso da faixa.
- Caso contrário: manter a carga e mirar +1 repetição na série mais fraca.
- N sessões seguidas sem progresso (padrão N = 3): apenas sinalizar "estagnado há N sessões".
- O modelo só redige a mensagem final a partir do retorno desta função. Todo número mostrado vem dela.
- Sessões `com_personal` (menos exercícios, ajuda nas últimas repetições) não contam para "estagnado".
- Dizer no README que a sugestão é heurística, não recomendação profissional.

## 6. Dados e avaliação

Arquivo `eval/data/dataset.jsonl`, um exemplo por linha:

```json
{"id": "r001", "text": "supino 4x8 com 80, última até a falha; remada 3x10 com 60",
 "expected": {"entries": [
   {"exercise": "supino_reto", "sets": [
     {"weight_kg": 80, "reps": 8, "flag": null}, {"weight_kg": 80, "reps": 8, "flag": null},
     {"weight_kg": 80, "reps": 8, "flag": null}, {"weight_kg": 80, "reps": 8, "flag": "failure"}]},
   {"exercise": "remada_curvada", "sets": [
     {"weight_kg": 60, "reps": 10, "flag": null}, {"weight_kg": 60, "reps": 10, "flag": null},
     {"weight_kg": 60, "reps": 10, "flag": null}]}]},
 "source": "real", "tags": ["nxm", "falha", "multi"]}
```

`source` é obrigatório e vale `real` (escrito por você, do jeito que você escreve), `reconstruido` (treino que você lembra com segurança) ou `sintetico` (gerado pelo Gemini e revisado por você). **Nunca rotular sintético como real.** As métricas saem separadas por fonte.

Convenções de rotulagem (valem para todo o dataset):
- `expected.entries[].exercise` é o slug canônico (ou `null` se o exercício não está na lista; aí `needs_confirmation = true`). A avaliação compara depois da normalização.
- "Até a falha" sem "todas as séries" marca `failure` só na última série do exercício. "Todas as séries até a falha" marca todas.
- Drop com carga dita ("drop pra 20 por 8"): série extra com `flag = "dropset"`. Drop sem carga ("meti um dropset na última"): `flag = "dropset"` na última série.
- Aquecimento dito: séries com `flag = "warmup"`, fora da regra de progressão.
- "Cada" em halteres é a carga de um halter. Mensagem sem dados de série: `entries = []` e `needs_confirmation = true`.
- Repetições feitas com ajuda do personal não contam: vale o número "sem ajuda". Cada exemplo pode ter `context.com_personal`; a sessão no banco guarda `com_personal` (bool).
- Número aproximado ("uns 20 e poucos, acho que 22") vale o número dito (tag `aproximado`). "Cada lado" fica com a carga dita, sem multiplicar (tag `por_lado`).
- Sem número de séries no texto, vale 3 (padrão da autora; configurável).
- Supino reto com barra: ela fala só as anilhas de um lado ("7,5 de sempre"). O extrator devolve o valor falado; a normalização em código calcula `weight_kg = barra_kg + 2 × falado` com `barra_kg = 20` (campos `barra_kg` e `carga_modo = "anilhas_por_lado"` em `exercises.json`). O esperado do dataset já está no total (7,5 falado → 35 kg). "Só a barra" = 20 kg. O prompt do extrator recebe essa regra por exercício, vinda do `exercises.json`.
- Nos outros exercícios o valor falado é a carga como dita ("cada lado" nas máquinas não é multiplicado).
- Autocorreção ("na verdade foi 140") vale o valor final.

Meta: cerca de 60 exemplos (≈20 reais, ≈15 reconstruídos, ≈25 sintéticos). Se a última série "até a falha" não tem repetições ditas, decidir uma regra única de rotulagem e aplicar em todo o dataset.

O histórico simulado fica em `data/progression_sim.csv` (colunas `date,exercise,set_number,weight_kg,reps,flag,source,com_personal`; 663 linhas, 39 sessões de 28/09 a 11/11/2026, `source = sintetico`). Foi reconstruído de trás para frente a partir das cargas reais da semana de 09 a 11/11, com dupla progressão 8–12, em ciclo push → pernas → costas de segunda a sábado; as 3 últimas sessões estão marcadas `com_personal = true`. É histórico simulado e o README precisa dizer isso. Só o que a autora confirmar que lembra pode virar `reconstruido`. O CSV original do Gemini (sessões de 01/09 a 08/10) foi descartado porque as cargas não eram as dela.

Exemplos sintéticos com rótulo exato: gerar a partir das linhas estruturadas do CSV (estruturado para texto). O LLM escreve a mensagem como uma pessoa diria e o esperado já está correto por construção. Esses exemplos são `sintetico`. Os `real` são mensagens que você mesma escreve ou fala, rotuladas à mão.

Casos difíceis (use como tags): "12 10 8 com 60/70/80", "4x8 com 80", "3 séries de 10 com 27,5", "quilos" e "kg", "até a falha", "bi-set", "drop", peso corporal sem carga, vários exercícios na mesma mensagem, exercício ambíguo ou desconhecido, correção ("na verdade foi 75").

Métricas (comparação após normalização; carga com tolerância de 0,01):
- validade do JSON e do schema;
- acerto do exercício;
- acerto por série (carga e repetições);
- acerto exato da mensagem inteira;
- latência mediana;
- tokens e custo, quando aplicável.

Configurações a comparar (uma por arquivo em `eval/configs/`):
- A: Qwen3 8B local, zero-shot.
- B: Gemini Flash, zero-shot.
- C: a melhor das duas com few-shot e schema estrito.
- Opcional: Llama 3.1 8B local.

Rodar a avaliação completa no máximo 3 vezes (v1, v2, final). Salvar em `results/*.json`. Escrever pelo menos 5 erros reais com análise. A progressão é validada por testes unitários e pelo histórico simulado; com poucos dados reais não se afirma "evolução" medida.

## 7. Divisão de trabalho entre modelos

| Tarefa | Quem |
|---|---|
| Desenho do agente, `progression.py` + testes, revisão final | Claude Code (Sonnet, esforço baixo) |
| Boilerplate (Dockerfile, `.gitignore`, HTML da página), rascunho de README, dataset card, polimento do artigo | Gemini (assinatura AI Pro, no chat) |
| Exemplos sintéticos do dataset | Gemini, com revisão sua |
| Extração dentro do app (baselines) | Qwen3 8B local e API do Gemini (chave do AI Studio) |

Um agente principal. Sem enxame de agentes e sem plugins ou skills de terceiros nesta semana.

## 8. Cronograma

- **Qua 11 (noite):** estrutura do repositório, schemas, modelos de banco, testes iniciais. Dataset: começar a anotar os treinos reais.
- **Qui 12:** `exercises.py` e `progression.py` com testes; clientes LLM (Ollama e Gemini) e `extract.py` com teste de fumaça; revisar os sintéticos do Gemini.
- **Sex 13:** harness de avaliação, 3 configurações, 1ª tabela, ajuste de prompt (few-shot), 2ª rodada; P1 só se o P0 estiver verde. **Corte às 18h.**
- **Sáb 14:** README com resultados e limitações, dataset no Hugging Face, artigo curto. Congelar o código.
- **Dom 15 a ter 17:** currículo, inscrição (enviar na segunda 16), preparação para o desafio técnico e para a conversa. Terça só contingência.

## 9. Definição de pronto

- [ ] `pytest` verde (schemas, normalização, progressão, validação do dataset)
- [ ] `python -m eval.validate` passa no dataset
- [ ] `python -m eval.run --config all` e `python -m eval.report` geram a tabela
- [ ] README: o que é, como rodar, tabela de resultados, análise de erros, limitações (dataset pequeno, N por fonte, parte sintética), próximos passos
- [ ] Dataset no Hugging Face com dataset card (fontes, licença, anonimização)
- [ ] Artigo curto (600 a 900 palavras) sobre o que a avaliação mostrou
- [ ] Repositório público sem chaves (`.env.example`) e com licença MIT
- [ ] (P2) `docker compose up` sobe a API

## 10. Como contar na conversa (4 frases)

1. O problema: treino 6x por semana e não registrava.
2. A decisão: extração estruturada avaliada de forma sistemática e a regra de progressão em código, não no modelo.
3. O resultado: a tabela com as configurações e o que cada uma errou.
4. A limitação: dataset pequeno, parte sintética, e o que faria com mais tempo.
