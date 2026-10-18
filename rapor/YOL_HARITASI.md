# Yol haritası

Tarih: 11 Ekim 2026 · main `219b8bc` sonrası. Bu belge sıradaki işleri, her işin çıkış ölçütünü ve
karar kurallarını sabitler. Olasılıklar ya repodaki verilerden hesaplandı (yöntemi yanında) ya da
öznel önseldir (öyle işaretli). Yeni bir sonuç geldiğinde ilgili satır güncellenir; geçmiş satırlar silinmez.

## Bugünkü durum

| Alan | Durum |
|---|---|
| Küçük model | Qwen3-8B + LoRA v6: test2000 ad F1 0,135; eval115 0,135. v5 sırasıyla 0,124 ve 0,155 |
| Büyük model | mimo + çağrı bağlamı 0,167 (snkv dışı 0,190); + decompile 0,192 (0,214) |
| v6 − v5 | test2000 +0,011 [+0,002; +0,018]; eval115 −0,020 [−0,057; +0,020], proje-kümeli eşli bootstrap |
| Veri bütünlüğü | Bölümler ayrık; snkv ⊃ sqlite istisnası açıklandı ([V6_VERI_DENETIMI.md](arastirma/V6_VERI_DENETIMI.md)) |
| v6 | Eğitim, validation seçimi, iki nihai ölçüm ve açıklama denetimi tamamlandı; adaptör ve tam duyarlıklı kanıt yayımlandı |
| Altyapı | CI yeşil; doğrudan push'ta yeni dosyalar da lint'leniyor; release künyesi ve atıf dosyaları hazır |

## Fazlar

| Faz | İş | Çıkış ölçütü | Durum |
|---|---|---|---|
| F0 | Altyapı ve bütünlük | CI yeşil, v6 verisi denetlendi, README'de istisna açıklandı | tamam |
| F1 | v6 tam eğitimi (`molab/egit.py`, `VERI_SURUM=v6`) | Tam duyarlıklı ad raporu ve eşlenmiş açıklama denetimi yayımlandı | tamam |
| F2 | MSR 2027 Data & Tool Showcase (özet 5 Kasım, makale 10 Kasım AoE) | Taslak [`makale/msr2027`](../makale/msr2027) gönderildi; Zenodo DOI alındı | v6 sonucu işlendi; gönderim bekliyor |
| F3 | Mühürlü v7 testi | ≥15 proje, Qwen3 çıkışından (Nisan 2025) sonra açılmış, ≤200 yıldız; liste hash'i ölçümden önce commit'lendi; nihai modeller bir kez ölçüldü | açılmadı |
| F4 | Yöntem makalesi (koşullu) | Yalnız BAR 2027 çağrısı 15 Aralık'a kadar çıkarsa; yoksa DIMVA veya ICSE çalıştayları | koşula bağlı |
| F5 | Bakım | README son durum, release'ler DOI'li, açık PR yok | sonda |

`lora/v6_dogrulama.py` (eşit bütçeli asm/combined pilotu) tam v6 − v5 koşusundan daha dar bir nedensel
soruyu yanıtlar: aynı bütçede pseudocode eklemenin etkisi. İki ikili kanıt hash'i hâlâ sabitlenmediği için
pilot koşulmadı. Tam koşu girdi, sistem istemi ve ortalama token bütçesini birlikte değiştirdiğinden bu
pilotun yerini tutmaz; yeni GPU harcaması için öncelik değildir.

## Karar kuralları

| Koşul | Karar |
|---|---|
| v6 valid_300 (gömülü-ad satırları hariç) ≥ v5 + 0,010 | Decompile v7'de kalır; bu özel dışlama için yayımlanmış tam duyarlıklı fark yok, karar tetiklenmedi |
| Aynı fark < +0,005 | Decompile bırakılır; bu özel dışlama için yayımlanmış tam duyarlıklı fark yok, karar tetiklenmedi |
| 1 Kasım'da MSR taslağı gönderilebilir durumda değil | MSR bırakılır; arXiv + F4 |
| v6 test2000 ≥ 0,14 | Gerçekleşmedi (0,135); v6 karışık sonuçlu, compute-eşlenmemiş karşılaştırma olarak raporlanır |
| 15 Aralık'ta BAR 2027 çağrısı yok | F4 yedek venue'ya kayar |
| Yeni araç/protokol fikri | Önce validation'da, sabit başarı/zarar kapılarıyla; geliştirmede kullanılan testlere göre seçim yok |

