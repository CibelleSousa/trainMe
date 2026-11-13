---
language: pt
license: cc-by-4.0
task_categories:
- text-generation
- token-classification
tags:
- portuguese
- information-extraction
- fitness
- llm-evaluation
size_categories:
- n<1K
---

# Treino em linguagem natural (PT-BR) — extração estruturada

Dataset de relatos em português livre sobre treino de musculação
("supino 4x8 com 80, última até a falha"), anotado com os dados
estruturados esperados (exercício, séries, carga, repetições,
marcadores). Criado como parte de um projeto de portfólio para avaliar
a extração estruturada de texto livre por LLM.

- Repositório (código, agente, avaliação): https://github.com/CibelleSousa/trainMe
- Licença do dataset: **CC-BY-4.0**. Licença do código do repositório: MIT.

## Estrutura dos dados

### `dataset.jsonl` (52 linhas, uma por exemplo)

| Campo | Tipo | Exemplo real |
|---|---|---|
| `id` | `string` | `"r001"` |
| `text` | `string` | `"Segunda-feira eu fiz o supino reto, eu fiz com 7,5 kg de sempre, fiz 12 repetições, eu acho..."` |
| `expected.entries` | `list[object]` | ver abaixo |
| `expected.entries[].exercise` | `string \| null` | `"supino_reto_barra"` (slug de `exercises.json`); `null` quando o exercício não é reconhecido |
| `expected.entries[].sets` | `list[object]` | ver abaixo |
| `expected.entries[].sets[].weight_kg` | `float \| null` | `35.0` (`null` = peso corporal) |
| `expected.entries[].sets[].reps` | `int` | `10` |
| `expected.entries[].sets[].flag` | `"failure" \| "dropset" \| "warmup" \| null` | `null` |
| `expected.entries[].sets[].rir` | `int \| null` (opcional, só quando a frase menciona) | `2` |
| `expected.needs_confirmation` | `bool` | `false` |
| `source` | `"real" \| "sintetico"` | `"real"` |
| `tags` | `list[string]` | `["multi", "voz", "correcao", ...]` |
| `context` | `object` (opcional, chaves variam) | `{"com_personal": true}`, `{"date": "2026-06-07"}`, `{"dates": [...]}` ou `{"nota": "..."}` |

Exemplo real de uma linha (resumida):

```json
{"id": "r006", "text": "Opa, anota aí supino reto 1 com 7,5 e fiz 10 e 2 de 8kg com 8 reps deixei 2 na reserva em ambas.",
 "expected": {"entries": [{"exercise": "supino_reto_barra", "sets": [
   {"weight_kg": 35.0, "reps": 10, "flag": null, "rir": 2},
   {"weight_kg": 36.0, "reps": 8, "flag": null, "rir": 2},
   {"weight_kg": 36.0, "reps": 8, "flag": null, "rir": 2}]}], "needs_confirmation": false},
 "source": "real", "tags": ["voz", "rir", "enchimento", "series_agrupadas", "anilha_por_lado_implicita"]}
```

### `exercises.json` (37 exercícios)

Lista canônica usada para normalizar `exercise_raw` → `exercise` (slug).
Cada item: `slug`, `nome`, `grupo` (grupo muscular), `aliases` (lista de
jeitos de falar o exercício) e, só para quem usa anilha por lado,
`barra_kg` e `carga_modo` (`"anilhas_por_lado"` ou `"por_lado_se_dito"`).

```json
{"slug": "supino_reto_barra", "nome": "Supino Reto com Barra", "grupo": "peito",
 "aliases": ["supino reto", "supino reto barra", "supino com barra", "supino"],
 "barra_kg": 20, "carga_modo": "anilhas_por_lado"}
```

## Distribuição

52 exemplos: **6 `real`** (ditados/escritos pela autora) e **46
`sintetico`** (gerados a partir do histórico estruturado). Nenhum
exemplo é `reconstruido`.

`needs_confirmation = true` em 2 exemplos (exercício não reconhecido,
ex.: "Rosca scott" não está na lista canônica).

Tags mais frequentes (um exemplo pode ter várias):

| Tag | n | O que marca |
|---|---|---|
| `multi` | 39 | vários exercícios na mesma mensagem |
| `nxm` | 30 | formato "N x M" (séries x repetições) |
| `abreviacao` | 18 | nome do exercício abreviado |
| `anilha_por_lado` | 7 | carga falada é só a anilha de um lado |
| `voz` | 6 | mensagem ditada, não digitada |
| `falha` | 6 | menção a "até a falha" |
| `decimal` | 4 | carga com vírgula decimal |

