#!/usr/bin/env python3
"""Eğitilmemiş Qwen3-8B tabanını v6 ve v1 ile eşli karşılaştır (molab/TABAN_PROTOKOL.md).

python3 olcum_taban.py --veri ../asm-v6/lora/veri-v6 -o sonuc/olcum-taban.json
"""

import argparse
import json
import math
from pathlib import Path

from aciklama_degerlendir import bootstrap_farki
from olcum_v6 import eslestir, iz, oku, ozet

KOK = Path(__file__).resolve().parent
BOLUMLER = {"test_sabit": 2000, "eval115": 115}
DOSYALAR = {
    "taban": {"test_sabit": "sonuc/test2000-qwen3-8b-base.jsonl", "eval115": "sonuc/eval115-qwen3-8b-base.jsonl"},
    "v6": {
        "test_sabit": ".notlar/v6/hf-final/test_sabit-sonuc.jsonl",
        "eval115": ".notlar/v6/hf-final/eval115-sonuc.jsonl",
    },
    "v1": {"test_sabit": "sonuc/test2000-molab-qwen3-8b.jsonl", "eval115": "sonuc/eval115-molab-qwen3-8b.jsonl"},
}
# Sistem istemindeki örnek JSON: {"aciklama_en": "Reads a record from the stream.", "ad": "read_record", ...}
ORNEK_AD, ORNEK_EN = "read_record", "Reads a record from the stream."


def kopya(r):
    return {
        "ad_ornek": r["tahmin"] == ORNEK_AD,
        "ad_ornek_iceren": ORNEK_AD in r["tahmin"],
        "aciklama_ornek": (r.get("aciklama_en") or "").strip() == ORNEK_EN,
    }


def rapor(veri_dizin, tekrar=2000, tohum=42):
    sonuc = {
        "surum": "taban-olcum-1",
        "protokol": "molab/TABAN_PROTOKOL.md",
        "bootstrap_tekrar": tekrar,
        "bootstrap_tohum": tohum,
        "girdiler": {},
        "bolumler": {},
    }
    for bolum, n in BOLUMLER.items():
        veri_yol = Path(veri_dizin, bolum + ".jsonl")
        veri = oku(veri_yol)
        yollar = {k: KOK / v[bolum] for k, v in DOSYALAR.items()}
        satir = {k: oku(y) for k, y in yollar.items()}
        b = {}
        for model in ("v6", "v1"):
            # eslestir(veri, aday, karsi): "f1" adayın, "v5_f1" karşının skoru; burada karşı = taban.
            rows = eslestir(veri, satir[model], satir["taban"], n)
            s = ozet(rows)
            s = {
                "n": s["n"],
                "model_f1": s["f1"],
                "taban_f1": s["v5_f1"],
                "fark": s["fark"],
                "model_oneksiz_f1": s["oneksiz_f1"],
                "taban_oneksiz_f1": s["v5_oneksiz_f1"],
            }
            s.update(
                bootstrap_farki(
                    [r["f1"] for r in rows], [r["v5_f1"] for r in rows], [r["proje"] for r in rows], tohum, tekrar
                )
            )
            b[f"{model}_eksi_taban"] = s
        # Taban kendi başına: v6 ile aynı metrikler.
        t_rows = eslestir(veri, satir["taban"], satir["taban"], n)
        t = ozet(t_rows)
        tr = satir["taban"]
        kati = [r["f1"] if tr[r["id"]]["gecerli_json"] else 0.0 for r in t_rows]
        b["taban"] = {
            "n": n,
            "f1": t["f1"],
            "f1_kati": math.fsum(kati) / n,
            "oneksiz_f1": t["oneksiz_f1"],
            "tam_isabet": t["tam_isabet"],
            "f1_tam_isabet": t["f1_tam_isabet"],
            "oneksiz_f1_tam_isabet": t["oneksiz_f1_tam_isabet"],
            "kayitli_f1_uyumsuz": t["kayitli_f1_uyumsuz"],
            "gecerli_json_orani": sum(r["gecerli_json"] for r in tr.values()) / n,
            "sinira_dayanan_orani": sum(r["sinira_dayandi"] for r in tr.values()) / n,
            "opt": {o: ozet([r for r in t_rows if r["opt"] == o])["f1"] for o in sorted({r["opt"] for r in t_rows})},
        }
        for model in ("taban", "v6", "v1"):
            k = [kopya(r) for r in satir[model].values()]
            b.setdefault("istem_ornegi_kopyasi", {})[model] = {a: sum(x[a] for x in k) for a in k[0]}
        sonuc["girdiler"][bolum] = {"veri": iz(veri_yol), **{k: iz(y) for k, y in yollar.items()}}
        sonuc["bolumler"][bolum] = b
    return sonuc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--veri", type=Path, required=True)
    ap.add_argument("-o", "--cikti", type=Path)
    a = ap.parse_args()
    metin = json.dumps(rapor(a.veri), ensure_ascii=False, indent=2)
    if a.cikti:
        a.cikti.write_text(metin + "\n", encoding="utf-8")
    print(metin)


if __name__ == "__main__":
    main()
