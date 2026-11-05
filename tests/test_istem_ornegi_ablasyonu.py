import hashlib
import json

import pytest

from molab.istem_ornegi_ablasyonu import (
    KOK,
    cikti_yolu_dogrula,
    dogrulama_satirlari,
    ornek_araligi,
    orneksiz_istem,
)


def _ornek_json(ad="demo_name", en="A demo description.", tr="Örnek açıklama."):
    return json.dumps(
        {"aciklama_en": en, "ad": ad, "aciklama": tr},
        ensure_ascii=False,
    )


def test_orneksiz_istem_yalniz_ornek_degerlerini_degistirir():
    on = "Önceki yönerge. "
    son = " Sonraki yönerge."
    istem = on + _ornek_json() + son

    bas, bitis, nesne = ornek_araligi(istem)
    sonuc = orneksiz_istem(istem)

    assert nesne["ad"] == "demo_name"
    assert istem[:bas] == sonuc[:bas]
    assert istem[bitis:] == sonuc[-len(son) :]
    assert "demo_name" not in sonuc
    assert "A demo description." not in sonuc
    assert "<fonksiyon_adi>" in sonuc
    assert sonuc.startswith(on)
    assert sonuc.endswith(son)


def test_ornek_sayisi_bire_esit_olmali():
    with pytest.raises(ValueError):
        orneksiz_istem("JSON örneği yok")

    nesne = _ornek_json()
    with pytest.raises(ValueError):
        orneksiz_istem(nesne + " " + nesne)


def test_validation_jsonl_sha_ve_kapsam_korunur():
    satirlar = [
        {"id": "proje/a", "proje": "proje"},
        {"id": "proje/b", "proje": "proje"},
    ]
    icerik = ("\n".join(json.dumps(r) for r in satirlar) + "\n").encode()
    ozet = hashlib.sha256(icerik).hexdigest()

    assert dogrulama_satirlari(icerik, ozet, beklenen_n=2) == satirlar
    with pytest.raises(ValueError, match="SHA-256"):
        dogrulama_satirlari(icerik, "0" * 64, beklenen_n=2)
    with pytest.raises(ValueError, match="satırı gerekli"):
        dogrulama_satirlari(icerik, ozet, beklenen_n=3)


def test_validation_kimlikleri_yinelenemez():
    satirlar = [{"id": "proje/a"}, {"id": "proje/a"}]
    icerik = ("\n".join(json.dumps(r) for r in satirlar) + "\n").encode()
    ozet = hashlib.sha256(icerik).hexdigest()

    with pytest.raises(ValueError, match="yinelenmiş"):
        dogrulama_satirlari(icerik, ozet, beklenen_n=2)


def test_aggregate_cikti_depo_disinda_olmali(tmp_path):
    hedef = tmp_path / "ozet.json"
    assert cikti_yolu_dogrula(hedef) == hedef.resolve()

    with pytest.raises(ValueError, match="depo dışında"):
        cikti_yolu_dogrula(KOK / "ozet.json")

    hedef.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError):
        cikti_yolu_dogrula(hedef)
