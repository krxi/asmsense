# Önek kuralı denetimi

`python3 onek_denetim.py` çıktısı. Girdi: `veri/bin/olcek/dogrulama.jsonl`, `veri/bin/olcek/egitim.jsonl`, `veri/bin/olcek/test.jsonl`.

341 proje, 82804 benzersiz ad. `hazirla_olcek.py` varsayılan kuralı (siklik) 70 projede proje adıyla ilgisiz bir öneki atıyor; bu 10247 adın (%12.4) eğitim/test hedefini değiştiriyor.

Düzeltme: `lora/hazirla_olcek.py --onek-kurali proje` (aynı eşik, önek proje adıyla ilişkili olmalı).

## Projeler

| proje | ad | siklik öneki | proje kuralı öneki | yanlış kırpılan | çakışan hedef |
|---|---:|---|---|---:|---:|
| catime | 1640 | ma | - | 1606 | 0 |
| ttgo_twatch_library | 1738 | lv | - | 1115 | 14 |
| cglm | 728 | glmc | - | 712 | 0 |
| wasm3 | 1273 | op | - | 685 | 3 |
| php-ext-xlswriter | 1525 | lxlsx | - | 589 | 0 |
| cmsis-dsp | 563 | arm | - | 557 | 0 |
| kha | 694 | hl | - | 426 | 1 |
| sqlcipher | 619 | jim | - | 407 | 7 |
| ziparchive | 387 | mz | - | 328 | 0 |
| lcui | 955 | ui | - | 322 | 0 |
| jerryscript | 449 | ecma | - | 299 | 0 |
| lovr | 480 | ma | - | 251 | 1 |
| libsodium | 597 | crypto | - | 236 | 0 |
| lunasvg | 399 | plutovg | - | 226 | 0 |
| eth.zig | 494 | secp256k1 | - | 199 | 0 |
| bare-metal-programming-guide | 279 | mg | - | 188 | 2 |
| catimg | 219 | stbi | - | 186 | 0 |
| libpostal | 498 | cmp | - | 155 | 0 |
| warp | 382 | waste | - | 147 | 0 |
| quickjs | 287 | js | - | 145 | 0 |
| mcuboot | 171 | zcbor | - | 137 | 0 |
| onedraw | 157 | stbtt | - | 122 | 0 |
| barco | 164 | arg | - | 114 | 0 |
| jansson | 224 | json | - | 104 | 2 |
| fcvvdp | 85 | cvvdp | - | 79 | 0 |
| hash_extender | 110 | buffer | - | 60 | 0 |
| wasm-micro-runtime | 64 | ocall | - | 58 | 0 |
| chia-plotter | 139 | huf | - | 55 | 0 |
| arduino-mqtt | 49 | lwmqtt | - | 49 | 0 |
| gmssl | 46 | skf | - | 46 | 0 |
| shecc | 145 | a64 | - | 45 | 0 |
| wax | 46 | yajl | - | 43 | 0 |
| hactool | 111 | lz4 | - | 38 | 0 |
| easylogger | 42 | elog | - | 36 | 1 |
| arduino-homekit-esp8266 | 57 | homekit | - | 32 | 0 |
| blurhash | 62 | stbiw | - | 27 | 0 |
| wrk2 | 74 | hdr | - | 27 | 1 |
| sajs | 60 | eat | - | 26 | 0 |
| musializer | 28 | nob | - | 25 | 0 |
| tinyusb | 63 | segger | - | 23 | 0 |
| how-to-make-a-computer-operating-system | 29 | trio | - | 19 | 0 |
| nature | 34 | ld | - | 19 | 0 |
| haywire | 47 | http | - | 16 | 0 |
| sslsplit | 42 | logger | - | 15 | 0 |
| wlipsync | 35 | pt | - | 15 | 0 |
| ixy | 30 | virtio | - | 14 | 0 |
| p2pvc | 38 | pautil | - | 14 | 0 |
| stratux | 42 | uat | - | 14 | 0 |
| craft | 29 | ring | - | 13 | 0 |
| fzy | 16 | choices | - | 12 | 0 |
| ios-webkit-debug-proxy | 35 | ht | - | 12 | 0 |
| microcheck | 26 | http | - | 12 | 0 |
| tilck | 25 | term | - | 12 | 0 |
| zclaw | 32 | telegram | - | 12 | 0 |
| photoc | 23 | review | - | 11 | 0 |
| amx | 23 | emulate | - | 10 | 0 |
| esp-homekit | 24 | mdns | - | 10 | 0 |
| traildb | 21 | pqueue | - | 10 | 0 |
| ctypes.sh | 24 | rb | - | 9 | 0 |
| dperf | 10 | config | - | 9 | 0 |
| easyhook | 9 | ud | - | 7 | 0 |
| i3 | 7 | sd | - | 7 | 0 |
| libratbag | 13 | rbnode | - | 7 | 0 |
| picomatch | 21 | emit | - | 7 | 0 |
| raddebugger | 18 | sysv | - | 7 | 0 |
| zipline | 9 | js | - | 7 | 0 |
| box64 | 6 | log | - | 6 | 0 |
| cuik | 9 | tls | - | 6 | 0 |
| esp32 | 8 | db | - | 5 | 0 |
| google-authenticator-libpam | 12 | sha1 | - | 5 | 0 |
| adam | 201 | adam | adam | 0 | 0 |
| bcc | 13 | bcc | bcc | 0 | 0 |
| carquet | 44 | carquet | carquet | 0 | 0 |
| cex | 366 | cex | cex | 0 | 0 |
| cjson | 88 | cjson | cjson | 0 | 0 |
| clipmenu | 30 | cs | cs | 0 | 0 |
| colibri | 136 | coli | coli | 0 | 0 |
| cyaml | 262 | cyaml | cyaml | 0 | 0 |
| envchain | 23 | envchain | envchain | 0 | 0 |
| facil.io | 768 | fio | fio | 0 | 2 |
| finitestateentropy | 44 | fse | fse | 0 | 0 |
| fmag | 136 | fmag | fmag | 0 | 0 |
| gdrcopy | 12 | gdr | gdr | 0 | 0 |
| guacamole-server | 149 | guac | guac | 0 | 0 |
| h2o | 227 | h2o | h2o | 0 | 0 |
| h3.c | 346 | h3 | h3 | 0 | 0 |
| hev-socks5-tunnel | 13 | hev | hev | 0 | 0 |
| iris.c | 303 | iris | iris | 0 | 2 |
| janet | 1348 | janet | janet | 0 | 5 |
| kimi-k3-in-c | 79 | k3 | k3 | 0 | 0 |
| kore | 444 | kore | kore | 0 | 0 |
| libass | 117 | ass | ass | 0 | 0 |
| libcsp | 75 | csp | csp | 0 | 0 |
| libdill | 502 | dns | dns | 0 | 0 |
| libmill | 121 | mill | mill | 0 | 0 |
| libpng | 531 | png | png | 0 | 1 |
| libsoundio | 69 | soundio | soundio | 0 | 0 |
| libucl | 316 | ucl | ucl | 0 | 0 |
| libuv | 113 | uv | uv | 0 | 0 |
| libyaml | 169 | yaml | yaml | 0 | 0 |
| lily | 1114 | lily | lily | 0 | 2 |
| liquid-dsp | 93 | liquid | liquid | 0 | 0 |
| littlefs | 201 | lfs | lfs | 0 | 0 |
| lsquic | 711 | lsquic | lsquic | 0 | 6 |
| lz4 | 170 | lz4 | lz4 | 0 | 0 |
| lzfse | 47 | lzfse | lzfse | 0 | 0 |
| markdown-wasm | 131 | md | md | 0 | 0 |
| mbedtls | 2056 | mbedtls | mbedtls | 0 | 52 |
| md4c | 128 | md | md | 0 | 0 |
| melon | 1552 | mln | mln | 0 | 1 |
| mimalloc | 736 | mi | mi | 0 | 0 |
| minifb | 70 | mfb | mfb | 0 | 0 |
| mu_json_x | 75 | mu | mu | 0 | 0 |
| nanocolor | 36 | nc | nc | 0 | 0 |
| netcode | 162 | netcode | netcode | 0 | 0 |
| nnpack | 35 | nnp | nnp | 0 | 0 |
| painterengine | 4446 | px | px | 0 | 2 |
| phptrace | 17 | pt | pt | 0 | 0 |
| preeny | 52 | preeny | preeny | 0 | 0 |
| qaws | 326 | qaws | qaws | 0 | 0 |
| qoi | 7 | qoi | qoi | 0 | 0 |
| s2n-tls | 126 | s2n | s2n | 0 | 0 |
| sc | 264 | sc | sc | 0 | 0 |
| sfud | 29 | sfud | sfud | 0 | 0 |
| sigar | 66 | sigar | sigar | 0 | 1 |
| silk-v3-decoder | 151 | skp | skp | 0 | 0 |
| skynet | 217 | skynet | skynet | 0 | 0 |
| sparkey | 54 | sparkey | sparkey | 0 | 0 |
| spiffs | 101 | spiffs | spiffs | 0 | 1 |
| tic-80 | 132 | tic | tic | 0 | 0 |
| tinymaix | 10 | tm | tm | 0 | 0 |
| toks | 436 | toks | toks | 0 | 3 |
| usockets | 118 | us | us | 0 | 0 |
| vlfeat | 353 | vl | vl | 0 | 0 |
| voxtral.c | 85 | vox | vox | 0 | 0 |
| wob | 9 | wob | wob | 0 | 0 |
| xxhash | 62 | xxh3 | xxh3 | 0 | 0 |
| yajl | 12 | yajl | yajl | 0 | 0 |
| yara | 491 | yr | yr | 0 | 1 |
| yyjson | 62 | yyjson | yyjson | 0 | 0 |
| zerocast | 9 | zerocast | zerocast | 0 | 0 |
| zlog | 233 | zlog | zlog | 0 | 0 |
| zstd | 1034 | zstd | zstd | 0 | 0 |

