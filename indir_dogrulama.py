#!/usr/bin/env python3
"""Bottom-up doğrulama deneyi için yalnız üç sabit validation girdisini indir."""

import argparse
import ctypes
import errno
import gzip
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Dict, Optional

KOK = Path(__file__).resolve().parent

V6_URL = "https://github.com/krxi/asmsense-data/releases/download/v6/veri-v6.zip"
V6_ARSIV_SHA256 = "e1286104e59860a34fc18fe908ccadc3896b4db40fe1a5a75253aa9cc7a8c201"
V6_VALID_SHA256 = "1148a533d05b044624e99d5a74dc43f6b481523dda61e8fbfc4f93ff77010256"
V6_VALID_SATIR = 300
V6_ARSIV_TAVAN = 100 * 1024 * 1024
V6_VALID_TAVAN = 16 * 1024 * 1024

V4_REVIZYON = "6e1eb5e44c3114a06c0b4cac9b38540c33e322e0"
V4_URL = (
    "https://huggingface.co/datasets/krxi123/asmsense/resolve/" + V4_REVIZYON + "/data/v4/validation-00000.jsonl.gz"
)
V4_HAM_SHA256 = "7516244ec1798b05f6c3ef09fbfb4636241b5dd6bbfd8b6814ad340b6f1beef3"
V4_SATIR = 19770
V4_GZIP_TAVAN = 8 * 1024 * 1024
V4_HAM_TAVAN = 128 * 1024 * 1024

V5_KAYNAK_COMMIT = "15e3b28f1be387d0e8655edd838e1c32f9d348d5"
V5_TAHMIN_URL = "https://raw.githubusercontent.com/krxi/asmsense/" + V5_KAYNAK_COMMIT + "/sonuc/valid300-molab-qwen3-8b-v5.jsonl"
V5_TAHMIN_SHA256 = "88f7bfb32ed87f5c43a43d670c5ca5e80bfd00c3592d59dc24b9ee52e14e4faf"
V5_TAHMIN_SATIR = 300
V5_TAHMIN_TAVAN = 16 * 1024 * 1024


def sha256(veri: bytes) -> str:
    return hashlib.sha256(veri).hexdigest()


def satir_sayisi(veri: bytes) -> int:
    return sum(1 for satir in veri.splitlines() if satir.strip())


def repo_disinda(yol: Path, kok: Optional[Path] = None) -> Path:
    kok = (kok or KOK).resolve()
    hedef = Path(yol).expanduser().resolve()
    if hedef == kok or kok in hedef.parents:
        raise ValueError("Validation artefaktları depo dışında tutulmalı")
    return hedef


def indir(url: str, tavan: int) -> bytes:
    istek = urllib.request.Request(url, headers={"User-Agent": "asmsense-validation-fetch/1.0"})
    parcalar = []
    toplam = 0
    with urllib.request.urlopen(istek, timeout=60) as yanit:
        while True:
            parca = yanit.read(1024 * 1024)
            if not parca:
                break
            toplam += len(parca)
            if toplam > tavan:
                raise ValueError("İndirilen dosya boyut sınırını aşıyor")
            parcalar.append(parca)
    return b"".join(parcalar)


def v6_valid_ayikla(arsiv: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(arsiv)) as paket:
        adaylar = [
            bilgi
            for bilgi in paket.infolist()
            if not bilgi.is_dir() and PurePosixPath(bilgi.filename).name == "valid_300.jsonl"
        ]
        if len(adaylar) != 1:
            raise ValueError("v6 arşivinde tam bir valid_300.jsonl bulunmalı")
        bilgi = adaylar[0]
        if bilgi.file_size > V6_VALID_TAVAN:
            raise ValueError("v6 valid_300 boyut sınırını aşıyor")
        with paket.open(bilgi, "r") as dosya:
            veri = dosya.read(V6_VALID_TAVAN + 1)
    if len(veri) > V6_VALID_TAVAN or len(veri) != bilgi.file_size:
        raise ValueError("v6 valid_300 eksik veya boyut sınırını aşıyor")
    if sha256(veri) != V6_VALID_SHA256:
        raise ValueError("v6 valid_300 SHA-256 sabit manifestle uyuşmuyor")
    if satir_sayisi(veri) != V6_VALID_SATIR:
        raise ValueError("v6 valid_300 satır sayısı 300 değil")
    return veri


def v4_validation_ac(gzip_veri: bytes) -> bytes:
    with gzip.GzipFile(fileobj=io.BytesIO(gzip_veri), mode="rb") as dosya:
        ham = dosya.read(V4_HAM_TAVAN + 1)
    if len(ham) > V4_HAM_TAVAN:
        raise ValueError("v4 validation açılmış boyut sınırını aşıyor")
    if sha256(ham) != V4_HAM_SHA256:
        raise ValueError("v4 validation SHA-256 sabit manifestle uyuşmuyor")
    if satir_sayisi(ham) != V4_SATIR:
        raise ValueError("v4 validation satır sayısı 19.770 değil")
    return ham


