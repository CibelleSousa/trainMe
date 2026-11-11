# Treino em linguagem natural (agente de IA + avaliação)

Projeto de portfólio com prazo: código pronto até sáb 14/11/2026. Especificação completa em `SPEC.md` (leia só a seção de que precisar, não o arquivo inteiro a cada tarefa).

## O que é
Recebe texto livre em português sobre treino de musculação, extrai séries (exercício, carga, repetições, marcadores), salva em SQLite e sugere a progressão por regra determinística. Inclui um harness de avaliação que compara modelos e prompts.

## Stack
Python 3.11+, FastAPI, SQLModel (SQLite), Pydantic v2, pytest, Docker.
LLMs: Ollama local (`qwen3:8b`, GPU de 8 GB) e API do Gemini (`google-genai`). Chave em `.env` (`GEMINI_API_KEY`, `GEMINI_MODEL`), nunca no git.

## Comandos
- Ambiente: `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`
- Testes: `pytest -q 2>&1 | tail -30`
- API: `uvicorn app.main:app --reload`
- Avaliação: `python -m eval.validate`, `python -m eval.run --config all`, `python -m eval.report`

## Regras fixas
- Todo número (carga, repetições) mostrado ao usuário vem do retorno de uma função de código, nunca do texto gerado pelo modelo.
- Normalização de exercícios e regra de progressão são código puro, com testes. O LLM só extrai dados e redige a mensagem.
- Ollama: `think=False`, `format` com JSON Schema, `temperature=0`, `num_ctx=4096` (só subir para 8192 se `ollama ps` continuar em 100% GPU).
- Dataset: o campo `source` é obrigatório (`real`, `reconstruido`, `sintetico`). Nunca rotular sintético como real.
- Escopo: nada fora do SPEC §2 e das prioridades do SPEC §3. Se algo parecer necessário e estiver fora, pergunte antes.
- Dúvida sobre API ou nome de modelo: consulte a documentação oficial atual, não a memória.
- Não instalar plugins, skills ou servidores MCP de terceiros. Não usar subagentes.
- Nunca imprimir, logar ou commitar chaves ou o conteúdo do `.env`.

## Como trabalhar (economia de tokens)
- Antes de codar cada etapa: plano de até 5 linhas e aguardar meu "ok".
- Um módulo com seus testes por vez. Não reler o repositório inteiro; abra só os arquivos da tarefa.
- Saída de testes sempre filtrada (`| tail -30`). Nunca colar logs longos.
- Ao fim de cada etapa: testes verdes, um commit pequeno em português (`feat:`, `test:`, `docs:`), resumo de até 6 linhas e a proposta da próxima etapa. Depois pare e espere.
- Textos do README e do artigo: honestos, com limitações explícitas. Sem afirmar o que não foi medido.

## Status (atualize ao fim de cada etapa)
- [x] Etapa 0: estrutura, schemas, banco
- [x] Etapa 1: exercises.py e progression.py com testes
- [ ] Etapa 2: clientes LLM e extract.py
- [ ] Etapa 3: dataset, validador, harness e relatório
- [ ] Etapa 4 (P1): agente com ferramentas e API
- [ ] Etapa 5 (P2): página com microfone (Web Speech API), export CSV, Docker, README
