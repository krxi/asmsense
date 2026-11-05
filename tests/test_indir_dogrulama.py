import gzip
import hashlib
import io
import json
import zipfile

import pytest

import indir_dogrulama as ind


def sha(veri):
    return hashlib.sha256(veri).hexdigest()


def zip_yap(dosyalar):
    cikti = io.BytesIO()
    with zipfile.ZipFile(cikti, "w", zipfile.ZIP_DEFLATED) as paket:
        for ad, veri in dosyalar.items():
            paket.writestr(ad, veri)
    return cikti.getvalue()


def test_yalniz_valid300_uyesi_ayiklanir(monkeypatch, tmp_path):
    valid = b'{"id":"sentetik-1"}\n{"id":"sentetik-2"}\n'
    ham = b'{"id":"raw-1"}\n{"id":"raw-2"}\n'
    arsiv = zip_yap(
        {
            "train.jsonl": b"train-only-sentinel\n",
            "nested/valid_300.jsonl": valid,
            "test.jsonl": b"held-out-sentinel\n",
        }
    )
    sikistirilmis = gzip.compress(ham)
    acilanlar = []
    asil_ac = zipfile.ZipFile.open

    def acilan_uyeyi_kaydet(paket, bilgi, *args, **kwargs):
        acilanlar.append(bilgi.filename if isinstance(bilgi, zipfile.ZipInfo) else bilgi)
        return asil_ac(paket, bilgi, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "open", acilan_uyeyi_kaydet)
    monkeypatch.setattr(ind, "KOK", tmp_path / "repo")
    monkeypatch.setattr(ind, "V6_ARSIV_SHA256", sha(arsiv))
    monkeypatch.setattr(ind, "V6_VALID_SHA256", sha(valid))
    monkeypatch.setattr(ind, "V6_VALID_SATIR", 2)
    monkeypatch.setattr(ind, "V4_HAM_SHA256", sha(ham))
    monkeypatch.setattr(ind, "V4_SATIR", 2)

    def fake_indir(url, tavan):
        return arsiv if url == ind.V6_URL else sikistirilmis

    monkeypatch.setattr(ind, "indir", fake_indir)
    hedef = tmp_path / "validation-artifacts"
    manifest = ind.indir_dogrulama(hedef)

    assert (hedef / "valid_300-v6.jsonl").read_bytes() == valid
    assert (hedef / "validation-v4.jsonl").read_bytes() == ham
    assert sorted(p.name for p in hedef.iterdir()) == [
        "manifest.json",
        "valid_300-v6.jsonl",
        "validation-v4.jsonl",
    ]
    assert acilanlar == ["nested/valid_300.jsonl"]
    assert manifest["test_uyesi_acildi"] == 0
    assert manifest["artefaktlar"]["valid_300-v6.jsonl"]["satir"] == 2
    manifest_text = (hedef / "manifest.json").read_text(encoding="utf-8")
    assert "held-out-sentinel" not in manifest_text
    assert "sentetik-1" not in manifest_text
    assert set(json.loads(manifest_text)) == {
        "sema",
        "bolum",
        "kaynaklar",
        "artefaktlar",
        "test_uyesi_acildi",
        "gpu",
        "model_cagrisi",
    }


def test_v6_arsiv_hash_uyusmazsa_cikti_olusturulmaz(monkeypatch, tmp_path):
    monkeypatch.setattr(ind, "KOK", tmp_path / "repo")
    monkeypatch.setattr(ind, "indir", lambda *_: b"wrong archive")
    hedef = tmp_path / "validation-artifacts"

    with pytest.raises(ValueError, match="v6 arşiv SHA-256"):
        ind.indir_dogrulama(hedef)

    assert not hedef.exists()


def test_v6_arsivde_tek_valid300_gerekir(monkeypatch):
    valid = b'{"id":"sentetik"}\n'
    arsiv = zip_yap({"a/valid_300.jsonl": valid, "b/valid_300.jsonl": valid})
    monkeypatch.setattr(ind, "V6_VALID_SHA256", sha(valid))
    monkeypatch.setattr(ind, "V6_VALID_SATIR", 1)

    with pytest.raises(ValueError, match="tam bir valid_300"):
        ind.v6_valid_ayikla(arsiv)