def v5_tahminleri_dogrula(veri: bytes) -> bytes:
    if len(veri) > V5_TAHMIN_TAVAN:
        raise ValueError("v5 valid300 tahmin dosyası boyut sınırını aşıyor")
    if sha256(veri) != V5_TAHMIN_SHA256:
        raise ValueError("v5 valid300 tahmin SHA-256 sabit manifestle uyuşmuyor")
    if satir_sayisi(veri) != V5_TAHMIN_SATIR:
        raise ValueError("v5 valid300 tahmin satır sayısı sabit manifestle uyuşmuyor")
    return veri


def ozel_yaz(yol: Path, veri: bytes) -> None:
    fd = os.open(str(yol), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as dosya:
        dosya.write(veri)
        dosya.flush()
        os.fsync(dosya.fileno())


def atomik_yeniden_adlandir(kaynak: Path, hedef: Path) -> None:
    """Hedef varsa onu değiştirmeden staging dizinini yayımla."""
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform.startswith("linux"):
        fonksiyon = getattr(libc, "renameat2", None)
        if fonksiyon is None:
            raise OSError(errno.ENOTSUP, "renameat2 desteklenmiyor", str(hedef))
        fonksiyon.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        fonksiyon.restype = ctypes.c_int
        sonuc = fonksiyon(-100, os.fsencode(kaynak), -100, os.fsencode(hedef), 0x00000001)
    elif sys.platform == "darwin":
        fonksiyon = getattr(libc, "renamex_np", None)
        if fonksiyon is None:
            raise OSError(errno.ENOTSUP, "renamex_np desteklenmiyor", str(hedef))
        fonksiyon.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        fonksiyon.restype = ctypes.c_int
        sonuc = fonksiyon(os.fsencode(kaynak), os.fsencode(hedef), 0x00000004)
    else:
        raise OSError(errno.ENOTSUP, "Atomik no-clobber yayın bu platformda desteklenmiyor", str(hedef))

    if sonuc != 0:
        hata = ctypes.get_errno()
        if hata in (errno.EEXIST, errno.ENOTEMPTY):
            raise FileExistsError(hata, os.strerror(hata), str(hedef))
        raise OSError(hata, os.strerror(hata), str(hedef))


def indir_dogrulama(cikti_dir: Path) -> Dict[str, object]:
    hedef = repo_disinda(cikti_dir)
    if hedef.exists():
        raise FileExistsError("Çıktı dizini zaten var; üzerine yazılmayacak")

    # Tam v6 ZIP yalnızca doğrulanmış valid_300 üyesini okumak için geçici tutulur.
    v6_arsiv = indir(V6_URL, V6_ARSIV_TAVAN)
    if sha256(v6_arsiv) != V6_ARSIV_SHA256:
        raise ValueError("v6 arşiv SHA-256 GitHub release kaydıyla uyuşmuyor")
    valid = v6_valid_ayikla(v6_arsiv)
    del v6_arsiv

    v4_gzip = indir(V4_URL, V4_GZIP_TAVAN)
    ham = v4_validation_ac(v4_gzip)
    del v4_gzip

    v5_tahminleri = v5_tahminleri_dogrula(indir(V5_TAHMIN_URL, V5_TAHMIN_TAVAN))

    hedef.parent.mkdir(parents=True, exist_ok=True)
    gecici = Path(tempfile.mkdtemp(prefix="." + hedef.name + ".", dir=str(hedef.parent)))
    try:
        ozel_yaz(gecici / "valid_300-v6.jsonl", valid)
        ozel_yaz(gecici / "validation-v4.jsonl", ham)
        ozel_yaz(gecici / "valid300-v5-predictions.jsonl", v5_tahminleri)
        manifest = {
            "sema": 1,
            "bolum": "valid300",
            "kaynaklar": {
                "v6_arsiv_sha256": V6_ARSIV_SHA256,
                "v4_hf_rev": V4_REVIZYON,
                "v4_ham_sha256": V4_HAM_SHA256,
                "v5_kaynak_commit": V5_KAYNAK_COMMIT,
                "v5_tahmin_sha256": V5_TAHMIN_SHA256,
            },
            "artefaktlar": {
                "valid_300-v6.jsonl": {"satir": V6_VALID_SATIR, "sha256": sha256(valid)},
                "validation-v4.jsonl": {"satir": V4_SATIR, "sha256": sha256(ham)},
                "valid300-v5-predictions.jsonl": {
                    "satir": V5_TAHMIN_SATIR,
                    "sha256": sha256(v5_tahminleri),
                },
            },
            "test_uyesi_acildi": 0,
            "gpu": "not used",
            "model_cagrisi": "not run",
        }
        ozel_yaz(
            gecici / "manifest.json",
            (json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"),
        )
        # Ön kontrol tek başına yarış koşulunu kapatmaz: hedef boş dizin olarak
        # bu arada oluşturulabilir. Platformun no-replace rename işlemi atomiktir.
        atomik_yeniden_adlandir(gecici, hedef)
    except Exception:
        shutil.rmtree(gecici, ignore_errors=True)
        raise
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cikti-dir", type=Path, required=True, help="depo dışında yeni bir dizin")
    args = parser.parse_args(argv)
    try:
        sonuc = indir_dogrulama(args.cikti_dir)
    except (OSError, ValueError, urllib.error.URLError, zipfile.BadZipFile, EOFError) as hata:
        parser.exit(2, "HATA: " + str(hata) + "\n")
    print(json.dumps(sonuc, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
