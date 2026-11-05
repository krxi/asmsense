import json
from pathlib import Path

import pytest

import alttan_yukari_sim as simulator

from alttan_yukari import (
    components_leaf_first,
    context_symbols,
    graph_for,
    identity,
    indexed,
    orchestrate,
    parse_name,
    rewrite,
)
from alttan_yukari_sim import lexical_metrics, name_candidates, simulate
from lora.hazirla import BAGLAM_BASLIK, DECOMPILE_BASLIK


def raw(symbol, name, calls=(), project="p", opt="-O0", source="a.c"):
    return {
        "id": f"{project}/{source}:{opt}:tam:{symbol}:{name}",
        "proje": project,
        "ad": name,
        "asm": "\n".join(f"call\t{s}" for s in calls) or "ret",
    }


def prepared(row, context=""):
    return {
        "id": row["id"],
        "proje": row["proje"],
        "gercek_ad": row["ad"],
        "oneksiz_onek": ["p"],
        "messages": [
            {"role": "system", "content": "system"},
            {
                "role": "user",
                "content": row["asm"] + (BAGLAM_BASLIK + context if context else "") + DECOMPILE_BASLIK + "sub_0002();",
            },
            {"role": "assistant", "content": json.dumps({"ad": row["ad"]})},
        ],
    }




