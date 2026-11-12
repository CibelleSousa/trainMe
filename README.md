# Treino em linguagem natural

Projeto de portfólio: recebe um relato em português livre sobre treino de
musculação ("supino 4x8 com 80, última até a falha"), extrai os dados
estruturados com um LLM, salva em SQLite e sugere a progressão da próxima
sessão por uma regra determinística (código, não LLM). Inclui um harness de
avaliação que compara configurações de extração.

A sugestão de progressão é uma heurística (dupla progressão simples), **não
é recomendação profissional**.

## O que faz

1. Você escreve ou fala o treino (ex.: "remada serrote 3x10 com 40").
2. O LLM extrai exercício, séries, carga e repetições (schema fixo).
3. O código normaliza o nome do exercício e a carga (ex.: anilha por lado) e
   grava no banco.
4. O código consulta o histórico daquele exercício e calcula a sugestão de
   carga/repetição pra próxima sessão.
5. O LLM escreve a mensagem final, usando só os números que o código
   calculou — nenhum número mostrado vem direto do texto do modelo.
6. Se o exercício não é reconhecido, ou a carga é ambígua (pode ser "por
   lado" ou total), o agente pergunta antes de gravar.

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # preencha GEMINI_API_KEY e GEMINI_MODEL
```

- Testes: `pytest -q`
- CLI de extração: `python -m app.extract "supino 3x10 com 80" --provider gemini`
- API + página web: `uvicorn app.main:app --reload` e abra `http://localhost:8000`
- Avaliação:
  ```bash
  python -m eval.validate
  python -m eval.run --config all
  python -m eval.report
  ```
- Exportar histórico: `GET /export.csv`
- Docker: `docker compose up` (sobe a API na porta 8000; precisa do `.env`)

### Página web (P2)

Campo de texto + botão de microfone (Web Speech API, `pt-BR`). Funciona no
Chrome/Chromium — o Firefox não suporta a API de voz. A voz é só uma camada
de entrada de texto; a avaliação é feita sempre em texto.

## Configurações comparadas

| Config | Provider | Modelo | Few-shot |
|---|---|---|---|
| A | Ollama (local) | `qwen3:8b` | não |
| B | Gemini | `gemini-3.1-flash-lite` | não |
| C | Gemini | `gemini-3.1-flash-lite` | sim |
| D | Ollama (local) | `qwen3:8b` | sim |

## Resultados

TODO — rodar `python -m eval.run --config all` com o dataset final e
`python -m eval.report`, e colar aqui a tabela com k/n por configuração,
por fonte (`real`/`reconstruido`/`sintetico`) e por tag. As rodadas feitas
até agora foram parciais (algumas por amostra, com `--ids`), feitas pra
validar o código, não pra tirar conclusão final.

## Limitações

- Dataset pequeno: 52 exemplos no momento (meta do SPEC é ~60).
- 46 dos 52 exemplos são `sintetico` (gerados a partir do histórico
  simulado e revisados), só 6 são `real` (escritos/ditos pela autora). Não
  há `reconstruido` ainda. Com tão poucos exemplos `real`, as métricas por
  fonte não sustentam uma afirmação de "o sistema funciona bem no mundo
  real" — só no que foi medido.
- O histórico de progressão em `data/progression_sim.csv` é **simulado**:
  reconstruído de trás para frente a partir das cargas reais da semana de
  09–11/11/2026, com dupla progressão 8–12. As 3 sessões reais (24/05,
  25/05 e 07/06/2026) são uma amostra pequena à parte.
  A sugestão de progressão é validada por teste unitário, não por dado
  real suficiente pra medir "evolução".
- O texto dos exemplos `sintetico` foi escrito pelo Gemini a partir das
  linhas estruturadas do CSV simulado (estruturado → texto), revisado pela
  autora. Isso favorece estilos de frase que o próprio Gemini sabe gerar —
  um viés real na avaliação, não só uma limitação de tamanho.
- A regra de ambiguidade de lado no agente (Etapa 4) olha só o primeiro
  exercício reconhecido da mensagem, pra não gastar as 3 chamadas de
  ferramenta nisso; mensagens com vários exercícios não ambíguos num
  mesmo pedido não passam pela checagem nos demais.

## Erros conhecidos (análise qualitativa, dataset atual)

Observados rodando os exemplos reais (`r001`–`r006`) nas configs B, C e D
(ver `results/*.jsonl`):

| Exemplo | O que aconteceu | Causa provável |
|---|---|---|
| `r006` | As 3 configs marcaram `rir=2` só nas 2 séries de 8kg, não nas 3 séries do exercício | "deixei 2 na reserva em ambas" é ambíguo — "ambas" pode significar as duas séries de 8kg (leitura do LLM) ou os dois grupos de série (leitura do rótulo) |
| `r001` (Qwen, config D) | Trocou `elevacao_lateral_polia` por `elevacao_lateral_halteres` e a carga (6kg em vez de 5kg) | sem few-shot suficiente pra essa ambiguidade específica do histórico da autora |
| `r001` (Gemini, configs B/C) | Repetições 12 em vez de 10 | não aplicou a regra "repetição com ajuda do personal não conta" |
| `r005` (Qwen, config D) | Perdeu 1 série de `supino_inclinado_maquina` | formato de anotação em linhas (`N x carga x reps`) com séries por bloco — Qwen não expandiu um dos blocos |
| `r002` | Confunde a segunda ocorrência de "cadeira abdutora" | ambíguo no próprio texto: a autora disse "abdutora" duas vezes pra dois aparelhos diferentes (tag `ambiguo`) — não dá pra resolver só com o texto |

## Próximos passos

- Rodar a avaliação final completa (`eval.run --config all` sem `--ids`) e
  preencher a seção de Resultados.
- Ampliar o dataset com mais exemplos `real` e `reconstruido`.
- Dataset no Hugging Face com dataset card.
