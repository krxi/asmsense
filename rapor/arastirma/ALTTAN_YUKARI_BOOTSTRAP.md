# Alttan yukarı sözcüksel denetim: eşli proje-kümeli aralıklar

## Amaç

`alttan_yukari_sim.py` aynı validation satırları için dört görünüm üretir:
anonimleştirilmiş çağrı bağlamı, bütün çözümlenmiş callee'lerin gerçek adları,
sabit v5 tahminlerinin bulunduğu callee yuvalarında gerçek adlar (`gold_prediction_coverage`)
ve sabit v5 callee tahminleri. Bu yardımcı, aggregate özetteki beş eşli
`macro_token_recall` karşılaştırması için proje-kümeli %95 bootstrap aralığı hesaplar.

Bu değerler yalnız **lexical-information availability** ölçüsüdür. Modelin
fonksiyon adı F1'ı, nedensel kazanım veya gerçek inference sonucu değildir.

## Yöntem

- Girdi, sabit v6 `valid_300` (n=300), v4 validation ve v5 `valid300`
  tahminlerinin hash'lerini taşıyan `alttan_yukari_sim.py` aggregate özetidir.
- Özetin `provenance` hash'leri `lora/v6_girdi_manifest.json` ve
  `rapor/arastirma/dogrulama_manifest.json` ile eşleşmelidir.
- Özet, dört modda aynı proje kümesini ve proje başına aynı satır sayısını
  taşımalıdır. Proje satırları toplamı 300 olmalıdır.
- Yeniden örnekleme birimi projedir. Her tekrarda proje sayısı kadar proje
  yerine koyarak örneklenir; seçilen projenin bütün satırları birlikte kalır.
- Her tekrarda aynı proje örneklemi beş karşılaştırmanın tamamında kullanılır.
  Böylece farklar eşlidir ve proje içindeki optimizasyon kopyaları bağımsız örnek sayılmaz.
- Nokta tahmini, proje kümeleri üzerinden satır-ağırlıklı macro token recall
  farkıdır. Aralık 2.000 tekrar ve 42 tohumla percentile yöntemiyle, doğrusal
  interpolasyon kullanılarak hesaplanır.

Karşılaştırmalar:

1. `gold - anonymised`: bütün çözümlenmiş callee adları bilinseydi bağlamın
   sağlayacağı toplam sözcüksel bilgi.
2. `gold_prediction_coverage - anonymised`: yalnız sabit v5 tahmini bulunan
   callee yuvalarında gerçek adlar kullanılsaydı görülecek sözcüksel bilgi.
3. `v5_predicted - anonymised`: aynı yuvalara sabit v5 tahmin adları yazıldığında
   gerçekten görülen sözcüksel bilgi.
4. `gold_prediction_coverage - v5_predicted`: aynı tahmin kapsamı sabitken
   gerçek callee adları ile v5 tahminleri arasındaki sözcüksel bilgi farkı.
5. `gold - gold_prediction_coverage`: v5 için tahmin bulunmayan callee
   yuvalarının eksik kapsama nedeniyle kaybettirdiği ek sözcüksel bilgi.

İkinci ve üçüncü karşılaştırmalar aynı callee yuvalarını kullandığı için
dördüncü karşılaştırma tahmin kapsamını sabit tutup gerçek adlarla tahminlerin
token-recall farkını gösterir. Bu fark semantik ad doğruluğu değildir ve bu
karşılaştırmalar modelin yeniden adlandırma başarısına eşit değildir; yalnız
bağlama eklenen hedef-token örtüşmesini ölçer.

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

Simülasyondan **önce**, kullanılan checkout'u sabitleyin:

```sh
AUDIT_COMMIT=$(git rev-parse HEAD)
test -z "$(git status --porcelain --untracked-files=no)"
```

Ardından yalnız aggregate özeti kullanın:

```sh
python3 alttan_yukari_bootstrap.py \
  --ozet /tmp/bottom-up-summary.json \
  --cikti /tmp/bottom-up-bootstrap.json \
  --audit-commit "$AUDIT_COMMIT" \
  --tekrar 2000 --tohum 42
```

`--audit-commit` mevcut `HEAD` ile aynı olmalı; araç ayrıca tüm **takipli** çalışma ağacının temiz olmasını, commit'in `alttan_yukari_sim.py` içermesini ve kodun SHA-256'sını doğrular. Rapor commit, tree ve simülatör dosyası hash'ini kaydeder. Simülasyon özeti mevcut şeması korunur. Özetin kendisi çalışma anındaki commit'i taşımadığından bu ilişki temiz checkout üzerinde **operatör beyanıdır**, kriptografik bir çalışma-zamanı imzası değildir: komutu aynı checkout'ta çalıştırın ve commit'i simülasyondan önce kaydedin. İzlenmeyen dosyalar bu temiz-ağaç kontrolüne dahil değildir. Varsayılanlar 2.000 tekrar ve seed 42'dir; komut bunları açıkça sabitler. Farklı bir yöntem önceden belirlenirse `--tekrar` ve `--tohum` değiştirilebilir. Çıktı depo dışında olmalı ve mevcut dosyanın üzerine yazılmaz.

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
