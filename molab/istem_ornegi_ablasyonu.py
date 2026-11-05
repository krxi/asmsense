#!/usr/bin/env python3
"""v6 valid_300 üzerinde sistem istemi örneğinin etkisini ölç; eğitim/test yok."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "lora"))

from aciklama_degerlendir import bootstrap_farki  # noqa: E402
from cikti import ad_ayikla  # noqa: E402
from hazirla import SISTEM_V6  # noqa: E402
from olcum_v6 import oneksiz  # noqa: E402
from taban import f1  # noqa: E402
from v6_dogrulama import sema_dogrula  # noqa: E402

MODEL = "Qwen/Qwen3-8B"
MODEL_REVIZYON = "b968826d9c46dd6066d109eabc6255188de91218"
VERI_SURUMU = "https://github.com/krxi/asmsense-data/releases/tag/v6"
MODEL_KARTI = "https://huggingface.co/Qwen/Qwen3-8B/tree/" + MODEL_REVIZYON
BEKLENEN_N = 300
GIRDI_TAVANI = 3072
URETIM_TAVANI = 160
BOOTSTRAP_TEKRAR = 2000
BOOTSTRAP_TOHUM = 42
ORNEK_ANAHTARLARI = {"aciklama_en", "ad", "aciklama"}
YER_TUTUCU = {
    "aciklama_en": "<tek cümle İngilizce>",
    "ad": "<fonksiyon_adi>",
    "aciklama": "<tek cümle Türkçe>",
}


def sha256(veri: bytes) -> str:
    return hashlib.sha256(veri).hexdigest()


def git_degeri(*argumanlar: str) -> Optional[str]:
    try:
        sonuc = subprocess.run(
            ["git", *argumanlar],
            cwd=KOK,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return sonuc.stdout.strip()


def ornek_araligi(istem: str) -> tuple[int, int, dict]:
    """Sistem istemindeki tek JSON örneğini bul; değerlerini dışarı çıkarma."""
    cozumleyici = json.JSONDecoder()
    bulunan = []
    for eslesme in re.finditer(r"\{", istem):
        try:
            nesne, son = cozumleyici.raw_decode(istem[eslesme.start() :])
        except ValueError:
            continue
        if (
            isinstance(nesne, dict)
            and set(nesne) == ORNEK_ANAHTARLARI
            and all(isinstance(nesne[k], str) for k in ORNEK_ANAHTARLARI)
        ):
            bulunan.append((eslesme.start(), eslesme.start() + son, nesne))
    if len(bulunan) != 1:
        raise ValueError("Sistem isteminde tam bir açıklama/ad JSON örneği bekleniyordu.")
    return bulunan[0]


def orneksiz_istem(istem: str) -> str:
    """Örnek yanıt değerlerini yer tutucuyla değiştir; diğer metne dokunma."""
    bas, son, _ = ornek_araligi(istem)
    yer_tutucu = json.dumps(YER_TUTUCU, ensure_ascii=False)
    return istem[:bas] + yer_tutucu + istem[son:]


def dogrulama_satirlari(icerik: bytes, beklenen_sha: str, beklenen_n: int = BEKLENEN_N) -> list[dict]:
    if sha256(icerik) != beklenen_sha:
        raise ValueError("Girdi, v6 manifestindeki sabit valid_300 SHA-256 değeriyle eşleşmiyor.")
    satirlar = []
    for sira, satir in enumerate(icerik.decode("utf-8").splitlines(), 1):
        if not satir.strip():
            continue
        try:
            kayit = json.loads(satir)
        except json.JSONDecodeError as hata:
            raise ValueError(f"JSONL satırı geçersiz: {sira}") from hata
        if not isinstance(kayit, dict):
            raise ValueError(f"JSONL satırı nesne olmalı: {sira}")
        satirlar.append(kayit)
    if len(satirlar) != beklenen_n:
        raise ValueError(f"Tam {beklenen_n} validation satırı gerekli; bulunan: {len(satirlar)}.")
    kimlikler = [r.get("id") for r in satirlar]
    if any(not isinstance(k, str) or not k for k in kimlikler) or len(set(kimlikler)) != beklenen_n:
        raise ValueError("Validation kimlikleri eksik veya yinelenmiş.")
    return satirlar


def validation_yukle(yol: Path) -> tuple[list[dict], str, str]:
    manifest_yolu = KOK / "lora" / "v6_girdi_manifest.json"
    manifest_bytes = manifest_yolu.read_bytes()
    manifest = json.loads(manifest_bytes)
    beklenen = manifest.get("beklenen_sha256", {}).get("valid")
    if not isinstance(beklenen, str) or len(beklenen) != 64:
        raise ValueError("v6 girdi manifestinde sabit valid_300 SHA-256 değeri yok.")
    icerik = yol.expanduser().read_bytes()
    satirlar = dogrulama_satirlari(icerik, beklenen)
    for kayit in satirlar:
        sema_dogrula(kayit, "v6")
    return satirlar, beklenen, sha256(manifest_bytes)


def cikti_yolu_dogrula(yol: Path) -> Path:
    hedef = yol.expanduser().resolve()
    try:
        hedef.relative_to(KOK)
    except ValueError:
        pass
    else:
        raise ValueError("Aggregate çıktı depo dışında olmalı; repo içine yazmaya izin verilmiyor.")
    if hedef.exists():
        raise FileExistsError("Mevcut çıktının üzerine yazılmayacak.")
    return hedef


def plan_olustur(satirlar: list[dict], veri_sha: str, manifest_sha: str) -> dict:
    # TABAN_PROTOKOL.md: 2.285 sn / 2.000 ve 130 sn / 115; en yavaş oranı kullan.
    saniye_satir = max(2285 / 2000, 130 / 115)
    toplam_uretim = len(satirlar) * 2
    tahmin_saniye = math.ceil(saniye_satir * toplam_uretim)
    return {
        "durum": "plan_only; GPU çıkarımı not run",
        "bolum": "valid_300",
        "n": len(satirlar),
        "proje_sayisi": len({r["proje"] for r in satirlar}),
        "validation_sha256": veri_sha,
        "girdi_manifest_sha256": manifest_sha,
        "model": MODEL,
        "model_revizyon": MODEL_REVIZYON,
        "adaptör": None,
        "kollar": ["tarihsel_istem", "ornek_degerleri_yok"],
        "toplam_uretim": toplam_uretim,
        "sinirlar": {
            "tek_gpu": True,
            "bfloat16": True,
            "asgari_vram_gib_tahmini": 24,
            "girdi_token_tavani": GIRDI_TAVANI,
            "yeni_token_tavani": URETIM_TAVANI,
            "batch_size": 1,
            "egitim_adimi": 0,
        },
        "maliyet_tahmini": {
            "saniye": tahmin_saniye,
            "dakika": round(tahmin_saniye / 60, 1),
            "gpu_saat": round(tahmin_saniye / 3600, 3),
            "dayanak": {
                "test_sabit": {"n": 2000, "saniye": 2285},
                "eval115": {"n": 115, "saniye": 130},
                "yontem": "İki tarihsel saniye/satır oranının büyüğü × 600 üretim; model yükleme hariç, ölçülmüş validation süresi değildir.",
            },
        },
        "basari_kriteri": {
            "birincil": "Örneksiz − tarihsel kanonik ad F1 farkı >= +0.010 ve eşli proje-bootstrap %95 alt sınırı > 0.",
            "korumalar": "Öneksiz F1 farkı >= 0 ve geçerli JSON oranı düşmemeli.",
            "bootstrap": {"birim": "proje", "tekrar": BOOTSTRAP_TEKRAR, "tohum": BOOTSTRAP_TOHUM},
        },
        "test_puanlama": "not run; bu araç test dosyalarını okumaz",
        "egitim": "not run",
        "ham_tahmin_kaydedilir": False,
    }


def _token_idleri(tokenizer, mesajlar) -> list[int]:
    sonuc = tokenizer.apply_chat_template(
        mesajlar,
        tokenize=True,
        add_generation_prompt=True,
        enable_thinking=False,
        return_dict=False,
    )
    if isinstance(sonuc, dict):
        sonuc = sonuc["input_ids"]
    if hasattr(sonuc, "tolist"):
        sonuc = sonuc.tolist()
    if sonuc and isinstance(sonuc[0], list):
        sonuc = sonuc[0]
    return list(sonuc)


def _kol_ozeti(kayitlar: list[dict], saniye: float) -> dict:
    adet = len(kayitlar)
    return {
        "n": adet,
        "ad_f1": math.fsum(r["ad_f1"] for r in kayitlar) / adet,
        "oneksiz_f1": math.fsum(r["oneksiz_f1"] for r in kayitlar) / adet,
        "tam_ad": sum(r["tam_ad"] for r in kayitlar),
        "f1_1": sum(r["ad_f1"] == 1.0 for r in kayitlar),
        "gecerli_json_orani": sum(r["gecerli_json"] for r in kayitlar) / adet,
        "gecersiz_json": sum(not r["gecerli_json"] for r in kayitlar),
        "ornek_adini_tam_kopya": sum(r["ornek_tam"] for r in kayitlar),
        "ornek_adini_iceren": sum(r["ornek_iceren"] for r in kayitlar),
        "tavan_token_satiri": sum(r["tavana_dayan"] for r in kayitlar),
        "ortalama_girdi_tokeni": math.fsum(r["girdi_token"] for r in kayitlar) / adet,
        "uretilen_token": sum(r["yeni_token"] for r in kayitlar),
        "uretim_saniye": round(saniye, 1),
    }


def _gpu_olc(satirlar: list[dict], model_dizini: Path, veri_sha: str, manifest_sha: str) -> dict:
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if transformers.__version__ != "5.3.0":
        raise RuntimeError("Bu protokol transformers==5.3.0 gerektirir.")
    if torch.__version__.split("+", 1)[0] != "2.11.0" or torch.version.cuda != "13.0":
        raise RuntimeError("Bu protokol torch 2.11.0 + CUDA 13.0 tabanıyla sabitlenmiştir.")
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError("BF16 destekli CUDA GPU gerekli.")
    vram_toplam = torch.cuda.get_device_properties(0).total_memory
    vram_bos, _ = torch.cuda.mem_get_info()
    if vram_toplam < 24 * 1024**3 or vram_bos < 20 * 1024**3:
        raise RuntimeError("En az 24 GiB toplam ve 20 GiB boş GPU belleği gerekli.")

    model_yolu = model_dizini.expanduser().resolve()
    if not model_yolu.is_dir() or model_yolu.name != MODEL_REVIZYON:
        raise ValueError("Model dizini, sabitlenmiş Qwen3-8B snapshot SHA'sıyla bitmeli.")
    tokenizer = AutoTokenizer.from_pretrained(str(model_yolu), local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        str(model_yolu),
        local_files_only=True,
        dtype=torch.bfloat16,
        device_map={"": 0},
        attn_implementation="sdpa",
    )
    model.eval()

    _, _, ornek = ornek_araligi(SISTEM_V6)
    ornek_ad = ornek["ad"]
    sistem_oz = SISTEM_V6
    sistem_orneksiz = orneksiz_istem(sistem_oz)
    kollar = {"tarihsel_istem": [], "ornek_degerleri_yok": []}
    sureler = {}

    for kol, sistem in (("tarihsel_istem", sistem_oz), ("ornek_degerleri_yok", sistem_orneksiz)):
        baslangic = time.monotonic()
        for kayit in satirlar:
            mesajlar = [
                {"role": "system", "content": sistem},
                {"role": "user", "content": kayit["messages"][1]["content"]},
            ]
            ids = _token_idleri(tokenizer, mesajlar)
            if len(ids) > GIRDI_TAVANI:
                raise ValueError("Validation girdisi 3072 tokenı aşıyor; kesme yapılmayacak.")
            girdi = torch.tensor([ids], dtype=torch.long, device="cuda:0")
            with torch.inference_mode():
                cikti = model.generate(
                    input_ids=girdi,
                    attention_mask=torch.ones_like(girdi),
                    do_sample=False,
                    max_new_tokens=URETIM_TAVANI,
                    use_cache=True,
                    pad_token_id=tokenizer.pad_token_id,
                )
            yeni = cikti[0, len(ids) :]
            ham = tokenizer.decode(yeni, skip_special_tokens=True)
            ad, _, _, gecerli = ad_ayikla(ham)
            tahmin = {"tahmin": ad}
            puan = f1(ad, kayit["gercek_ad"])
            kollar[kol].append(
                {
                    "proje": kayit["proje"],
                    "ad_f1": puan,
                    "oneksiz_f1": oneksiz(tahmin, kayit),
                    "tam_ad": ad == kayit["gercek_ad"],
                    "gecerli_json": gecerli,
                    "ornek_tam": ad == ornek_ad,
                    "ornek_iceren": ornek_ad in ad,
                    "tavana_dayan": len(yeni) >= URETIM_TAVANI,
                    "girdi_token": len(ids),
                    "yeni_token": len(yeni),
                }
            )
        torch.cuda.synchronize()
        sureler[kol] = time.monotonic() - baslangic

    projeler = [r["proje"] for r in kollar["tarihsel_istem"]]
    tarihsel = kollar["tarihsel_istem"]
    orneksiz = kollar["ornek_degerleri_yok"]
    ad_farki = bootstrap_farki(
        [r["ad_f1"] for r in orneksiz],
        [r["ad_f1"] for r in tarihsel],
        projeler,
        BOOTSTRAP_TOHUM,
        BOOTSTRAP_TEKRAR,
    )
    oneksiz_farki = bootstrap_farki(
        [r["oneksiz_f1"] for r in orneksiz],
        [r["oneksiz_f1"] for r in tarihsel],
        projeler,
        BOOTSTRAP_TOHUM,
        BOOTSTRAP_TEKRAR,
    )
    tarihsel_ozet = _kol_ozeti(tarihsel, sureler["tarihsel_istem"])
    orneksiz_ozet = _kol_ozeti(orneksiz, sureler["ornek_degerleri_yok"])
    basari = (
        ad_farki["fark"] >= 0.01
        and ad_farki["ga95"][0] > 0
        and oneksiz_farki["fark"] >= 0
        and orneksiz_ozet["gecerli_json_orani"] >= tarihsel_ozet["gecerli_json_orani"]
    )
    return {
        "durum": "inference tamamlandı",
        "bolum": "valid_300",
        "n": len(satirlar),
        "proje_sayisi": len(set(projeler)),
        "validation_sha256": veri_sha,
        "girdi_manifest_sha256": manifest_sha,
        "kaynak_commit": git_degeri("rev-parse", "HEAD"),
        "kaynak_tree": git_degeri("rev-parse", "HEAD^{tree}"),
        "model": MODEL,
        "model_revizyon": MODEL_REVIZYON,
        "model_lisans": "Apache-2.0",
        "komut_sablonu": "python3 molab/istem_ornegi_ablasyonu.py --validation <valid_300.jsonl> --model-dir <pinned-snapshot> --output <outside-repo>/aggregate.json --run",
        "transformers": transformers.__version__,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0),
        "gpu_vram_gib": round(vram_toplam / 1024**3, 1),
        "adaptör": None,
        "uretim": {
            "do_sample": False,
            "enable_thinking": False,
            "max_new_tokens": URETIM_TAVANI,
            "max_input_tokens": GIRDI_TAVANI,
            "batch_size": 1,
            "dtype": "bfloat16",
            "attention": "sdpa",
        },
        "istem_sha256": {
            "tarihsel": sha256(sistem_oz.encode("utf-8")),
            "ornek_degerleri_yok": sha256(sistem_orneksiz.encode("utf-8")),
        },
        "kollar": {
            "tarihsel_istem": tarihsel_ozet,
            "ornek_degerleri_yok": orneksiz_ozet,
        },
        "esli_fark": {
            "ad_f1": ad_farki,
            "oneksiz_f1": oneksiz_farki,
        },
        "karar": {
            "onceden_tanimli_kriter_gecti": basari,
            "kriter": "Kanonik F1 farkı >= +0.010, proje-bootstrap GA95 alt sınırı > 0; öneksiz F1 farkı >= 0 ve geçerli JSON oranı düşmemeli.",
        },
        "test_puanlama": "not run; test dosyaları okunmadı",
        "egitim": "not run",
        "ham_tahmin_kaydedildi": False,
        "uretim_saniye": {k: round(v, 1) for k, v in sureler.items()},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Yalnız sabit valid_300 üzerinde prompt örneği ablation.")
    ap.add_argument("--validation", type=Path, required=True, help="v6 release içindeki sabit valid_300.jsonl")
    ap.add_argument("--model-dir", type=Path, help="Yerel Qwen3-8B snapshot dizini; ağdan indirme yapılmaz.")
    ap.add_argument("--output", type=Path, help="Aggregate JSON çıktısı; depo dışında ve mevcut olmayan yol.")
    ap.add_argument("--run", action="store_true", help="Varsayılan plan kipinden çıkıp GPU inference çalıştır.")
    args = ap.parse_args()

    satirlar, veri_sha, manifest_sha = validation_yukle(args.validation)
    if not args.run:
        print(json.dumps(plan_olustur(satirlar, veri_sha, manifest_sha), ensure_ascii=False, indent=2))
        return 0
    if args.model_dir is None or args.output is None:
        ap.error("--run için --model-dir ve --output gereklidir.")
    cikti = cikti_yolu_dogrula(args.output)
    ozet = _gpu_olc(satirlar, args.model_dir, veri_sha, manifest_sha)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    cikti.write_text(json.dumps(ozet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"durum": ozet["durum"], "aggregate_cikti_yazildi": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
