from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
BELGE = KOK / "rapor/arastirma/ONCEKI_CALISMALAR.md"
MSR_ANA = KOK / "makale/msr2027/main.tex"
MSR_KAYNAKLAR = KOK / "makale/msr2027/refs.bib"


def test_literatur_guncel_main_ve_v6_onceligi():
    md = BELGE.read_text(encoding="utf-8")
    assert "15e3b28f1be387d0e8655edd838e1c32f9d348d5" in md
    assert "6f8d4781522bc7be45839071dc7231e12d0164e5" in md
    assert "İlk iş mevcut v6 hattını değerlendir" in md
    assert "Main'de karşılanan gereksinim" in md and "Kalan boşluklar" in md
    for yol in ("lora/hazirla_sonraki.py", "molab/egit.py", "decompile_ghidra.py", "dogrula_v6.py", "olcekle.py"):
        assert (KOK / yol).is_file() and yol in md
    assert "--surum v6" in md and "VERI_SURUM" in md


def test_birlesen_araclar_acik_veya_taslak_gosterilmez():
    md = BELGE.read_text(encoding="utf-8")

    assert "[#9](https://github.com/krxi/asmsense/pull/9) ana dala birleştirildi" in md
    assert "#6 iki kanıt hash'i\nsağlanana kadar fail-closed" in md
    assert "Açık [#4]" not in md
    assert "#6 taslaktır" not in md


def test_testin_gelistirme_kullanimi_gizlenmez():
    md = BELGE.read_text(encoding="utf-8")
    assert "geliştirmede kullanılmış\nölçüt" in md
    assert "gerçekleşmiş bir özellik değildir" in md
    assert "Geleceğe yönelik öneri" in md
    assert "tam koşuların sonunda testi ölçer" in md
    assert "gerçek arşiv tahminlerini" in md


def test_kume_ve_coklu_karsilastirma_protokolu():
    md = BELGE.read_text(encoding="utf-8")
    for ifade in (
        "Birincil yeniden örnekleme birimi proje",
        "optimizasyon kopyaları",
        "Bonferroni",
        "%99",
        "0,005",
        "0,995",
    ):
        assert ifade in md
    assert "0,05 / 5" in md and "20.000" in md
    assert "yalnız raporlanan\nkazananlara değil" in md


@pytest.mark.parametrize(
    "yasak", ["/workspace/", "/Users/", "sys.executable", "58157e7", "eccf6b4", "1b4a0a7", "3b7aefe", "63e6ddc"]
)
def test_kisisel_yol_ve_eski_birincil_kaynak_yok(yasak):
    assert yasak not in BELGE.read_text(encoding="utf-8")


def test_kaynak_haritasi_temel_calisma_ve_sinirlari_korur():
    md = BELGE.read_text(encoding="utf-8")
    for ad in (
        "DIRE",
        "DIRTY",
        "NERO",
        "SymLM",
        "XFL",
        "BLens",
        "SymGen",
        "HexT5",
        "AsmDepictor",
        "VarBERT",
        "ReSym",
        "LLM4Decompile",
        "BinSum",
    ):
        assert ad in md
    assert "unverified" in md and "not run" in md
    assert "https://" in md and "veri veya ağırlık lisansı yerine geçmez" in md


def test_msr_blens_ve_symgen_kaynaklari_dogrulandi():
    refs = MSR_KAYNAKLAR.read_text(encoding="utf-8")
    ana = MSR_ANA.read_text(encoding="utf-8")

    assert "TODO" not in refs
    for ifade in (
        "Benoit, Tristan and Wang, Yunru and Dannehl, Moritz and Kinder, Johannes",
        "34th USENIX Security Symposium (USENIX Security 25)",
        "pages     = {6877--6896}",
        "Jiang, Linxi and Jin, Xin and Lin, Zhiqiang",
        "Beyond Classification: Inferring Function Names in Stripped Binaries",
        "doi       = {10.14722/ndss.2025.240797}",
    ):
        assert ifade in refs

    assert "excludes 20 common names" not in ana
    assert "twenty static-analysis-identifiable functions" in ana
    assert "binary-level split" in ana and "2.94\\times" in ana


def test_benchmark_raporlari_satir_duzeyinde_ornek_yayinlamaz():
    for yol in (KOK / "rapor/ONEK_DENETIM.md", KOK / "rapor/ONEK_DENETIM_V4.md"):
        md = yol.read_text(encoding="utf-8")
        assert "## Örnekler" not in md
        assert "## Çakışmalar" not in md
        assert not any("→" in satir and "`" in satir for satir in md.splitlines())


def test_v6_pilot_belgesi_satir_duzeyinde_ornek_yayinlamaz():
    md = (KOK / "lora/V6_DOGRULAMA.md").read_text(encoding="utf-8")
    assert "→" not in md
    assert "; ->" not in md
    assert "95.000 train +" in md


def test_readme_kopyalama_notu_ornek_etiketi_yayinlamaz():
    en = (KOK / "README.md").read_text(encoding="utf-8")
    tr = (KOK / "README.tr.md").read_text(encoding="utf-8")
    en_satir = next(s for s in en.splitlines() if "main failure is copying" in s.lower())
    tr_satir = next(s for s in tr.splitlines() if "asıl hata kopyalama" in s.lower())
    en_bolum = en_satir.split("the system prompt contains", 1)[1].split("in 768/2,000 rows", 1)[0]
    tr_bolum = tr_satir.split("sistem istemi örnek bir cevap içeriyor ve eğitilmemiş model", 1)[1].split(
        "2.000 satırın 768'inde", 1
    )[0]
    assert "`" not in en_bolum
    assert "`" not in tr_bolum


def test_model_kirilim_raporlari_tahmin_adi_yayinlamaz():
    yollar = (
        "rapor/MOLAB_KIRILIM.md",
        "rapor/MOLAB_KIRILIM_EVAL115.md",
        "rapor/MOLAB_V5_KIRILIM.md",
        "rapor/MOLAB_V5_KIRILIM_EVAL115.md",
    )
    for goreli in yollar:
        md = (KOK / goreli).read_text(encoding="utf-8")
        assert "En sık 10 tahmin" not in md
        assert "tekil tahmin adları yayımlanmaz" in md
        assert not any("×" in satir and "`" in satir for satir in md.splitlines())
