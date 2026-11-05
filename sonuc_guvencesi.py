"""Yeni sonuç JSONL dosyalarında satır düzeyinde veri sızıntısını engeller."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Optional


SATIR_DUZEYI_ALANLARI = frozenset(
    {
        "id",
        "gercek",
        "gercek_ad",
        "tahmin",
        "asm",
        "assembly",
        "source",
        "kaynak",
        "anahtar",
        "gerekce_en",
        "gerekce_tr",
        "puan_en",
        "puan_tr",
        "ogretmen",
        "proje",
        "project",
        "opt",
        "token",
        "aciklama",
        "aciklama_en",
        "function",
        "function_name",
        "function_id",
        "address",
        "target",
        "prediction",
        "gold",
        "prompt",
        "completion",
        "decompile",
        "pseudocode",
    }
)


def sonuc_jsonl_mi(yol: str) -> bool:
    """sonuc/ altındaki JSONL sonuç dosyalarını seçer."""
    parca = PurePosixPath(yol)
    return len(parca.parts) >= 2 and parca.parts[0] == "sonuc" and parca.suffix.lower() == ".jsonl"


def satir_duzeyi_alan_var(kayit: object) -> bool:
    """Satır düzeyindeki alanları iç içe nesne/listelerde de bulur."""
    if isinstance(kayit, dict):
        anahtarlar = {alan.casefold() for alan in kayit if isinstance(alan, str)}
        if anahtarlar & SATIR_DUZEYI_ALANLARI:
            return True
        return any(satir_duzeyi_alan_var(deger) for deger in kayit.values())
    if isinstance(kayit, list):
        return any(satir_duzeyi_alan_var(deger) for deger in kayit)
    return False


def jsonl_denetle(yol: str, icerik: str) -> list[str]:
    """Sonuç JSONL içeriğinde satır düzeyinde veri alanları taşıyan kayıtları reddeder."""
    if not sonuc_jsonl_mi(yol):
        return []

    hatalar = []
    for satir_no, satir in enumerate(icerik.splitlines(), start=1):
        if not satir.strip():
            continue
        try:
            kayit = json.loads(satir)
        except json.JSONDecodeError:
            hatalar.append(f"{yol}:{satir_no}: geçersiz JSONL satırı; denetim kapalı kalır.")
            continue
        if not isinstance(kayit, dict):
            hatalar.append(f"{yol}:{satir_no}: JSONL kaydı nesne olmalı.")
            continue
        if satir_duzeyi_alan_var(kayit):
            hatalar.append(f"{yol}:{satir_no}: satır düzeyinde kimlik, ad, tahmin veya kaynak içeren sonuç yasak.")
    return hatalar


def degisen_dosyalar(taban: str, bas: str) -> list[str]:
    """İki Git revizyonu arasında eklenen/değişen sonuç JSONL dosyalarını döndürür."""
    sonuc = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMRT",
            taban,
            bas,
            "--",
            "sonuc/*.jsonl",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return [yol for yol in sonuc.stdout.splitlines() if sonuc_jsonl_mi(yol)]


def git_denetle(taban: str, bas: str, kok: Optional[Path] = None) -> tuple[list[str], int]:
    """Yalnız değişen sonuç dosyalarını denetler; eski arşivleri yeniden yazmaz."""
    kok = kok or Path.cwd()
    dosyalar = degisen_dosyalar(taban, bas)
    hatalar = []
    for yol in dosyalar:
        yol_dosya = kok / yol
        if not yol_dosya.is_file():
            continue
        try:
            icerik = yol_dosya.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            hatalar.append(f"{yol}: UTF-8 olmayan sonuç JSONL dosyası.")
            continue
        hatalar.extend(jsonl_denetle(yol, icerik))
    return hatalar, len(dosyalar)


def main() -> int:
    ayr = argparse.ArgumentParser(description=__doc__)
    ayr.add_argument("--base", required=True, help="Karşılaştırmanın taban Git revizyonu")
    ayr.add_argument("--head", required=True, help="Karşılaştırmanın baş Git revizyonu")
    args = ayr.parse_args()
    try:
        hatalar, sayi = git_denetle(args.base, args.head)
    except subprocess.CalledProcessError as hata:
        print(f"Git değişiklik listesi alınamadı: {hata.stderr.strip()}", file=sys.stderr)
        return 2
    if hatalar:
        print("\n".join(hatalar), file=sys.stderr)
        return 1
    print(f"Sonuç güvencesi geçti: {sayi} değişen sonuç JSONL dosyası denetlendi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
