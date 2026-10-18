# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "transformers==5.3.0",
#     "accelerate>=1.12,<2",
#     "huggingface_hub>=1.0,<2",
#     "torch>=2.6",
#     "marimo>=0.15.2",
# ]
# ///
# Paket sürümleri v6 final ölçümünün koştuğu molab/egit.py ile aynı (transformers 5.3.0).

import marimo

__generated_with = "0.15.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md(
        r"""
        # asmsense: eğitilmemiş Qwen3-8B taban ölçümü

        v6 final ölçümüyle aynı koşullar, **adaptörsüz**: aynı `test_sabit` (2000) ve `eval115` (115) girdisi,
        aynı istem ve chat template, greedy, `enable_thinking=False`, `max_new_tokens=160`, bf16, tek GPU.
        Protokol: `molab/TABAN_PROTOKOL.md`. Token gerekmez; hiçbir yere yükleme yapılmaz.

        **Başlat**'a bas. Bittiğinde (yaklaşık 1,5 saat) en alttaki `taban-sonuc.zip`'i indir.
        Oturum koparsa notebook'u yeniden çalıştır; biten satırlar atlanır.
        """
    )
    return


@app.cell
def _():
    import hashlib
    import json
    import logging
    import os
    import re
    import shutil
    import time
    import urllib.request
    import zipfile
    from pathlib import Path

    MODEL = "Qwen/Qwen3-8B"
    REVIZYON = "b968826d9c46dd6066d109eabc6255188de91218"
    VERI_URL = "https://github.com/krxi/asmsense-data/releases/download/v6/veri-v6.zip"
    BEKLENEN = {
        "test_sabit": (2000, "4ad04cd5b904a91a77d417b2a427ccb053bffe502368ecb182d293be84fcc586"),
        "eval115": (115, "e9fa2f5747eda8a2b78fb614548182da869e87a0b32508e6d26f6c9527922b12"),
    }
    KOK = Path(os.environ.get("ASM_KOK", "asm-taban-v6")).expanduser().resolve()

    # lora/cikti.py ile aynı (v6 molab/egit.py'deki kopya). Değiştirme: ana skor v6 ile aynı ayrıştırıcıdır.
    def ad_ayikla(metin: str) -> tuple[str, str, str, bool]:
        """JSON, kesik JSON ve düz metin için (ad, İngilizce, Türkçe, geçerli JSON)."""
        metin = metin.strip()
        decoder = json.JSONDecoder()
        for bas in (m.start() for m in re.finditer(r"\{", metin)):
            try:
                veri, _ = decoder.raw_decode(metin[bas:])
            except ValueError:
                continue
            if isinstance(veri, dict) and isinstance(veri.get("ad"), str):
                return (veri["ad"], veri.get("aciklama_en") or "", veri.get("aciklama") or "", True)

        def alan(ad):
            es = re.search(r'"' + ad + r'"\s*:\s*("(?:\\.|[^"\\])*")', metin)
            if es:
                try:
                    return json.loads(es[1])
                except ValueError:
                    pass
            return ""

        ad = alan("ad")
        if ad:
            return ad, alan("aciklama_en"), alan("aciklama"), False
        es = re.search(r"[A-Za-z_][A-Za-z0-9_]*", metin)
        return (es[0] if es else ""), "", "", False

    def kelimeler(ad: str) -> list[str]:
        ad = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", ad)
        return [k for k in re.split(r"[_\W]+", ad.lower()) if k]

    def f1(tahmin: str, gercek: str) -> float:
        t, g = kelimeler(tahmin), kelimeler(gercek)
        ortak = len(set(t) & set(g))
        if not ortak:
            return 0.0
        p, r = ortak / len(set(t)), ortak / len(set(g))
        return 2 * p * r / (p + r)

    def jsonl_oku(yol):
        with Path(yol).open(encoding="utf-8") as dosya:
            return [json.loads(satir) for satir in dosya if satir.strip()]

    def sha256(yol):
        ozet = hashlib.sha256()
        with Path(yol).open("rb") as dosya:
            for parca in iter(lambda: dosya.read(1 << 20), b""):
                ozet.update(parca)
        return ozet.hexdigest()

    def sablon_ids(tokenizer, mesajlar):
        cikti = tokenizer.apply_chat_template(
            mesajlar,
            tokenize=True,
            add_generation_prompt=True,
            enable_thinking=False,
            return_dict=False,
        )
        if hasattr(cikti, "keys"):
            cikti = cikti["input_ids"]
        return list(cikti)

    def veri_hazirla(logger):
        KOK.mkdir(parents=True, exist_ok=True)
        arsiv = KOK / "veri-v6.zip"
        if not arsiv.exists():
            gecici = arsiv.with_suffix(".part")
            with urllib.request.urlopen(VERI_URL) as yanit, gecici.open("wb") as dosya:
                shutil.copyfileobj(yanit, dosya)
            gecici.replace(arsiv)
        acilmis = KOK / "veri-v6"
        with zipfile.ZipFile(arsiv) as z:
            for bilgi in z.infolist():
                if bilgi.filename.rsplit("/", 1)[-1] not in ("test_sabit.jsonl", "eval115.jsonl"):
                    continue
                hedef = (acilmis / bilgi.filename).resolve()
                if acilmis.resolve() not in hedef.parents:
                    raise ValueError("Arşiv yolu çalışma dizini dışına taşıyor.")
                z.extract(bilgi, acilmis)
        bolumler = {}
        for bolum, (adet, ozet) in BEKLENEN.items():
            yol = next(acilmis.rglob(f"{bolum}.jsonl"))
            if sha256(yol) != ozet:
                raise ValueError(f"{bolum}: girdi v6 ile aynı değil (sha256 uyuşmuyor).")
            satirlar = jsonl_oku(yol)
            if len(satirlar) != adet:
                raise ValueError(f"{bolum}: {adet} satır bekleniyordu, {len(satirlar)} bulundu.")
            bolumler[bolum] = satirlar
            logger.info("%s: %s satır, sha256 doğrulandı", bolum, adet)
        return bolumler

    def olc():
        import torch
        import transformers
        from transformers import AutoModelForCausalLM, AutoTokenizer

        KOK.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger("asm-taban")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            for handler in (logging.FileHandler(KOK / "taban.log", encoding="utf-8"), logging.StreamHandler()):
                handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
                logger.addHandler(handler)
        if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
            raise RuntimeError("CUDA ve bf16 destekli GPU gerekli.")
        bolumler = veri_hazirla(logger)
        ortam = {
            "model": MODEL,
            "revizyon": REVIZYON,
            "adaptor": None,
            "dtype": "bfloat16",
            "attn": "sdpa",
            "max_new_tokens": 160,
            "do_sample": False,
            "enable_thinking": False,
            "transformers": transformers.__version__,
            "torch": torch.__version__,
            "gpu": torch.cuda.get_device_name(0),
        }
        logger.info("Ortam: %s", json.dumps(ortam, ensure_ascii=False))
        tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVIZYON)
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        model, yukleme = AutoModelForCausalLM.from_pretrained(
            MODEL,
            revision=REVIZYON,
            dtype=torch.bfloat16,
            device_map={"": 0},
            attn_implementation="sdpa",
            output_loading_info=True,
        )
        if yukleme.get("missing_keys") or yukleme.get("mismatched_keys"):
            raise RuntimeError("Model ağırlıkları eksik/uyumsuz yüklendi.")
        model.eval()

        ozet = {"ortam": ortam, "bolumler": {}}
        dosyalar = []
        for bolum, satirlar in bolumler.items():
            yol = KOK / f"taban-{bolum}-sonuc.jsonl"
            bitti = {r["id"] for r in jsonl_oku(yol)} if yol.exists() else set()
            baslangic = time.monotonic()
            with yol.open("a", encoding="utf-8") as dosya, torch.inference_mode():
                for i, r in enumerate(satirlar, 1):
                    if r["id"] in bitti:
                        continue
                    ids = sablon_ids(tokenizer, r["messages"][:2])
                    if len(ids) > 3072:
                        raise ValueError(f"{r['id']}: üretim girdisi 3072 tokenı aşıyor.")
                    girdi = torch.tensor([ids], device=model.device)
                    sonuc = model.generate(
                        input_ids=girdi,
                        attention_mask=torch.ones_like(girdi),
                        do_sample=False,
                        max_new_tokens=160,
                        use_cache=True,
                        pad_token_id=tokenizer.pad_token_id,
                    )
                    yeni = sonuc[0, len(ids) :]
                    ham = tokenizer.decode(yeni, skip_special_tokens=True)
                    ad, en, tr, gecerli = ad_ayikla(ham)
                    satir = {
                        "id": r["id"],
                        "gercek": r["gercek_ad"],
                        "tahmin": ad,
                        "aciklama_en": en,
                        "aciklama": tr,
                        "gecerli_json": gecerli,
                        "f1": f1(ad, r["gercek_ad"]),
                        "opt": r["opt"],
                        "proje": r["proje"],
                        "token": len(ids) + len(yeni),
                        "yeni_token": len(yeni),
                        "sinira_dayandi": len(yeni) >= 160,
                        "ham": ham,
                    }
                    dosya.write(json.dumps(satir, ensure_ascii=False) + "\n")
                    dosya.flush()
                    if i % 100 == 0:
                        logger.info("%s %s/%s", bolum, i, len(satirlar))
            sonuclar = jsonl_oku(yol)
            if len(sonuclar) != len(satirlar) or {r["id"] for r in sonuclar} != {r["id"] for r in satirlar}:
                raise RuntimeError(f"{bolum}: sonuç satırları girdiyle hizalı değil.")
            n = len(sonuclar)
            ozet["bolumler"][bolum] = {
                "n": n,
                "f1": sum(r["f1"] for r in sonuclar) / n,
                "f1_kati": sum(r["f1"] if r["gecerli_json"] else 0.0 for r in sonuclar) / n,
                "gecerli_json_orani": sum(r["gecerli_json"] for r in sonuclar) / n,
                "sinira_dayanan_orani": sum(r["sinira_dayandi"] for r in sonuclar) / n,
                "sure_sn": round(time.monotonic() - baslangic, 1),
                "sha256": sha256(yol),
            }
            logger.info("TABAN %s %s", bolum, ozet["bolumler"][bolum])
            dosyalar.append(yol)
        (KOK / "taban-tamam.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=2), encoding="utf-8")
        for handler in logger.handlers:
            handler.flush()
        dosyalar += [KOK / "taban-tamam.json", KOK / "taban.log"]
        zip_yolu = KOK / "taban-sonuc.zip"
        with zipfile.ZipFile(zip_yolu, "w", zipfile.ZIP_DEFLATED) as z:
            for d in dosyalar:
                z.write(d, d.name)
        return zip_yolu, ozet

    return (olc,)


@app.cell
def _(mo):
    baslat = mo.ui.run_button(label="Başlat")
    baslat
    return (baslat,)


@app.cell
def _(baslat, mo, olc):
    mo.stop(not baslat.value, mo.md("Hazır olunca **Başlat**'a bas."))
    zip_yolu, ozet = olc()
    mo.vstack(
        [
            mo.md(f"```\n{__import__('json').dumps(ozet['bolumler'], indent=2)}\n```"),
            mo.download(data=zip_yolu.read_bytes(), filename=zip_yolu.name, label=f"İndir: {zip_yolu.name}"),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
