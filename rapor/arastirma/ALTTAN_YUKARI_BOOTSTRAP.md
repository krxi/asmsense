# Alttan yukarı sözcüksel denetim: eşli proje-kümeli aralıklar

## Amaç

`alttan_yukari_sim.py` aynı validation satırları için üç görünüm üretir:
anonimleştirilmiş çağrı bağlamı, gerçek callee adlarıyla yeniden yazılmış bağlam
ve sabit v5 callee tahminleriyle yeniden yazılmış bağlam. Bu yardımcı, mevcut
aggregate özetteki iki eşli `macro_token_recall` farkı için proje-kümeli %95
bootstrap aralığı hesaplar.

Bu değerler yalnız **lexical-information availability** ölçüsüdür. Modelin
fonksiyon adı F1'ı, nedensel kazanım veya gerçek inference sonucu değildir.

## Yöntem

- Girdi, sabit v6 `valid_300` (n=300), v4 validation ve v5 `valid300`
  tahminlerinin hash'lerini taşıyan `alttan_yukari_sim.py` aggregate özetidir.
- Özetin `provenance` hash'leri `lora/v6_girdi_manifest.json` ve
  `rapor/arastirma/dogrulama_manifest.json` ile eşleşmelidir.
- Özet, üç modda aynı proje kümesini ve proje başına aynı satır sayısını
  taşımalıdır. Proje satırları toplamı 300 olmalıdır.
- Yeniden örnekleme birimi projedir. Her tekrarda proje sayısı kadar proje
  yerine koyarak örneklenir; seçilen projenin bütün satırları birlikte kalır.
- Her tekrarda aynı proje örneklemi iki karşılaştırmada da kullanılır. Böylece
  farklar eşlidir ve proje içindeki optimizasyon kopyaları bağımsız örnek sayılmaz.
- Nokta tahmini, proje kümeleri üzerinden satır-ağırlıklı macro token recall
  farkıdır. Aralık 2.000 tekrar ve 42 tohumla percentile yöntemiyle, doğrusal
  interpolasyon kullanılarak hesaplanır.

Karşılaştırmalar:

1. `gold - anonymised`: bütün callee adları bilinseydi bağlamın sağlayacağı
   sözcüksel bilgi üst sınırı.
2. `v5_predicted - anonymised`: sabit v5 callee tahminleriyle görülebilen
   sözcüksel bilgi.

İkinci fark modelin yeniden adlandırma başarısına eşit değildir; yalnız tahmin
edilmiş callee adlarının bağlama eklediği sözcük örtüşmesini ölçer.

## Çalıştırma

Önce PR #27'deki hash-sabit validation girdilerini depo dışında hazırlayın ve
PR #25'teki validation-only simülasyonunu çalıştırın. `--export` kullanmayın:

```sh
python3 alttan_yukari_sim.py \
  --prompts /path/to/valid_300-v6.jsonl \
  --raw /path/to/validation-v4.jsonl \
  --predictions /path/to/valid300-v5-predictions.jsonl \
  --output /tmp/bottom-up-summary.json
```

Simülasyon komutunu çalıştırdığınız commit'i kaydedin:

```sh
AUDIT_COMMIT=$(git rev-parse HEAD)
```

Ardından yalnız aggregate özeti kullanın:

```sh
python3 alttan_yukari_bootstrap.py \
  --ozet /tmp/bottom-up-summary.json \
  --cikti /tmp/bottom-up-bootstrap.json \\
  --audit-commit "$AUDIT_COMMIT" \\
  --tekrar 2000 --tohum 42
```

`--audit-commit`, simülasyonu üreten commit'tir; araç commit'in geçerli olduğunu ve bu commit'te `alttan_yukari_sim.py` bulunduğunu doğrular. Rapor bu commit'i kaydeder. Varsayılanlar 2.000 tekrar ve seed 42'dir; komut bunları açıkça sabitler. Farklı bir yöntem önceden belirlenirse `--tekrar` ve `--tohum` değiştirilebilir. Çıktı depo dışında olmalı ve mevcut dosyanın üzerine yazılmaz.

## Güvenlik ve kapsam

- Araç satır düzeyindeki girdileri okumaz; yalnız aggregate simülasyon JSON'unu
  işler. Proje adları, kimlikler, fonksiyon adları ve assembly çıktı JSON'una
  yazılmaz.
- Sabit validation hash'leri uyuşmazsa, proje kümeleri farklıysa veya satır
  sayıları tutmuyorsa fail-closed durur.
- `taban.f1`, tarihsel prompt biçimleri, scorer ve mevcut JSON şemaları
  değiştirilmez. Yeni bootstrap raporu ayrı bir şemadır.
- Testler sentetik aggregate özetleri kullanır; ağ, GPU, Ghidra veya API anahtarı
  gerektirmez.
- Gerçek validation artifact indirmesi ve bootstrap çalıştırması bu PR'da
  **not run**. Herhangi bir F1 kazanımı iddia edilmez.
