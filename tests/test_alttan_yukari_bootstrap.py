import json
import subprocess

import pytest

import alttan_yukari_bootstrap as bootstrap


HASHLER = {
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
            "gold_prediction_coverage": 0.40,
        },
        "proje-b": {
            "rows": 50,
            "anonymised": 0.30,
            "gold": 0.70,
            "v5_predicted": 0.40,
            "gold_prediction_coverage": 0.60,
        },
        "proje-c": {
            "rows": 50,
            "anonymised": 0.50,
            "gold": 0.60,
            "v5_predicted": 0.70,
            "gold_prediction_coverage": 0.50,
        },
    }
    projeler = {}
    kipler = {}
    for kip in bootstrap.KIPLER:
        projeler[kip] = {
            proje: {"rows": deger["rows"], "macro_token_recall": deger[kip]} for proje, deger in proje_satirlari.items()
        }
        kipler[kip] = {"rows": 300}
    return {
        "prediction_rows": 300,
        "valid_prediction_rows": 275,
        "modes": kipler,
        "projects": projeler,
        "provenance": {
            "prompts_sha256": HASHLER["prompts"],
            "raw_sha256": {"validation-v4.jsonl": HASHLER["raw"]},
            "predictions_sha256": HASHLER["predictions"],
        },
    }


def hazirla(tmp_path, monkeypatch):
    kok = tmp_path / "repo"
    yaz_json(
        kok / "lora" / "v6_girdi_manifest.json",
        {"beklenen_sha256": {"valid_v6": HASHLER["prompts"]}},
    )
    yaz_json(
        kok / "rapor" / "arastirma" / "dogrulama_manifest.json",
        {
            "tam_dogrulama_sha256": HASHLER["raw"],
            "dondurulmus_tahminler": {"v5": HASHLER["predictions"]},
        },
    )
    (kok / "alttan_yukari_sim.py").write_text("# sentetik denetim araci\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=kok, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "tests@example.invalid"], cwd=kok, check=True)
    subprocess.run(["git", "config", "user.name", "Asmsense Tests"], cwd=kok, check=True)
    subprocess.run(["git", "add", "."], cwd=kok, check=True)
    subprocess.run(["git", "commit", "-m", "sentetik audit"], cwd=kok, check=True, capture_output=True)
    audit_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=kok, text=True).strip()
    monkeypatch.setattr(bootstrap, "KOK", kok)
    ozet_yolu = yaz_json(tmp_path / "bottom-up-summary.json", sentetik_ozet())
    return kok, ozet_yolu, audit_commit


def test_proje_bootstrap_esli_ve_deterministik(tmp_path, monkeypatch):
    kok, ozet_yolu, audit_commit = hazirla(tmp_path, monkeypatch)
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8"))

    ilk = bootstrap.rapor_olustur(ozet_yolu, ozet, audit_commit=audit_commit, tekrar=500, tohum=42)
    ikinci = bootstrap.rapor_olustur(ozet_yolu, ozet, audit_commit=audit_commit, tekrar=500, tohum=42)

    assert ilk == ikinci
    assert ilk["audit_commit"] == audit_commit
    assert (
        ilk["audit_tree"]
        == subprocess.check_output(
            ["git", "rev-parse", "--verify", audit_commit + "^{tree}"], cwd=kok, text=True
        ).strip()
    )
    assert ilk["audit_simulator_sha256"] == bootstrap.sha256(kok / "alttan_yukari_sim.py")
    assert ilk["audit_provenance"] == "clean_tracked_head_operator_attestation"
    assert ilk["n_projects"] == 3
    assert ilk["n_rows"] == 300
    assert ilk["comparisons"]["gold_minus_anonymised_macro_token_recall"]["estimate"] == 0.35
    assert ilk["comparisons"]["v5_predicted_minus_anonymised_macro_token_recall"]["estimate"] == pytest.approx(
        0.116666667
    )
    assert ilk["comparisons"]["coverage_matched_gold_minus_anonymised_macro_token_recall"]["estimate"] == 0.25
    assert ilk["comparisons"]["coverage_matched_gold_minus_v5_predicted_macro_token_recall"][
        "estimate"
    ] == pytest.approx(0.133333333)
    assert ilk["comparisons"]["gold_minus_coverage_matched_gold_macro_token_recall"]["estimate"] == 0.10
    for sonuc in ilk["comparisons"].values():
        assert sonuc["n_projects"] == 3
        assert sonuc["n_rows"] == 300
        assert sonuc["ci95"][0] <= sonuc["ci95"][1]


