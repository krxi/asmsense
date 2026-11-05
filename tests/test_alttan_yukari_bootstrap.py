import json

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
        "proje-a": {"rows": 200, "anonymised": 0.10, "gold": 0.50, "v5_predicted": 0.20},
        "proje-b": {"rows": 50, "anonymised": 0.30, "gold": 0.70, "v5_predicted": 0.40},
        "proje-c": {"rows": 50, "anonymised": 0.50, "gold": 0.60, "v5_predicted": 0.70},
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
    monkeypatch.setattr(bootstrap, "KOK", kok)
    ozet_yolu = yaz_json(tmp_path / "bottom-up-summary.json", sentetik_ozet())
    return kok, ozet_yolu


def test_proje_bootstrap_esli_ve_deterministik(tmp_path, monkeypatch):
    _, ozet_yolu = hazirla(tmp_path, monkeypatch)
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8"))

    ilk = bootstrap.rapor_olustur(ozet_yolu, ozet, tekrar=500, tohum=42)
    ikinci = bootstrap.rapor_olustur(ozet_yolu, ozet, tekrar=500, tohum=42)

    assert ilk == ikinci
    assert ilk["n_projects"] == 3
    assert ilk["n_rows"] == 300
    assert ilk["comparisons"]["gold_minus_anonymised_macro_token_recall"]["estimate"] == 0.35
    assert ilk["comparisons"]["v5_predicted_minus_anonymised_macro_token_recall"]["estimate"] == pytest.approx(
        0.116666667
    )
    for sonuc in ilk["comparisons"].values():
        assert sonuc["n_projects"] == 3
        assert sonuc["n_rows"] == 300
        assert sonuc["ci95"][0] <= sonuc["ci95"][1]


def test_rapor_yalniz_toplu_dayanak_icerir(tmp_path, monkeypatch):
    _, ozet_yolu = hazirla(tmp_path, monkeypatch)
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8"))

    rapor = bootstrap.rapor_olustur(ozet_yolu, ozet, tekrar=100, tohum=7)
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
    _, ozet_yolu = hazirla(tmp_path, monkeypatch)
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8"))
    ozet["provenance"]["prompts_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="sabit v6 validation"):
        bootstrap.rapor_olustur(ozet_yolu, ozet, tekrar=100)


def test_eslesmeyen_proje_kumeleri_reddedilir(tmp_path, monkeypatch):
    _, ozet_yolu = hazirla(tmp_path, monkeypatch)
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8"))
    del ozet["projects"]["gold"]["proje-c"]

    with pytest.raises(ValueError, match="proje kümeleri farklı"):
        bootstrap.rapor_olustur(ozet_yolu, ozet, tekrar=100)


def test_proje_satir_sayisi_uyusmazligi_reddedilir(tmp_path, monkeypatch):
    _, ozet_yolu = hazirla(tmp_path, monkeypatch)
    ozet = json.loads(ozet_yolu.read_text(encoding="utf-8"))
    ozet["projects"]["v5_predicted"]["proje-b"]["rows"] = 49

    with pytest.raises(ValueError, match="satır sayıları farklı"):
        bootstrap.rapor_olustur(ozet_yolu, ozet, tekrar=100)


def test_gecersiz_bootstrap_parametreleri_reddedilir():
    with pytest.raises(ValueError, match="en az 100"):
        bootstrap.esli_proje_bootstrap({}, tekrar=99)

    with pytest.raises(ValueError, match="tohumu tamsayı"):
        bootstrap.esli_proje_bootstrap({}, tekrar=100, tohum=True)


def test_toplu_cikti_depo_disinda_olmali(tmp_path, monkeypatch):
    kok, _ = hazirla(tmp_path, monkeypatch)

    assert bootstrap.depo_icinde(kok / "summary.json")
    assert not bootstrap.depo_icinde(tmp_path / "summary.json")
