#!/usr/bin/env python3
"""Bottom-up sözcüksel tanılama için sabit validation kümesi üzerinde eşli proje bootstrap'i."""

import argparse
import hashlib
import json
import math
import random
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

KOK = Path(__file__).resolve().parent
DOGRULAMA_SATIRI = 300
VARSAYILAN_TEKRAR = 2000
VARSAYILAN_TOHUM = 42
OLCUT = "macro_token_recall"
KARSILASTIRMALAR = (
    ("gold_minus_anonymised_macro_token_recall", "gold", "anonymised"),
    ("coverage_matched_gold_minus_anonymised_macro_token_recall", "gold_prediction_coverage", "anonymised"),
    ("v5_predicted_minus_anonymised_macro_token_recall", "v5_predicted", "anonymised"),
    ("coverage_matched_gold_minus_v5_predicted_macro_token_recall", "gold_prediction_coverage", "v5_predicted"),
    ("gold_minus_coverage_matched_gold_macro_token_recall", "gold", "gold_prediction_coverage"),
)
KIPLER = ("anonymised", "gold", "v5_predicted", "gold_prediction_coverage")


def sha256(yol: Path) -> str:
    ozet = hashlib.sha256()
    with yol.open("rb") as akim:
        for parca in iter(lambda: akim.read(1024 * 1024), b""):
            ozet.update(parca)
    return ozet.hexdigest()


def _json_nesnesi(yol: Path, etiket: str) -> Dict[str, object]:
    try:
        deger = json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError(etiket + " manifesti veya özeti eksik ya da geçersiz") from None
    if not isinstance(deger, dict):
        raise ValueError(etiket + " bir JSON nesnesi olmalı")
    return deger


def _hash_dogrula(deger: object, etiket: str) -> str:
    if not isinstance(deger, str) or not re.fullmatch(r"[0-9a-f]{64}", deger):
        raise ValueError(etiket + " geçerli bir SHA-256 özeti değil")
    return deger


def beklenen_dogrulama_hashleri(kok: Optional[Path] = None) -> Dict[str, str]:
    kok = kok or KOK
    v6 = _json_nesnesi(kok / "lora" / "v6_girdi_manifest.json", "v6")
    denetim = _json_nesnesi(kok / "rapor" / "arastirma" / "dogrulama_manifest.json", "validation")
    try:
        hashler = {
            "prompts": v6["beklenen_sha256"]["valid_v6"],
            "raw": denetim["tam_dogrulama_sha256"],
            "predictions": denetim["dondurulmus_tahminler"]["v5"],
        }
    except (KeyError, TypeError):
        raise ValueError("depo manifestleri gerekli validation girdilerini sabitlemiyor") from None
    return {ad: _hash_dogrula(deger, ad) for ad, deger in hashler.items()}