def test_rapor_yalniz_toplu_dayanak_icerir(tmp_path, monkeypatch):
    _, ozet_yolu, audit_commit = hazirla(tmp_path, monkeypatch)
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8"))

    rapor = bootstrap.rapor_olustur(ozet_yolu, ozet, audit_commit=audit_commit, tekrar=100, tohum=7)
    kodlanmis = json.dumps(rapor, ensure_ascii=False)

    assert "proje-a" not in kodlanmis
    assert "proje-b" not in kodlanmis
    assert "proje-c" not in kodlanmis
    assert HASHLER["prompts"] in kodlanmis
    assert HASHLER["raw"] in kodlanmis
    assert HASHLER["predictions"] in kodlanmis
    assert "id" not in rapor
    assert "asm" not in rapor


def test_yanlis_dogrulama_dayanagi_reddedilir(tmp_path, monkeypatch):
    _, ozet_yolu, audit_commit = hazirla(tmp_path, monkeypatch)
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8"))
    ozet["provenance"]["prompts_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="sabit v6 validation"):
        bootstrap.rapor_olustur(ozet_yolu, ozet, audit_commit=audit_commit, tekrar=100)


def test_eslesmeyen_proje_kumeleri_reddedilir(tmp_path, monkeypatch):
    _, ozet_yolu, audit_commit = hazirla(tmp_path, monkeypatch)
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8"))
    del ozet["projects"]["gold"]["proje-c"]

    with pytest.raises(ValueError, match="proje kümeleri farklı"):
        bootstrap.rapor_olustur(ozet_yolu, ozet, audit_commit=audit_commit, tekrar=100)


def test_kapsama_esli_altin_kipi_zorunludur(tmp_path, monkeypatch):
    _, ozet_yolu, audit_commit = hazirla(tmp_path, monkeypatch)
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8"))
    del ozet["projects"]["gold_prediction_coverage"]

    with pytest.raises(ValueError, match="gold_prediction_coverage"):
        bootstrap.rapor_olustur(ozet_yolu, ozet, audit_commit=audit_commit, tekrar=100)


def test_kapsama_esli_altin_satir_sayisi_eslesmelidir(tmp_path, monkeypatch):
    _, ozet_yolu, audit_commit = hazirla(tmp_path, monkeypatch)
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8"))
    ozet["projects"]["gold_prediction_coverage"]["proje-b"]["rows"] = 49

    with pytest.raises(ValueError, match="satır sayıları farklı"):
        bootstrap.rapor_olustur(ozet_yolu, ozet, audit_commit=audit_commit, tekrar=100)


def test_proje_satir_sayisi_uyusmazligi_reddedilir(tmp_path, monkeypatch):
    _, ozet_yolu, audit_commit = hazirla(tmp_path, monkeypatch)
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8"))
    ozet["projects"]["v5_predicted"]["proje-b"]["rows"] = 49

    with pytest.raises(ValueError, match="satır sayıları farklı"):
        bootstrap.rapor_olustur(ozet_yolu, ozet, audit_commit=audit_commit, tekrar=100)


def test_audit_commit_depo_gecmisinde_olmali(tmp_path, monkeypatch):
    _, ozet_yolu, _ = hazirla(tmp_path, monkeypatch)
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8"))

    with pytest.raises(ValueError, match="audit commit depoda"):
        bootstrap.rapor_olustur(ozet_yolu, ozet, audit_commit="0" * 40, tekrar=100)


def test_audit_commit_mevcut_head_olmali(tmp_path, monkeypatch):
    kok, ozet_yolu, audit_commit = hazirla(tmp_path, monkeypatch)
    (kok / "sonraki.txt").write_text("sonraki\n", encoding="utf-8")
    subprocess.run(["git", "add", "sonraki.txt"], cwd=kok, check=True)
    subprocess.run(["git", "commit", "-m", "sonraki audit"], cwd=kok, check=True, capture_output=True)
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8"))

    with pytest.raises(ValueError, match="mevcut HEAD ile eşleşmeli"):
        bootstrap.rapor_olustur(ozet_yolu, ozet, audit_commit=audit_commit, tekrar=100)


def test_audit_takipli_calisma_agaci_temiz_olmali(tmp_path, monkeypatch):
    kok, ozet_yolu, audit_commit = hazirla(tmp_path, monkeypatch)
    (kok / "alttan_yukari_sim.py").write_text("# değiştirilmiş\n", encoding="utf-8")
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8"))

    with pytest.raises(ValueError, match="takipli çalışma ağacı temiz"):
        bootstrap.rapor_olustur(ozet_yolu, ozet, audit_commit=audit_commit, tekrar=100)


def test_gecersiz_bootstrap_parametreleri_reddedilir():
    with pytest.raises(ValueError, match="en az 100"):
        bootstrap.esli_proje_bootstrap({}, tekrar=99)

    with pytest.raises(ValueError, match="tohumu tamsayı"):
        bootstrap.esli_proje_bootstrap({}, tekrar=100, tohum=True)


def test_toplu_cikti_depo_disinda_olmali(tmp_path, monkeypatch):
    kok, _, _ = hazirla(tmp_path, monkeypatch)

    assert bootstrap.depo_icinde(kok / "summary.json")
    assert not bootstrap.depo_icinde(tmp_path / "summary.json")
