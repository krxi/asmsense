"""İzlenen sonuç JSONL dosyalarını değerleri göstermeden şema düzeyinde sayar."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

from sonuc_guvencesi import satir_duzeyi_alan_var

TOPLU_ALANLARI = frozenset(
    {
        "adim",
        "epoch",
        "step",
        "eval_loss",
        "loss",
        "f1",
        "gecerli_json_orani",
        "model",
        "n",
        "split",
        "timestamp",
        "duration_s",
    }
)

TOPLU_ANKORLARI = frozenset({"adim", "epoch", "step", "n"})


def _git(kok: Path, *args: str) -> str:
    sonuc = subprocess.run(
        ["git", *args],
        cwd=kok,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return sonuc.stdout


def _siniflandir(icerik: str) -> str:
    """Bir dosyayı yalnız anahtar kümelerine göre sınıflandırır; değerleri döndürmez."""
    anahtarlar = set()
    satir_duzeyi = False
    bozuk = False
    kayit_var = False

    for satir in icerik.splitlines():
        if not satir.strip():
            continue
        kayit_var = True
        try:
            kayit = json.loads(satir)
        except json.JSONDecodeError:
            bozuk = True
            continue
        if not isinstance(kayit, dict):
            bozuk = True
            continue

        anahtarlar.update(kayit)
        if satir_duzeyi_alan_var(kayit):
            satir_duzeyi = True

    if satir_duzeyi:
        return "satir_duzeyi"
    if bozuk or not kayit_var:
        return "belirsiz"
    if anahtarlar and anahtarlar <= TOPLU_ALANLARI and anahtarlar & TOPLU_ANKORLARI:
        return "toplu"
    return "belirsiz"


def envanteri_uret(ref: str, kok: Optional[Path] = None) -> Dict[str, int]:
    """Bir Git commit'indeki sonuc/*.jsonl dosyalarını değerleri açığa çıkarmadan sayar."""
    if not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
        raise ValueError("--ref tam bir Git commit SHA olmalı.")

    kok = kok or Path.cwd()
    yollar = [
        yol
        for yol in _git(kok, "ls-tree", "-r", "--name-only", ref, "--", "sonuc").splitlines()
        if yol.startswith("sonuc/") and yol.endswith(".jsonl")
    ]

    sayim = {
        "dosya": len(yollar),
        "satir_duzeyi": 0,
        "toplu": 0,
        "belirsiz": 0,
    }

    for yol in yollar:
        try:
            icerik = _git(kok, "show", f"{ref}:{yol}")
            sinif = _siniflandir(icerik)
        except (subprocess.CalledProcessError, UnicodeDecodeError):
            sinif = "belirsiz"
        sayim[sinif] += 1

    return sayim


def rapor_metni(ref: str, sayim: Dict[str, int]) -> str:
    """Yalnız aggregate sayaçları yazdırır; dosya adları ve satır değerleri yoktur."""
    return (
        "Sonuç JSONL envanteri (yalnız şema sayaçları; satır değerleri yazdırılmaz): "
        f"ref={ref} dosya={sayim['dosya']} satır_düzeyi={sayim['satir_duzeyi']} "
        f"toplu={sayim['toplu']} belirsiz={sayim['belirsiz']}"
    )


def main(argv: Optional[List[str]] = None) -> int:
    ayr = argparse.ArgumentParser(description=__doc__)
    ayr.add_argument("--ref", required=True, help="Denetlenecek commit'in tam SHA değeri")
    ayr.add_argument(
        "--strict",
        action="store_true",
        help="Satır düzeyinde veya sınıflandırılamayan dosya varsa başarısız dön.",
    )
    args = ayr.parse_args(argv)

    try:
        sayim = envanteri_uret(args.ref)
    except (ValueError, subprocess.CalledProcessError) as hata:
        print(f"Sonuç envanteri üretilemedi: {hata}", file=sys.stderr)
        return 2

    print(rapor_metni(args.ref, sayim))
    if args.strict and (sayim["satir_duzeyi"] or sayim["belirsiz"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