def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def validation_fixture(tmp_path, monkeypatch):
    source = raw("sub_0001", "p_read_file")
    prompts = [prepared(source)]
    raw_rows = [source]
    predictions = [{"id": source["id"], "proje": "p", "gercek": source["ad"], "tahmin": "read_file"}]
    prompts_path = write_jsonl(tmp_path / "inputs" / "valid_300.jsonl", prompts)
    raw_path = write_jsonl(tmp_path / "inputs" / "dogrulama.jsonl", raw_rows)
    predictions_path = write_jsonl(tmp_path / "inputs" / "valid300-v5.jsonl", predictions)

    (tmp_path / "lora").mkdir(parents=True, exist_ok=True)
    (tmp_path / "rapor" / "arastirma").mkdir(parents=True, exist_ok=True)
    (tmp_path / "lora" / "v6_girdi_manifest.json").write_text(
        json.dumps({"beklenen_sha256": {"valid_v6": simulator.sha256(prompts_path)}}),
        encoding="utf-8",
    )
    (tmp_path / "rapor" / "arastirma" / "dogrulama_manifest.json").write_text(
        json.dumps(
            {
                "tam_dogrulama_sha256": simulator.sha256(raw_path),
                "dondurulmus_tahminler": {"v5": simulator.sha256(predictions_path)},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(simulator, "KOK", tmp_path)
    return prompts_path, raw_path, predictions_path, prompts, raw_rows, predictions


def refresh_prediction_hash(tmp_path, predictions_path):
    manifest_path = tmp_path / "rapor" / "arastirma" / "dogrulama_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["dondurulmus_tahminler"]["v5"] = simulator.sha256(predictions_path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_prediction_gold_label_mismatch_fails():
    a = raw("sub_0001", "a")
    prediction = {**a, "gercek": "wrong_gold", "tahmin": "valid_name"}
    with pytest.raises(ValueError, match="gold label mismatch"):
        simulate([prepared(a)], indexed([a]), [prediction])


def test_validation_guard_accepts_exact_pinned_inputs(tmp_path, monkeypatch):
    inputs = validation_fixture(tmp_path, monkeypatch)
    simulator.validate_validation_inputs(*inputs)


def test_validation_guard_rejects_changed_prompt_hash(tmp_path, monkeypatch):
    inputs = validation_fixture(tmp_path, monkeypatch)
    prompts_path = inputs[0]
    prompts_path.write_text(prompts_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="prompts do not match"):
        simulator.validate_validation_inputs(*inputs)


def test_validation_guard_rejects_mismatched_prediction_ids(tmp_path, monkeypatch):
    inputs = validation_fixture(tmp_path, monkeypatch)
    prompts_path, raw_path, predictions_path, prompts, raw_rows, predictions = inputs
    other = raw("sub_0009", "p_other")
    changed = [{**predictions[0], "id": other["id"], "gercek": other["ad"]}]
    write_jsonl(predictions_path, changed)
    refresh_prediction_hash(tmp_path, predictions_path)
    with pytest.raises(ValueError, match="identifier sets"):
        simulator.validate_validation_inputs(
            prompts_path, raw_path, predictions_path, prompts, raw_rows, changed
        )


def test_validation_guard_rejects_prediction_gold_mismatch(tmp_path, monkeypatch):
    inputs = validation_fixture(tmp_path, monkeypatch)
    prompts_path, raw_path, predictions_path, prompts, raw_rows, predictions = inputs
    changed = [{**predictions[0], "gercek": "wrong_gold"}]
    write_jsonl(predictions_path, changed)
    refresh_prediction_hash(tmp_path, predictions_path)
    with pytest.raises(ValueError, match="gold label"):
        simulator.validate_validation_inputs(
            prompts_path, raw_path, predictions_path, prompts, raw_rows, changed
        )


def test_validation_guard_rejects_raw_directories(tmp_path, monkeypatch):
    inputs = validation_fixture(tmp_path, monkeypatch)
    prompts_path, raw_path, predictions_path, prompts, raw_rows, predictions = inputs
    raw_path.unlink()
    raw_path.mkdir()
    with pytest.raises(ValueError, match="one complete validation"):
        simulator.validate_validation_inputs(
            prompts_path, raw_path, predictions_path, prompts, raw_rows, predictions
        )


def test_row_level_export_must_stay_outside_repository(tmp_path, monkeypatch):
    monkeypatch.setattr(simulator, "KOK", tmp_path)
    assert simulator.is_inside_repo(tmp_path / "exports" / "validation.jsonl")
    assert not simulator.is_inside_repo(tmp_path.parent / "validation.jsonl")


def test_readme_bottom_up_example_is_validation_only():
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    start = readme.index("### Bottom-up naming (no training)")
    end = readme.index("alttan_yukari.py runs", start)
    section = readme[start:end]
    fence = chr(96) * 3
    command = section.split(fence + "bash", 1)[1].split(fence, 1)[0]
    assert "valid_300.jsonl" in command
    assert "dogrulama.jsonl" in command
    assert "test_sabit" not in section
    assert "test2000" not in section
    assert "eval115" not in section
    assert "--export" not in command
    assert "fixed validation sample" in readme[end:]


def test_rewriting_keeps_asm_decompile_literals_and_substrings():
    context = 'sub_0002 (2 komut): çağırır sub_0003; string "sub_0002"\nsub_00020 (1 komut)'
    text = "call sub_0002" + BAGLAM_BASLIK + context + DECOMPILE_BASLIK + "sub_0002();"
    result = rewrite(text, {"sub_0002": "read_file", "sub_0003": "close_file"})
    assert result.startswith("call sub_0002" + BAGLAM_BASLIK + "read_file (2 komut)")
    assert 'string "sub_0002"' in result
    assert result.endswith(DECOMPILE_BASLIK + "sub_0002();")
    assert "sub_00020 (1 komut)" in result
    assert context_symbols('string "sub_0009" sub_0002') == {"sub_0002"}


def test_identity_scopes_project_opt_mode_but_not_source():
    a = raw("sub_0001", "a", source="a.c")
    b = raw("sub_0001", "b", source="b.c")
    assert identity(a) == identity(b)
    with pytest.raises(ValueError, match="duplicate"):
        indexed([a, b])
    assert identity(a) != identity(raw("sub_0001", "a", project="other"))
    assert identity(a) != identity(raw("sub_0001", "a", opt="-O2"))


def test_leaf_first_chain_cycle_self_and_disconnected():
    graph = {"a": {"b"}, "b": {"c"}, "c": set(), "d": {"e", "c"}, "e": {"d"}, "f": {"f"}, "g": set()}
    groups = list(components_leaf_first(graph))
    position = {node: i for i, group in enumerate(groups) for node in group}
    assert position["c"] < position["b"] < position["a"]
    assert position["c"] < position["d"] == position["e"]
    assert len(position) == len(graph)


def test_large_chain_is_iterative():
    graph = {n: {n + 1} if n < 2499 else set() for n in range(2500)}
    assert list(components_leaf_first(graph)) == [[n] for n in reversed(range(2500))]


def test_orchestration_propagates_without_gold_or_cross_scope():
    leaf = raw("sub_0001", "GOLD_LEAF")
    caller = raw("sub_0002", "GOLD_CALLER", ["sub_0001", "sub_0099"])
    other = raw("sub_0001", "OTHER_GOLD", project="other")
    inputs = indexed([prepared(leaf), prepared(caller, "sub_0001 (1 komut)"), prepared(other)])
    source = indexed([leaf, caller, other])
    results = []

    def predict(row, messages):
        assert all(m["role"] != "assistant" for m in messages)
        assert not any("GOLD" in m["content"] for m in messages)
        if row["id"] == caller["id"]:
            assert "predicted_leaf (1 komut)" in messages[1]["content"]
        return {"ad": "predicted_leaf" if row["id"] == leaf["id"] else "another_prediction"}

    orchestrate(inputs, source, predict, results.append)
    record = next(r for r in results if r["id"] == caller["id"])
    assert record["missing_direct_callees"] == 1
    assert record["rewritten_symbols"] == 1


def test_cycle_predictions_commit_simultaneously_and_self_stays_anonymous():
    a = raw("sub_0001", "gold_a", ["sub_0002"])
    b = raw("sub_0002", "gold_b", ["sub_0001"])
    own = raw("sub_0003", "gold_self", ["sub_0003"])
    source = indexed([a, b, own])
    inputs = indexed(
        [prepared(a, "sub_0002 (1 komut)"), prepared(b, "sub_0001 (1 komut)"), prepared(own, "sub_0003 (1 komut)")]
    )
    records = []

    def predict(row, messages):
        assert "predicted" not in messages[1]["content"]
        return {"ad": "predicted"}

    orchestrate(inputs, source, predict, records.append)
    assert all(r["recursive"] for r in records)
    assert all(not r["context_changed"] for r in records)
    assert sorted(r["component_size"] for r in records) == [1, 2, 2]


def test_call_graph_does_not_treat_context_grandchildren_as_direct_edges():
    a = raw("sub_0001", "a", ["sub_0002"])
    b = raw("sub_0002", "b")
    c = raw("sub_0003", "c")
    rows = [prepared(a, "sub_0002 (1 komut): çağırır sub_0003"), prepared(b), prepared(c)]
    graph, _ = graph_for(indexed(rows), indexed([a, b, c]))
    assert graph[identity(a)] == {identity(b)}


def test_missing_raw_fails_instead_of_inventing_graph():
    row = prepared(raw("sub_0001", "a"))
    with pytest.raises(ValueError, match="missing raw"):
        graph_for(indexed([row]), {})


def test_lexical_diagnostics_are_not_model_predictions():
    assert name_candidates('sub_0001 (10 komut): çağırır malloc; string "read_file"') == ["malloc"]
    score = lexical_metrics("read_file", ["read_buffer", "write_file"])
    assert score["all_shared"]
    assert score["token_recall"] == 1
    assert score["best_copy_f1"] == 0.5


def test_simulator_gold_prediction_coverage_and_self_exclusion():
    a = raw("sub_0001", "p_read_file", ["sub_0002", "sub_0001"])
    b = raw("sub_0002", "p_read_buffer")
    row = prepared(a, "sub_0002 (1 komut): çağırır sub_0001")
    prediction = {**b, "gercek": b["ad"], "tahmin": "write_buffer"}
    summary, exports = simulate([row], indexed([a, b]), [prediction])
    assert summary["counts"]["self_symbol_slots_excluded"] == 1
    assert summary["modes"]["gold"]["macro_token_recall"] == 0.5
    assert summary["modes"]["v5_predicted"]["macro_token_recall"] == 0
    assert summary["modes"]["gold_prediction_coverage"]["macro_token_recall"] == 0.5
    assert "sub_0001" in exports[0]["prompts"]["gold"][1]["content"]
    assert all(m["role"] != "assistant" for m in exports[0]["prompts"]["gold"])


def test_prediction_identity_mismatch_fails():
    a = raw("sub_0001", "a")
    changed = raw("sub_0009", "changed")
    prediction = {**changed, "gercek": changed["ad"], "tahmin": "valid_name"}
    with pytest.raises(ValueError, match="not aligned"):
        simulate([prepared(a)], indexed([a]), [prediction])


@pytest.mark.parametrize("content", ['{"ad": "bad name"}', '{"ad": "sub_0001"}', '{"ad": null}'])
def test_invalid_model_name_fails(content):
    with pytest.raises(ValueError):
        parse_name(content)


def test_fenced_model_json():
    assert parse_name('```json\n{"ad": "read_file"}\n```')["ad"] == "read_file"