def test_v4_gzip_hash_ve_satir_sayisi_dogrulanir(monkeypatch):
    ham = b'{"id":"sentetik"}\n'
    monkeypatch.setattr(ind, "V4_HAM_SHA256", sha(ham))
    monkeypatch.setattr(ind, "V4_SATIR", 1)
    assert ind.v4_validation_ac(gzip.compress(ham)) == ham

    monkeypatch.setattr(ind, "V4_HAM_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="v4 validation SHA-256"):
        ind.v4_validation_ac(gzip.compress(ham))


def test_cikti_repo_ici_reddedilir(tmp_path):
    kok = tmp_path / "repo"
    kok.mkdir()
    with pytest.raises(ValueError, match="depo dışında"):
        ind.repo_disinda(kok / "exports", kok)


def test_var_olan_cikti_dizini_uzerine_yazilmaz(monkeypatch, tmp_path):
    kok = tmp_path / "repo"
    kok.mkdir()
    monkeypatch.setattr(ind, "KOK", kok)
    hedef = tmp_path / "validation-artifacts"
    hedef.mkdir()
    (hedef / "keep.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="zaten var"):
        ind.indir_dogrulama(hedef)

    assert (hedef / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_atomik_yayin_bos_hedef_dizinini_degistirmez(tmp_path):
    kaynak = tmp_path / "staging"
    kaynak.mkdir()
    (kaynak / "new.txt").write_text("new", encoding="utf-8")
    hedef = tmp_path / "hedef"
    hedef.mkdir()

    with pytest.raises(FileExistsError):
        ind.atomik_yeniden_adlandir(kaynak, hedef)

    assert list(hedef.iterdir()) == []
    assert (kaynak / "new.txt").read_text(encoding="utf-8") == "new"


def test_indir_boyut_tavanini_asinca_durdurur(monkeypatch):
    class Yanit:
        def __init__(self):
            self._parcalar = [b"1234", b"5678", b""]

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, _boyut):
            return self._parcalar.pop(0)

    monkeypatch.setattr(ind.urllib.request, "urlopen", lambda *_args, **_kwargs: Yanit())

    with pytest.raises(ValueError, match="boyut sınırını"):
        ind.indir("https://example.invalid/data", 6)


def test_kontrol_sirasinda_bos_hedef_olusturulursa_uzerine_yazilmaz(monkeypatch, tmp_path):
    valid = b'{"id":"sentetik"}\n'
    ham = b'{"id":"raw-sentetik"}\n'
    arsiv = zip_yap({"valid_300.jsonl": valid})
    sikistirilmis = gzip.compress(ham)
    monkeypatch.setattr(ind, "KOK", tmp_path / "repo")
    monkeypatch.setattr(ind, "V6_ARSIV_SHA256", sha(arsiv))
    monkeypatch.setattr(ind, "V6_VALID_SHA256", sha(valid))
    monkeypatch.setattr(ind, "V6_VALID_SATIR", 1)
    monkeypatch.setattr(ind, "V4_HAM_SHA256", sha(ham))
    monkeypatch.setattr(ind, "V4_SATIR", 1)
    monkeypatch.setattr(ind, "indir", lambda url, _tavan: arsiv if url == ind.V6_URL else sikistirilmis)

    asil_yayin = ind.atomik_yeniden_adlandir
    hedef = tmp_path / "validation-artifacts"

    def hedefi_kontrol_sonrasi_olustur(kaynak, hedef_yolu):
        assert hedef_yolu == hedef
        hedef_yolu.mkdir()
        asil_yayin(kaynak, hedef_yolu)

    monkeypatch.setattr(ind, "atomik_yeniden_adlandir", hedefi_kontrol_sonrasi_olustur)

    with pytest.raises(FileExistsError):
        ind.indir_dogrulama(hedef)

    assert hedef.is_dir()
    assert list(hedef.iterdir()) == []
    assert list(tmp_path.glob(".validation-artifacts.*")) == []