def _audit_commit_dogrula(commit: str, kok: Optional[Path] = None) -> str:
    kok = kok or KOK
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("audit commit tam 40 karakterli küçük harfli SHA olmalı")
    try:
        cozum = subprocess.check_output(
            ["git", "rev-parse", "--verify", commit + "^{commit}"],
            cwd=kok,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        head = subprocess.check_output(
            ["git", "rev-parse", "--verify", "HEAD^{commit}"],
            cwd=kok,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        durum = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=kok,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        subprocess.run(
            ["git", "cat-file", "-e", cozum + ":alttan_yukari_sim.py"],
            cwd=kok,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        raise ValueError("audit commit depoda bulunmalı ve alttan_yukari_sim.py içermeli") from None
    if cozum != head:
        raise ValueError("audit commit mevcut HEAD ile eşleşmeli")
    if durum:
        raise ValueError("audit için takipli çalışma ağacı temiz olmalı")
    return cozum


def _dayanak_dogrula(ozet: Mapping[str, object], beklenen: Mapping[str, str]) -> Dict[str, str]:
    dayanak = ozet.get("provenance")
    if not isinstance(dayanak, dict):
        raise ValueError("özette girdi dayanağı yok")
    istem_hash = dayanak.get("prompts_sha256")
    tahmin_hash = dayanak.get("predictions_sha256")
    ham_hashler = dayanak.get("raw_sha256")
    if istem_hash != beklenen["prompts"]:
        raise ValueError("özet sabit v6 validation istemleriyle eşleşmiyor")
    if tahmin_hash != beklenen["predictions"]:
        raise ValueError("özet sabit v5 validation tahminleriyle eşleşmiyor")
    if not isinstance(ham_hashler, dict) or len(ham_hashler) != 1:
        raise ValueError("özet tam olarak bir ham validation dosyası tanımlamalı")
    if next(iter(ham_hashler.values())) != beklenen["raw"]:
        raise ValueError("özet sabit v4 validation verisiyle eşleşmiyor")
    return {
        "prompts_sha256": beklenen["prompts"],
        "raw_sha256": beklenen["raw"],
        "predictions_sha256": beklenen["predictions"],
    }


def _sonlu_oran(deger: object, etiket: str) -> float:
    if isinstance(deger, bool) or not isinstance(deger, (int, float)):
        raise ValueError(etiket + " sonlu bir sayı olmalı")
    sonuc = float(deger)
    if not math.isfinite(sonuc) or not 0.0 <= sonuc <= 1.0:
        raise ValueError(etiket + " 0 ile 1 arasında olmalı")
    return sonuc


def proje_degerleri(ozet: Mapping[str, object]) -> Tuple[Dict[str, Dict[str, float]], int]:
    kip_ozetleri = ozet.get("modes")
    projeler = ozet.get("projects")
    if not isinstance(kip_ozetleri, dict) or not isinstance(projeler, dict):
        raise ValueError("özet kipleri ve proje bazlı toplulaştırmaları içermeli")

    proje_kumeleri = []
    for kip in KIPLER:
        kip_projeleri = projeler.get(kip)
        kip_ozeti = kip_ozetleri.get(kip)
        if not isinstance(kip_projeleri, dict) or not isinstance(kip_ozeti, dict):
            raise ValueError("özette gerekli kip eksik: " + kip)
        if kip_ozeti.get("rows") != DOGRULAMA_SATIRI:
            raise ValueError("kip satır sayısı sabit 300 satırlık validation kümesi değil")
        proje_kumeleri.append(set(kip_projeleri))

    if not proje_kumeleri[0] or any(kume != proje_kumeleri[0] for kume in proje_kumeleri[1:]):
        raise ValueError("eşli kipler arasında proje kümeleri farklı")
    if len(proje_kumeleri[0]) < 2:
        raise ValueError("en az iki proje kümesi gerekli")

    degerler: Dict[str, Dict[str, float]] = {}
    toplam_satir = 0
    for proje in sorted(proje_kumeleri[0]):
        if not isinstance(proje, str) or not proje:
            raise ValueError("toplu özette geçersiz proje anahtarı")
        kume: Dict[str, float] = {}
        satir_sayisi = None
        for kip in KIPLER:
            metrikler = projeler[kip][proje]
            if not isinstance(metrikler, dict):
                raise ValueError("geçersiz proje toplulaştırması")
            satir = metrikler.get("rows")
            if isinstance(satir, bool) or not isinstance(satir, int) or satir <= 0:
                raise ValueError("proje satır sayısı pozitif bir tamsayı olmalı")
            if satir_sayisi is None:
                satir_sayisi = satir
            elif satir_sayisi != satir:
                raise ValueError("eşli kiplerde proje satır sayıları farklı")
            kume[kip] = _sonlu_oran(metrikler.get(OLCUT), kip + "." + OLCUT)
        kume["rows"] = float(satir_sayisi)
        degerler[proje] = kume
        toplam_satir += satir_sayisi

    if toplam_satir != DOGRULAMA_SATIRI:
        raise ValueError("proje toplulaştırmaları sabit validation kümesindeki 300 satıra eşit değil")
    if ozet.get("prediction_rows") != DOGRULAMA_SATIRI:
        raise ValueError("tahmin satır sayısı sabit 300 satırlık validation kümesi değil")
    return degerler, toplam_satir


def _kantil(sirali: List[float], olasilik: float) -> float:
    konum = (len(sirali) - 1) * olasilik
    alt = int(math.floor(konum))
    ust = int(math.ceil(konum))
    if alt == ust:
        return sirali[alt]
    agirlik = konum - alt
    return sirali[alt] * (1.0 - agirlik) + sirali[ust] * agirlik


def esli_proje_bootstrap(
    degerler: Mapping[str, Mapping[str, float]],
    tekrar: int = VARSAYILAN_TEKRAR,
    tohum: int = VARSAYILAN_TOHUM,
) -> Dict[str, Dict[str, object]]:
    if isinstance(tekrar, bool) or not isinstance(tekrar, int) or tekrar < 100:
        raise ValueError("bootstrap tekrarı en az 100 tamsayı olmalı")
    if isinstance(tohum, bool) or not isinstance(tohum, int):
        raise ValueError("bootstrap tohumu tamsayı olmalı")
    projeler = sorted(degerler)
    if len(projeler) < 2:
        raise ValueError("en az iki proje kümesi gerekli")

    toplam_satir = sum(int(degerler[proje]["rows"]) for proje in projeler)
    tahminler = {}
    ornekler = {ad: [] for ad, _, _ in KARSILASTIRMALAR}
    for ad, sol, sag in KARSILASTIRMALAR:
        tahminler[ad] = (
            sum(int(degerler[proje]["rows"]) * (degerler[proje][sol] - degerler[proje][sag]) for proje in projeler)
            / toplam_satir
        )

    uretic = random.Random(tohum)
    for _ in range(tekrar):
        secilen = [uretic.choice(projeler) for _ in projeler]
        payda = sum(int(degerler[proje]["rows"]) for proje in secilen)
        for ad, sol, sag in KARSILASTIRMALAR:
            pay = sum(int(degerler[proje]["rows"]) * (degerler[proje][sol] - degerler[proje][sag]) for proje in secilen)
            ornekler[ad].append(pay / payda)

    sonuc = {}
    for ad, _, _ in KARSILASTIRMALAR:
        sirali = sorted(ornekler[ad])
        sonuc[ad] = {
            "estimate": round(tahminler[ad], 9),
            "ci95": [round(_kantil(sirali, 0.025), 9), round(_kantil(sirali, 0.975), 9)],
            "n_projects": len(projeler),
            "n_rows": toplam_satir,
        }
    return sonuc


def rapor_olustur(
    ozet_yolu: Path,
    ozet: Mapping[str, object],
    audit_commit: str,
    tekrar: int = VARSAYILAN_TEKRAR,
    tohum: int = VARSAYILAN_TOHUM,
) -> Dict[str, object]:
    audit_commit = _audit_commit_dogrula(audit_commit)
    audit_tree = subprocess.check_output(
        ["git", "rev-parse", "--verify", audit_commit + "^{tree}"],
        cwd=KOK,
        stderr=subprocess.DEVNULL,
        text=True,
    ).strip()
    audit_simulator_sha256 = sha256(KOK / "alttan_yukari_sim.py")
    beklenen = beklenen_dogrulama_hashleri()
    girdi_hashleri = _dayanak_dogrula(ozet, beklenen)
    degerler, toplam_satir = proje_degerleri(ozet)
    karsilastirmalar = esli_proje_bootstrap(degerler, tekrar=tekrar, tohum=tohum)
    return {
        "schema": 1,
        "scope": "fixed validation-only valid300; no test/eval scoring",
        "interpretation": "Lexical information availability only; not model F1 or a causal naming gain.",
        "method": "paired project-cluster percentile bootstrap with linear-interpolated 95% intervals",
        "resampling_unit": "project",
        "weighting": "row-weighted macro token recall; all rows in each sampled project stay together",
        "replicates": tekrar,
        "seed": tohum,
        "confidence_level": 0.95,
        "n_projects": len(degerler),
        "n_rows": toplam_satir,
        "audit_commit": audit_commit,
        "audit_tree": audit_tree,
        "audit_simulator_sha256": audit_simulator_sha256,
        "audit_provenance": "clean_tracked_head_operator_attestation",
        "summary_sha256": sha256(ozet_yolu),
        "validation_inputs": girdi_hashleri,
        "comparisons": karsilastirmalar,
    }


def depo_icinde(yol: Path, kok: Optional[Path] = None) -> bool:
    kok = kok or KOK
    try:
        yol.resolve().relative_to(kok.resolve())
    except ValueError:
        return False
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ozet", required=True, type=Path, help="alttan_yukari_sim.py toplu çıktısı")
    parser.add_argument("--cikti", required=True, type=Path, help="depo dışında yeni toplu JSON yolu")
    parser.add_argument("--audit-commit", required=True, help="alttan_yukari_sim.py çalıştırmasında kullanılan commit")
    parser.add_argument("--tekrar", type=int, default=VARSAYILAN_TEKRAR)
    parser.add_argument("--tohum", type=int, default=VARSAYILAN_TOHUM)
    args = parser.parse_args(argv)

    try:
        if not args.ozet.is_file():
            raise ValueError("özet tek bir toplu JSON dosyası olmalı")
        if depo_icinde(args.cikti):
            raise ValueError("toplu çıktı depo dışında olmalı")
        if args.cikti.exists():
            raise FileExistsError("çıktı zaten var; üzerine yazılmayacak")
        ozet = _json_nesnesi(args.ozet, "Özet")
        rapor = rapor_olustur(args.ozet, ozet, audit_commit=args.audit_commit, tekrar=args.tekrar, tohum=args.tohum)
        args.cikti.parent.mkdir(parents=True, exist_ok=True)
        with args.cikti.open("x", encoding="utf-8") as akim:
            json.dump(rapor, akim, ensure_ascii=False, indent=2, allow_nan=False)
            akim.write("\n")
    except (OSError, ValueError) as hata:
        parser.exit(2, "HATA: " + str(hata) + "\n")

    print(json.dumps(rapor, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