As outras ~30 tags (`correcao`, `dropset`, `warmup`, `rir`, `ambiguo`,
`series_agrupadas`, `formato_anotacao`, `erro_digitacao`,
`exercicio_desconhecido`, `sem_dados`, entre outras) aparecem em 1 a 3
exemplos — cobrem casos difíceis específicos, não frequência real.

## Convenções de anotação

Resumo das regras completas em `SPEC.md` do repositório:

- `exercise` é sempre o slug canônico de `exercises.json`, nunca
  inventado; exercício fora da lista vira `null` com
  `needs_confirmation = true`.
- Carga por lado: no supino reto com barra, o valor falado é só a
  anilha de um lado — o total já anotado é `barra_kg + 2 × falado`
  (`carga_modo = "anilhas_por_lado"`). Em máquinas, "cada lado" só conta
  em dobro quando a pessoa diz isso explicitamente
  (`carga_modo = "por_lado_se_dito"`).
- "Até a falha" sem "todas": `flag = "failure"` só na última série do
  exercício. "Todas até a falha": todas as séries de trabalho.
- Aquecimento dito: `flag = "warmup"` (fora da progressão).
- Drop com carga dita: série extra com `flag = "dropset"`. Drop sem
  carga: a própria última série marcada `dropset`.
- Autocorreção ("na verdade foi 140"): vale o valor final dito.
- Repetição com ajuda do personal não conta: vale o número sem ajuda;
  a sessão guarda `context.com_personal = true`.
- RIR ("deixei 2 na reserva"): campo `rir` nas séries a que a frase se
  refere; sem menção, o campo não aparece.
- Sem número de séries dito: vale 3 (padrão da autora).
- "Cada" em halteres é a carga de um halter, não multiplica.

## Como foi criado

- **6 exemplos `real`**: frases que a autora realmente disse ou
  escreveu sobre o próprio treino, rotuladas à mão.
- **46 exemplos `sintetico`**: gerados a partir de linhas estruturadas
  de um histórico de treino simulado (estruturado → texto, por um LLM),
  revisados pela autora. O rótulo esperado já é conhecido por
  construção. Como o texto foi escrito por um LLM, ele tende a favorecer
  o estilo de frase que o próprio tipo de modelo avaliado sabe gerar —
  um viés real de avaliação, não só uma questão de tamanho de amostra.

## Usos pretendidos

- Avaliar/comparar modelos (incluindo configurações zero-shot vs.
  few-shot, local vs. via API) na extração estruturada de relatos de
  treino em português.
- Pesquisa e ensino sobre extração estruturada de texto livre e
  avaliação de LLM.

## Usos não pretendidos

- **Não é recomendação de treino nem orientação profissional.**
- Não representa uma população diversa: é o jeito de falar de **uma
  única pessoa**.
- Não é um dataset validado de progressão real de carga — o histórico
  de referência usado pra gerar os sintéticos é simulado.
- Não serve para treinar um modelo de reconhecimento de voz (não tem
  áudio, só texto).

## Limitações

- **n=52 é pequeno**, e só 6 são `real` — pouco pra generalizar.
- Uma única pessoa, um único jeito de falar; só português do Brasil.
- Lista fechada de 37 exercícios; qualquer outro vira
  `needs_confirmation`.
- Os 46 exemplos `sintetico` têm viés de estilo (ver "Como foi
  criado").
- Ambiguidade real não resolvível só pelo texto: no exemplo `r002`, a
  autora diz "cadeira abdutora" duas vezes se referindo a dois
  aparelhos diferentes (`adutora` e `abdutora`) — marcado com a tag
  `ambiguo`.

## Resultados de referência

Tabela de avaliação do repositório (52 exemplos, ver
`results/report.md` e o README do código para a análise completa):

| Config | Exercício | Série | Exato | Latência med. |
|---|---|---|---|---|
| A — qwen3:8b zero-shot | 92% | 39% | 13% | 8,2 s |
| B — Gemini 3.1 Flash Lite zero-shot | 99% | 97% | 94% | 4,4 s |
| C — Gemini 3.1 Flash Lite few-shot | 99% | 98% | 92% | 6,5 s |
| D — qwen3:8b few-shot | 88% | 80% | 67% | 10,0 s |

## Licença

CC-BY-4.0. Dê crédito à autora (Cibelle Sousa Rodrigues) e ao
repositório https://github.com/CibelleSousa/trainMe ao reusar.