## Tahmin sonrası kayıt

Önceki olasılıklar sonuç görülmeden yazılmış önsellerdir; geçmişi silmemek için aşağıda korunur.
Gerçekleşen iki ana olay:

- test2000'de v6 − v5 farkı +0,0111 ve proje-kümeli %95 aralık [+0,002; +0,018]: sıfırı dışladı;
- v6 test2000 F1 0,135: 0,14 eşiğini aşmadı. eval115 farkı −0,0201 ve aralığı
  [−0,057; +0,020], dolayısıyla ikinci küçük kontrolde kazanım doğrulanmadı.

Bu iki sonuç birlikte decompile'ın küçük modelde genel bir kazanım sağladığını kanıtlamaz. Sıradaki model
kalitesi işi, mühürlü v7 seti açılmadan önce validation'da açıklama hedeflerini ve string'siz işlevleri
iyileştiren tek değişkenli bir deney olmalıdır. v6'nın 1,39× daha uzun ortalama konuşmaları nedeniyle
compute-eşlenmiş asm/combined pilotu yalnız ek GPU bütçesi ayrılırsa anlamlıdır.

## Önsel olasılıklar (sonuç öncesi kayıt)

| Olay | Olasılık | Dayanak |
|---|---|---|
| v6 − v5 eşli fark proje-kümeli %95 GA'da sıfırı dışlar | 0,62–0,76 | Sonuçtan önce: v5 − v1 eşli farkının proje-kümeli SE'si 0,0054 (test2000, 4.000 çekim), anlamlılık eşiği ≈ +0,011. Önsel kazanç: büyük modelde decompile göreli +%15; küçük modele %11 (alt sınır) ile %15 (üst sınır) aktarıldı, belirsizlik ±0,010 |
| v6 test2000 ≥ 0,14 | 0,42–0,60 | Sonuçtan önce: aynı önsel |
| 6 ay içinde küçük model ≥ 0,167 (mimo + bağlam) | 0,09–0,15 | Öznel kalem kazanımları (decompile, tüm veri/2 epoch, 9B taban, alttan-yukarı adlar; RL eklenirse üst sınır), azalan getiri katsayısı 0,7 |
| MSR 2027 Data & Tool Showcase kabulü (gönderilirse) | ≈0,50 | Ölçülen taban oran: HotCRP "N of M accepted" 2023 22/42, 2026 28/58 (son iki yıl %50); 2021–26 toplam 100/172 = %58 |
| BAR 2027 düzenlenir | ≈0,85 | 2018–2026 her yıl düzenlendi (Laplace 0,91); 11 Ekim'de çağrı yok |
| BAR kabulü (gönderilirse) | ≈0,62 | Ölçülen taban oran: HotCRP 2019–2024 + 2026 toplam 57/89 = %64 |
| Mart 2027'ye kadar ≥1 hakemli kabul (MSR, sonra koşullu BAR) | ≈0,64 | Yukarıdaki oranlar + öznel gönderim olasılıkları (MSR 0,70, BAR 0,75) ve emek; Monte Carlo 20.000 çekim. Yalnız MSR: ≈0,36 |

Sonuç: "küçük model büyük modeli yakalar" iddiası önümüzdeki 6 ayda düşük olasılıklı. Yayınlar
ezbere dayanıklı benchmark, denetlenmiş veri ve dürüst küçük-model taban çizgisi üzerine kurulur.

## Yeniden üretim açıkları

- v4'ün 473 projelik aday listesi (url, commit, rol) git'te yok (`.notlar/aday-projeler.json`); F2 öncesi
  commit'lenmeli. HF'deki kaynak tablosunda url ve rol eksik.
- Mühürlü test (F3) olmadan bütün sonuçlar "geliştirmede kullanılmış ölçüt" etiketi taşır.
