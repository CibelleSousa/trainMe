import json

import eval.run as run_mod
from app.schemas import ExerciseEntry, ExtractionResult, SetEntry


class ClientFalso:
    pass


def preparar(tmp_path, monkeypatch, exemplos, provider="ollama"):
    dataset = tmp_path / "dataset.jsonl"
    with dataset.open("w", encoding="utf-8") as f:
        for ex in exemplos:
            f.write(json.dumps(ex) + "\n")

    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    (configs_dir / "T.yaml").write_text(f"provider: {provider}\nfew_shot: false\n")

    results_dir = tmp_path / "results"

    monkeypatch.setattr(run_mod, "DATASET_PATH", dataset)
    monkeypatch.setattr(run_mod, "CONFIGS_DIR", configs_dir)
    monkeypatch.setattr(run_mod, "RESULTS_DIR", results_dir)
    monkeypatch.setattr(run_mod, "criar_client", lambda provider, model=None: ClientFalso())
    return results_dir


def test_rodar_config_salva_um_resultado_por_exemplo(tmp_path, monkeypatch):
    chamadas = []

    def extract_falso(client, text, few_shot=True):
        chamadas.append(text)
        return ExtractionResult(
            entries=[ExerciseEntry(exercise_raw="supino", sets=[SetEntry(weight_kg=80, reps=10)])],
            needs_confirmation=False,
        )

    monkeypatch.setattr(run_mod, "extract", extract_falso)
    results_dir = preparar(
        tmp_path, monkeypatch, [{"id": "a", "text": "treino a"}, {"id": "b", "text": "treino b"}]
    )

    caminho = run_mod.rodar_config("T")
    linhas = [json.loads(l) for l in caminho.read_text().splitlines()]

    assert len(linhas) == 2
    assert len(chamadas) == 2
    assert {l["id"] for l in linhas} == {"a", "b"}


def test_rodar_config_retoma_e_nao_repete_exemplo_ja_feito(tmp_path, monkeypatch):
    chamadas = []

    def extract_falso(client, text, few_shot=True):
        chamadas.append(text)
        return ExtractionResult(entries=[], needs_confirmation=False)

    monkeypatch.setattr(run_mod, "extract", extract_falso)
    results_dir = preparar(
        tmp_path, monkeypatch, [{"id": "a", "text": "treino a"}, {"id": "b", "text": "treino b"}]
    )

    run_mod.rodar_config("T")
    assert len(chamadas) == 2

    run_mod.rodar_config("T")
    assert len(chamadas) == 2


def test_rodar_config_registra_erro_sem_derrubar_a_rodada(tmp_path, monkeypatch):
    def extract_falso(client, text, few_shot=True):
        raise ValueError("saída inválida")

    monkeypatch.setattr(run_mod, "extract", extract_falso)
    preparar(tmp_path, monkeypatch, [{"id": "a", "text": "treino a"}])

    caminho = run_mod.rodar_config("T")
    linha = json.loads(caminho.read_text().splitlines()[0])
    assert linha["output"] is None
    assert "ValueError" in linha["error"]
