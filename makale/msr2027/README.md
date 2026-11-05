# MSR 2027 Data and Tool Showcase taslağı

Son tarihler (AoE): özet 5 Kasım 2026, makale 10 Kasım 2026. Sınır: 4 sayfa + 1 sayfa kaynak, IEEE
biçimi, tek-taraflı kör hakemlik. Kabulde en az bir yazar kayıt yaptırıp sunmak zorunda; kamera-hazırda
verinin DOI'si gerekir.

```sh
tectonic main.tex          # veya: pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Taslak v6 satırını, karışık sonucu ve güncel veri-audit sınırlarını içeriyor. Sayfa sayısı gönderimden
önce aşağıdaki derleme komutuyla yeniden doğrulanmalı.

## Göndermeden önce

- [ ] Yazar soyadı (`main.tex` başı; kurum "Independent researcher, Türkiye" yazıldı, e-posta gönderim sisteminde)
- [ ] Zenodo DOI: gönderimde gerekmez, kamera-hazırda (24 Ocak) gerekir. `asmsense-data` için entegrasyonu aç, yeni release yayımla
- [x] `refs.bib`: 7 kaynak doğrulandı; BLens ve SymGen sayfa/DOI ile resmî konferans sayfalarından (#15), diğerleri arXiv/ACL/Zenodo'dan (XFL/NERO sayfa ve DOI'si çelişkili kaynaklar yüzünden yok)
- [x] v6 sonucu ve karşılaştırma sınırları Tablo III'e/metne işlendi (`olcum-v6.json`, main `219b8bc`)
- [ ] Metni kendi sesinle revize et; sayıları değiştirme, kaynakları aşağıda
- [ ] İsteğe bağlı şekil: `grafik/x-ezber.png` (ezber karşılaştırması) veya `grafik/test-hata.png`

## Sayıların kaynağı

| Metindeki sayı | Kaynak |
|---|---|
| Veri boyutu ve bölmeler | README "Scaled dataset (v4 pipeline)" |
| Ezber tablosu | README bölüm 2 |
| test2000 taban çizgileri ve snkv dışı sütun | `sonuc/test2000-*.jsonl`, `rapor/arastirma/V6_VERI_DENETIMI.md` |
| v5 − v1 aralığı (+0,010 … +0,031) | proje-kümeli bootstrap, `aciklama_degerlendir.bootstrap_farki`, 4.000 çekim, tohum 42 |
| v6 − v5 adı, checkpoint/protokol ve açıklama kalitesi | README bölüm 6; [tam duyarlıklı ad raporu](https://huggingface.co/krxi123/asmsense-lora-v6/blob/main/olcum-v6.json); [eşlenmiş açıklama denetimi](https://huggingface.co/krxi123/asmsense-lora-v6/blob/main/aciklama-v6.json) |
| Decompile kazancı | README bölüm 7 |
