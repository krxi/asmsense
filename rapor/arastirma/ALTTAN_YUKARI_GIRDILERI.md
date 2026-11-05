# Bottom-up doğrulama deneyi: sabit girdileri hazırlama

Bu yardımcı, açık [PR #25](https://github.com/krxi/asmsense/pull/25) içindeki CPU-only
lexical-context denetiminin üç sabit validation girdisini, yayımlanmış kaynaklardan sabit SHA-256 ile alır.
Model, Ghidra, API anahtarı veya GPU çağrısı yapmaz.

## İndirilen girdiler

| Yerel dosya | Kaynak | Doğrulama | Kapsam |
|---|---|---|---:|
| `valid_300-v6.jsonl` | [`asmsense-data` v6 release](https://github.com/krxi/asmsense-data/releases/tag/v6) | Arşiv SHA-256 `e1286104…a7c8c201`; üye SHA-256 `1148a533…77010256` | 300 validation satırı |
| `validation-v4.jsonl` | [HF v4 dataset revision `6e1eb5e`](https://huggingface.co/datasets/krxi123/asmsense/tree/6e1eb5e44c3114a06c0b4cac9b38540c33e322e0/data/v4) | Açılmış JSONL SHA-256 `7516244e…f1beef3` | 19.770 validation satırı |
| `valid300-v5-predictions.jsonl` | [asmsense commit `15e3b28`](https://github.com/krxi/asmsense/tree/15e3b28f1be387d0e8655edd838e1c32f9d348d5/sonuc) | SHA-256 `88f7bfb3…e14e4faf`; sabit commit ve manifest | 300 validation tahmini |

GitHub release tek bir v6 ZIP sunduğu için arşivin tamamı geçici indirilir; araç
ZIP içinden yalnız `valid_300.jsonl` üyesini açar. Train/test/eval üyelerinin içerikleri
açılmaz veya okunmaz. V5 tahmin dosyası yalnız sabit `15e3b28` commitindeki
`valid300` validation çıktısından alınır; test/eval tahminleri istenmez. Geçici ZIP
işlem sonunda bellekten bırakılır.

## Çalıştırma

Depo kökünden, henüz var olmayan ve depo dışında bir dizin seçin:

```sh
python3 indir_dogrulama.py --cikti-dir ../asmsense-validation
```

Araç yalnız şu dosyaları yazar:

- `../asmsense-validation/valid_300-v6.jsonl`
- `../asmsense-validation/validation-v4.jsonl`
- `../asmsense-validation/valid300-v5-predictions.jsonl`
- `../asmsense-validation/manifest.json` (toplu sayaçlar ve SHA-256; satır verisi yok)

Linux ve macOS'ta staging dizini atomik no-replace rename ile yayımlanır; arada boş
hedef dizin oluşturulsa bile üzerine yazılmaz. Bu işlemi desteklemeyen platformlarda
araç fail-closed durur. Ağ, hash, satır sayısı veya arşiv üye kontrolü başarısızsa
kısmi çıktı bırakılmaz. V4/v6 ham satırları kendi `lisans` alanlarını korur;
V5 dosyası yalnız sabitlenmiş model tahminidir. Üç dosyayı da depo dışında,
yalnız validation audit girdisi olarak tutun; eğitim/prompt örneğine veya yayımlanan
belgeye kopyalamayın.
Lisanslar için `veri/LISANSLAR.md` geçerlidir.

Üç dosya hazır olduktan ve PR #25 birleştirildikten sonra aşağıdaki validation-only
`alttan_yukari_sim.py` komutu çalıştırılabilir:

```sh
python3 alttan_yukari_sim.py --prompts ../asmsense-validation/valid_300-v6.jsonl --raw ../asmsense-validation/validation-v4.jsonl --predictions ../asmsense-validation/valid300-v5-predictions.jsonl --output ../asmsense-validation/bottom-up-summary.json
```

Sonuç yalnız aggregate olmalı; satır export'u kullanılmamalıdır. Bu PR'da gerçek
validation deneyi **not run**.

## Sınırlar

- Bu araç benchmark üretmez, yeniden bölmez veya puanlamaz.
- `veri/test/`, `veri/test.jsonl`, `lora/test_sabit_idler.txt`, test/eval üyeleri ve
  Hugging Face/Kaggle veri kümeleri değiştirilmez.
- Test üyesi açma sayısı manifestte `0` olarak kaydedilir.
- Testler sentetik ZIP/GZIP içerikleri kullanır; ağ erişimi gerektirmez.
