# Sistem istemi örneği: validation-only ablation

## Neden bu deney?

18 Ekim 2026'da yayımlanan eğitilmemiş Qwen3-8B tabanı, v6 final değerlendirmesiyle
aynı sistem istemi ve girdileri kullandı. Arşivlenmiş ölçümde sistem istemindeki
tek JSON örneğinin adını 2.000 sabit test satırının 768'inde aynen, 1.188'inde
içeren biçimde üretti. Bu, tabanın fonksiyonu anlamadan örnek yanıtı kopyalamasına
işaret eden bir karıştırıcıdır; **yeni bir model kazancı veya prompt değişikliği
kanıtı değildir**.

Tarihsel ölçümün kaydı:

- Ölçülen checkout: [`fd64c1a8201b396300b88602f87702b81d1e5dfc`](https://github.com/krxi/asmsense/commit/fd64c1a8201b396300b88602f87702b81d1e5dfc).
- Üretim protokolü: [`molab/TABAN_PROTOKOL.md`](../../molab/TABAN_PROTOKOL.md), 18 Ekim 2026; [notebook](../../molab/taban.py).
- Üretim komutu: `python3 molab/taban.py` (Marimo arayüzünde Başlat); arşivlenmiş tahminlerin aggregate raporu: `python3 olcum_taban.py --veri /path/to/veri-v6 -o /tmp/olcum-taban.json`.
- Sabit test: `test_sabit`, n=2.000; kanonik `taban.f1` = 0,0359155483; öneksiz F1 = 0,0364703102; örnek adı tam kopya 768/2.000, içeren tahmin 1.188/2.000.
- Küçük kontrol: `eval115`, n=115; kanonik F1 = 0,0308350587; öneksiz F1 = 0,0329054520; tam kopya 50/115, içeren tahmin 72/115.

Skorlayıcı kaynakları: [taban.py::f1](../../taban.py), [olcum_v6.py::oneksiz](../../olcum_v6.py) ve [aciklama_degerlendir.py::bootstrap_farki](../../aciklama_degerlendir.py).

Bu sayılar yalnız tarihsel test ölçümünü tanımlar. Bu PR test dosyalarını okumaz,
puanlamaz veya prompt seçimi için kullanmaz. Yeni karşılaştırma yalnız sabit
v6 `valid_300` üzerinde yapılır.

## Deney

`molab/istem_ornegi_ablasyonu.py` iki eşli kolu aynı temel modelde, adaptörsüz
çalıştırır:

1. **Tarihsel istem:** v6 sistem mesajı bayt düzeyinde değişmeden kalır.
2. **Örnek değerleri yok:** aynı sistem mesajındaki tek örnek JSON nesnesinin
   değerleri şema yer tutucularıyla değiştirilir. Anahtarlar, sıra, görev
   yönergesi, kullanıcı assembly/bağlam/decompile metni ve üretim şeması korunur.

Değişiklik yalnız inference sırasında bellekte yapılır. Tarihsel prompt, eğitim
satırları, assistant hedefleri, scorer ve veri şeması değişmez. İki kolda da
yalnız ilk iki mesaj modele verilir; validation hedef mesajı prompt'a eklenmez.

Girdi, v6 release'indeki 300 satırlık `valid_300.jsonl` olmalıdır. Betik
[`lora/v6_girdi_manifest.json`](../../lora/v6_girdi_manifest.json) içindeki `valid` SHA-256 değerini doğrular,
satırları [`lora/v6_dogrulama.py`](../../lora/v6_dogrulama.py)::`sema_dogrula` ile denetler ve tam 300 benzersiz
kimlik ister. Dosya adıyla split seçilmez. Beklenen `valid` dosya SHA-256 değeri `45ed0960b03453f6a2eb45a118cc68bff3ff50ae22afec1849d023633dea90ad`'dır. Başka dosya, test/eval115 dahil,
hash uyuşmadığı için reddedilir.

### Çalıştırma

Önce veri arşivini [v6 release](https://github.com/krxi/asmsense-data/releases/tag/v6)
içinden yerel olarak açın. Arşiv SHA-256:
`e1286104e59860a34fc18fe908ccadc3896b4db40fe1a5a75253aa9cc7a8c201`.
Modeli [resmî Qwen3-8B deposundan](https://huggingface.co/Qwen/Qwen3-8B/tree/b968826d9c46dd6066d109eabc6255188de91218)
aynı revision ile önceden indirin; model kartındaki lisans Apache-2.0'dır.
Kod [MIT](../../LICENSE) lisanslıdır. Veri release'ini yeniden dağıtmayın; kaynak proje lisansları ve
`lisans` metaverisi için [veri/LISANSLAR.md](../../veri/LISANSLAR.md) geçerlidir.
Betik ağ erişimini kapalı tutar ve yalnız yerel snapshot kabul eder.

Planı GPU olmadan doğrulayın:

```sh
python3 molab/istem_ornegi_ablasyonu.py --validation /path/to/valid_300.jsonl
```

İsteğe bağlı GPU ortamı (Python 3.11+):

```sh
python3 -m pip install -r molab/requirements-prompt-ablation.txt
python3 molab/istem_ornegi_ablasyonu.py \
  --validation /path/to/valid_300.jsonl \
  --model-dir /path/to/huggingface/snapshots/b968826d9c46dd6066d109eabc6255188de91218 \
  --output /tmp/asmsense-prompt-ablation/aggregate.json --run
```

Yalnız aggregate JSON yazılır; satır tahminleri bellekte tutulur ve diske
kaydedilmez. Çıktı yolu depo dışında olmalı ve mevcut olmamalıdır.

## Önceden belirlenmiş sınırlar ve başarı ölçütü

- Tek BF16 CUDA GPU; en az 24 GiB toplam ve 20 GiB boş VRAM. Referans koşu
  RTX PRO 6000 96 GB idi; 24 GiB alt sınırı farklı GPU'da doğrulanmış değildir.
- Batch 1, girdi en çok 3.072 token, üretim en çok 160 token; kesme veya örnek
  düşürme yok. Tam 300 satır × 2 kol = 600 üretim.
- `transformers==5.3.0`, `torch==2.11.0+cu130`, greedy üretim,
  `enable_thinking=False`, SDPA. Model revision sabittir; adaptör yoktur.
- Ana metrik değişmeyen kanonik `taban.f1`; öneksiz F1 yanında raporlanır.
  Aynı projeler birlikte örneklenerek eşli proje bootstrap (2.000 tekrar,
  tohum 42) hesaplanır.
- Örneksiz kol ancak kanonik F1 farkı en az +0,010 ve %95 aralığın alt sınırı
  sıfırın üstündeyse başarılı sayılır; öneksiz F1 farkı negatif olmamalı ve
  geçerli JSON oranı düşmemelidir. Bu, prompt değişikliği için otomatik izin
  değildir; yeni prompt'un eğitilmiş adaptörde ayrıca validation değerlendirmesi
  ve ayrı PR gerekir.

## Maliyet tahmini ve durum

[TABAN_PROTOKOL.md](../../molab/TABAN_PROTOKOL.md) tarihsel aynı-GPU sürelerini
`test_sabit` için 2.285 sn / 2.000 satır ve `eval115` için 130 sn / 115 satır
olarak kaydeder (ölçülen commit yukarıda). Daha yavaş oranı 600 üretime uygularsak
yaklaşık 686 sn, yani 11,4 dakika veya 0,19 GPU-saat eder; model yükleme süresi
hariçtir. Bu yalnız tahmindir, validation üzerinde ölçülmüş süre değildir.
Ücretli servis başlatılmaz.

**Bu PR'da GPU çıkarımı not run; eğitim not run; test puanlama not run.**
Başarı/başarısızlık veya F1 kazancı iddiası yoktur. Sonraki adım, maintainer
incelemesinden sonra yalnız bu sabit validation karşılaştırmasını çalıştırmak;
sonuca göre tarihsel prompt'u değiştirmeden devam etmek veya ayrı bir prompt
tasarım PR'ı önermektir.