Tabloda olmayan 198 projede iki kural da önek bulmuyor.

## Yayın sınırı

Satır düzeyinde fonksiyon adı, kaynak veya assembly örnekleri yayımlanmaz;
bu rapor yalnız toplulaştırılmış denetim sonuçlarını tutar.

## Çakışmalar (kırpma sonrası aynı hedef)

- ttgo_twatch_library: `fs_close` / `lv_fs_close`
- ttgo_twatch_library: `fs_dir_close` / `lv_fs_dir_close`
- ttgo_twatch_library: `fs_dir_open` / `lv_fs_dir_open`
- ttgo_twatch_library: `fs_dir_read` / `lv_fs_dir_read`
- ttgo_twatch_library: `fs_open` / `lv_fs_open`
- ttgo_twatch_library: `fs_read` / `lv_fs_read`
- ttgo_twatch_library: `fs_remove` / `lv_fs_remove`
- ttgo_twatch_library: `fs_rename` / `lv_fs_rename`
- ttgo_twatch_library: `fs_seek` / `lv_fs_seek`
- ttgo_twatch_library: `fs_size` / `lv_fs_size`
- ttgo_twatch_library: `fs_tell` / `lv_fs_tell`
- ttgo_twatch_library: `fs_trunc` / `lv_fs_trunc`
- ttgo_twatch_library: `fs_write` / `lv_fs_write`
- ttgo_twatch_library: `lv_theme_apply` / `theme_apply`
- wasm3: `Call` / `op_Call`
- wasm3: `Op_ContinueLoop` / `op_ContinueLoop`
- wasm3: `XXH64_digest` / `Xxh64_Digest`
- kha: `gc_major` / `hl_gc_major`
- sqlcipher: `DictAddElement` / `Jim_DictAddElement`
- sqlcipher: `JimCreateCommand` / `Jim_CreateCommand`
