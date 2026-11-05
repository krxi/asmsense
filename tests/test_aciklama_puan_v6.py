import json

import pytest

import aciklama_puan_v6 as ap6


def _kimlikler():
    return [f"proje{no // 2}/kaynak.c:{no}" for no in range(4)]


def _puan_dosyasi(yol, puanlar, kimlikler=None):
    kimlikler = kimlikler or _kimlikler()
    satirlar = [
        {
            "id": kimlik,
            "f1": 0.25,
            "puan_en": puan,
            "puan_tr": puan,
        }
        for kimlik, puan in zip(kimlikler, puanlar)
    ]
    yol.write_text(
        "".join(json.dumps(satir, ensure_ascii=False) + "\n" for satir in satirlar),
        encoding="utf-8",
    )
    return yol


def test_ozet_hakem_hatalarini_kapsamdan_silmeden_ayri_gosterir(tmp_path):
    kimlikler = _kimlikler()
    aday = _puan_dosyasi(tmp_path / "aday.jsonl", [2, 1, 0, None], kimlikler)
    v5 = _puan_dosyasi(tmp_path / "v5.jsonl", [2, 0, 2, None], kimlikler)

    sonuc = ap6.ozet(aday, v5, tekrar=200)
    en = sonuc["diller"]["en"]

    assert en["n"] == 4
    assert en["puanlanan"] == 3
    assert en["hata"] == 1
    assert en["ortalama"] == 1.0
    assert en["dogru_orani"] == 0.25
    assert en["tam_karar_dogru_orani"] == pytest.approx(1 / 3)
    assert en["tam_karar_kismen_orani"] == pytest.approx(1 / 3)
    assert en["tam_karar_yanlis_orani"] == pytest.approx(1 / 3)
    assert en["yanlis_orani"] == 0.25
    assert en["v5_dogru_orani"] == 0.5
    assert en["v5_tam_karar_dogru_orani"] == pytest.approx(2 / 3)
    assert en["v5_hata"] == 1
    assert en["fark"] == -0.25
    assert en["proje_sayisi"] == 2
    assert en["hedef_gecildi"] is False


def test_ozet_tum_hakem_cevaplari_bos_oldugunda_sifira_bolmez(tmp_path):
    aday = _puan_dosyasi(tmp_path / "aday.jsonl", [None] * 4)
    v5 = _puan_dosyasi(tmp_path / "v5.jsonl", [None] * 4)

    en = ap6.ozet(aday, v5, tekrar=100)["diller"]["en"]

    assert en["n"] == 4
    assert en["puanlanan"] == 0
    assert en["hata"] == 4
    assert en["ortalama"] is None
    assert en["tam_karar_dogru_orani"] is None
    assert en["tam_karar_yanlis_orani"] is None
    assert en["dogru_orani"] == 0.0
    assert en["fark"] == 0.0


def test_ozet_esli_kimlik_kumesi_farkini_reddeder(tmp_path):
    aday = _puan_dosyasi(tmp_path / "aday.jsonl", [2, 1, 0, None])
    farkli = _kimlikler()
    farkli[-1] = "baska_proje/kaynak.c:son"
    v5 = _puan_dosyasi(tmp_path / "v5.jsonl", [2, 0, 2, None], farkli)

    with pytest.raises(ValueError, match="aynı kimlik kümesi"):
        ap6.ozet(aday, v5, tekrar=100)


def test_ozet_bool_puani_gecerli_tamsayi_saymaz(tmp_path):
    aday = _puan_dosyasi(tmp_path / "aday.jsonl", [True, 1, 0, None])
    v5 = _puan_dosyasi(tmp_path / "v5.jsonl", [2, 0, 2, None])

    with pytest.raises(ValueError, match="Puan"):
        ap6.ozet(aday, v5, tekrar=100)
