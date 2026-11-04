# Önek kuralı denetimi

`python3 onek_denetim.py` çıktısı. Girdi: `veri/test/cyaml.jsonl`, `veri/test/mu_json_x.jsonl`, `veri/test/picomatch.jsonl`, `veri/test/sajs.jsonl`, `veri/test/tomlc17.jsonl`, `veri/test.jsonl`, `veri/zlib-v3.jsonl`, `veri/zlib.jsonl`.

6 proje, 661 benzersiz ad. `hazirla_olcek.py` varsayılan kuralı (siklik) 2 projede proje adıyla ilgisiz bir öneki atıyor; bu 33 adın (%5.0) eğitim/test hedefini değiştiriyor.

Düzeltme: `lora/hazirla_olcek.py --onek-kurali proje` (aynı eşik, önek proje adıyla ilişkili olmalı).

v4 verisi (`veri/bin/olcek/`) bu girdide yok; 341 projenin tamamı için `python3 onek_denetim.py veri/bin/olcek/*.jsonl -o rapor/ONEK_DENETIM_V4.md` çalıştırılmalı.

## Projeler

| proje | ad | siklik öneki | proje kuralı öneki | yanlış kırpılan | çakışan hedef |
|---|---:|---|---|---:|---:|
| sajs | 60 | eat | - | 26 | 0 |
| picomatch | 22 | emit | - | 7 | 0 |
| cyaml | 263 | cyaml | cyaml | 0 | 0 |
| mu_json_x | 79 | mu | mu | 0 | 0 |

Tabloda olmayan 2 projede iki kural da önek bulmuyor.

## Yayın sınırı

Satır düzeyinde fonksiyon adı/hedef örnekleri yayımlanmaz. Bu rapor yalnız
ölçüm kapsamını, toplulaştırılmış sayıları ve yeniden üretim komutunu tutar.
