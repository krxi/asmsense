import json

import pytest

import alttan_yukari_bootstrap as bootstrap


HASHES = {
    "prompts": "a" * 64,
    "raw": "b" * 64,
    "predictions": "c" * 64,
}


def yaz_json(yol, veri):
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")
    return yol


def sentetik_ozet():
    proje_satirlari = {
        "proje-a": {
            "rows": 200,
            "anonymised": 0.10,
            "gold": 0.50,
            "v5_predicted": 0.20,
        },
        "proje-b": {
            "rows": 50,
            "anonymised": 0.30,
            "gold": 0.70,
            "v5_predicted": 0.40,
        },
        "proje-c": {
            "rows": 50,
            "anonymised": 0.50,
            "gold": 0.60,
            "v5_predicted": 0.70,
        },
    }
    projects = {}
    modes = {}
    for mode in bootstrap.MODES:
        projects[mode] = {
            project: {"rows": values["rows"], "macro_token_recall": values[mode]}
            for project, values in proje_satirlari.items()
        }
        modes[mode] = {"rows": 300}
    return {
        "prediction_rows": 300,
        "valid_prediction_rows": 275,
        "modes": modes,
        "projects": projects,
        "provenance": {
            "prompts_sha256": HASHES["prompts"],
            "raw_sha256": {"validation-v4.jsonl": HASHES["raw"]},
            "predictions_sha256": HASHES["predictions"],
        },
    }


def hazirla(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    yaz_json(
        root / "lora" / "v6_girdi_manifest.json",
        {"beklenen_sha256": {"valid_v6": HASHES["prompts"]}},
    )
    yaz_json(
        root / "rapor" / "arastirma" / "dogrulama_manifest.json",
        {
            "tam_dogrulama_sha256": HASHES["raw"],
            "dondurulmus_tahminler": {"v5": HASHES["predictions"]},
        },
    )
    monkeypatch.setattr(bootstrap, "KOK", root)
    summary_path = yaz_json(tmp_path / "bottom-up-summary.json", sentetik_ozet())
    return root, summary_path


def test_project_cluster_bootstrap_is_paired_and_deterministic(tmp_path, monkeypatch):
    _, summary_path = hazirla(tmp_path, monkeypatch)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    first = bootstrap.build_report(summary_path, summary, replicates=500, seed=42)
    second = bootstrap.build_report(summary_path, summary, replicates=500, seed=42)

    assert first == second
    assert first["n_projects"] == 3
    assert first["n_rows"] == 300
    assert first["comparisons"]["gold_minus_anonymised_macro_token_recall"]["estimate"] == 0.35
    assert first["comparisons"]["v5_predicted_minus_anonymised_macro_token_recall"]["estimate"] == pytest.approx(
        0.116666667
    )
    for result in first["comparisons"].values():
        assert result["n_projects"] == 3
        assert result["n_rows"] == 300
        assert result["ci95"][0] <= result["ci95"][1]


def test_report_contains_only_aggregate_provenance(tmp_path, monkeypatch):
    _, summary_path = hazirla(tmp_path, monkeypatch)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    report = bootstrap.build_report(summary_path, summary, replicates=100, seed=7)
    encoded = json.dumps(report, ensure_ascii=False)

    assert "proje-a" not in encoded
    assert "proje-b" not in encoded
    assert "proje-c" not in encoded
    assert HASHES["prompts"] in encoded
    assert HASHES["raw"] in encoded
    assert HASHES["predictions"] in encoded
    assert "id" not in report
    assert "asm" not in report


def test_wrong_validation_provenance_fails_closed(tmp_path, monkeypatch):
    _, summary_path = hazirla(tmp_path, monkeypatch)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["provenance"]["prompts_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="pinned v6 validation"):
        bootstrap.build_report(summary_path, summary, replicates=100)


def test_mismatched_project_sets_are_rejected(tmp_path, monkeypatch):
    _, summary_path = hazirla(tmp_path, monkeypatch)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    del summary["projects"]["gold"]["proje-c"]

    with pytest.raises(ValueError, match="project sets differ"):
        bootstrap.build_report(summary_path, summary, replicates=100)


def test_per_project_row_count_mismatch_is_rejected(tmp_path, monkeypatch):
    _, summary_path = hazirla(tmp_path, monkeypatch)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["projects"]["v5_predicted"]["proje-b"]["rows"] = 49

    with pytest.raises(ValueError, match="row counts differ"):
        bootstrap.build_report(summary_path, summary, replicates=100)


def test_invalid_bootstrap_parameters_are_rejected():
    with pytest.raises(ValueError, match=">= 100"):
        bootstrap.paired_project_bootstrap({}, replicates=99)

    with pytest.raises(ValueError, match="seed must be an integer"):
        bootstrap.paired_project_bootstrap({}, replicates=100, seed=True)


def test_aggregate_output_must_stay_outside_repository(tmp_path, monkeypatch):
    root, _ = hazirla(tmp_path, monkeypatch)

    assert bootstrap.is_inside_repo(root / "summary.json")
    assert not bootstrap.is_inside_repo(tmp_path / "summary.json")
