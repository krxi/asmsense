"""Build the static name index for the asmsense v4 dataset.

Inputs (all public):
  - krxi123/asmsense on Hugging Face, config v4: data/v4/{train,validation,test}-00000.jsonl.gz
  - krxi123/asmsense-lora-v6 on Hugging Face: test_sabit-sonuc.jsonl (v6 predictions, 2,000 test rows)

Output (v1/):
  meta.json            counts, shard counts, input hashes, license table
  tokens.json.gz       every name token with the number of names that contain it (for prefix completion)
  t/NN.json.gz         token -> [[name, record count], ...] for names containing it (TOKEN_SHARDS files)
  n/NNN.json.gz        exact name -> list of records               (NAME_SHARDS files)

A browser loads one token shard and one name shard per lookup. Shards are gzip-compressed JSON;
the client decompresses them with DecompressionStream. The shard of a key is fnv1a32(key) % N,
the same function as in lib/asmsense-search.js.

Usage: python3 tools/build_index.py --v4 DIR --v6 FILE --out v1
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

NAME_SHARDS = 512
TOKEN_SHARDS = 64
ASM_LINES = 24       # instructions kept per record; the full body is in the dataset
CONTEXT_CHARS = 320  # call-context excerpt
SPLITS = ("train", "validation", "test")
# The dataset keeps a few license notes in Turkish; the index shows them in English.
LICENSE_EN = {
    "BSD-2-Clause (lib/ dizini; programs/ GPL, kullanilmaz)": "BSD-2-Clause (lib/ only; GPL programs/ not used)",
    "Apache-2.0 (Apache-2.0 OR GPL-2.0+ ikili lisansin Apache secenegi)": "Apache-2.0 (Apache option of Apache-2.0 OR GPL-2.0+)",
    "Public domain (SQLite); mirror yalniz CMake sarmalayicisini BSD-3 lisanslar":
        "Public domain (SQLite); the mirror's BSD-3 covers only its CMake wrapper",
    "BSD-2-Clause (kutuphane; cli/ GPL, kullanilmaz)": "BSD-2-Clause (library only; GPL cli/ not used)",
    "BSD-3-Clause (BSD/GPLv2 ikili lisansin BSD secenegi)": "BSD-3-Clause (BSD option of BSD/GPLv2)",
    "zlib": "Zlib",
}

TOKEN_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")


def context_en(s: str) -> str:
    """The call context is stored with two Turkish words: "(N komut)" and "çağırır" (calls)."""
    return re.sub(r"\((\d+) komut\)", r"(\1 insns)", s).replace(": çağırır ", ": calls ")


def fnv1a32(s: str) -> int:
    h = 0x811C9DC5
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def tokens(name: str) -> list[str]:
    """Split an identifier into lowercase tokens: snake_case, camelCase and digits.
    Letter+digit runs such as crc32 or sha256 are kept together as well as split."""
    out = []
    for part in re.split(r"[^A-Za-z0-9]+", name):
        if not part:
            continue
        pieces = TOKEN_RE.findall(part)
        out.extend(p.lower() for p in pieces)
        # also keep letter+digit pairs such as crc32, base64, sha256 as one token
        for x, y in zip(pieces, pieces[1:]):
            if x.isalpha() and y.isdigit():
                out.append((x + y).lower())
    seen, uniq = set(), []
    for t in out:
        # single letters and bare numbers match too much to be useful
        if len(t) < 2 or t.isdigit():
            continue
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_gz(path: Path, obj) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    # mtime=0 keeps the output byte-identical across rebuilds
    with open(path, "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", compresslevel=9, mtime=0) as g:
        g.write(raw)
    return path.stat().st_size


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v4", type=Path, required=True, help="directory with the three v4 .jsonl.gz files")
    ap.add_argument("--v6", type=Path, required=True, help="test_sabit-sonuc.jsonl from krxi123/asmsense-lora-v6")
    ap.add_argument("--out", type=Path, default=Path("v1"))
    a = ap.parse_args()

    v6 = {}
    for line in a.v6.open():
        d = json.loads(line)
        v6[d["id"]] = {"name": d["tahmin"], "f1": round(d["f1"], 3), "en": d.get("aciklama_en") or ""}

    licenses: list[str] = []
    lic_idx: dict[str, int] = {}
    by_name: dict[str, list] = defaultdict(list)
    projects = set()
    inputs = {}
    n = 0
    for split in SPLITS:
        p = a.v4 / f"{split}-00000.jsonl.gz"
        inputs[p.name] = sha256(p)
        for line in gzip.open(p, "rt", encoding="utf-8"):
            d = json.loads(line)
            n += 1
            projects.add(d["proje"])
            lic = d.get("lisans") or "unknown"
            lic = LICENSE_EN.get(lic, lic)
            if lic not in lic_idx:
                lic_idx[lic] = len(licenses)
                licenses.append(lic)
            body = d["asm"].split("\n")
            rec = {
                "project": d["proje"],
                "file": d["dosya"],
                "rev": d["surum"][:12],
                "opt": d["opt"],
                "split": split,
                "insns": d["komut_sayisi"],
                "exported": bool(d.get("export")),
                "license": lic_idx[lic],
                "asm": "\n".join(body[:ASM_LINES]),
                "asm_lines": len(body),
                "context": context_en(d.get("baglam") or "")[:CONTEXT_CHARS],
            }
            if d["id"] in v6:
                rec["v6"] = v6[d["id"]]
            by_name[d["ad"]].append(rec)
    inputs[a.v6.name] = sha256(a.v6)

    # exact-name shards (key: name as written; lookup is case-sensitive, the client also tries the lowercase key)
    name_shards: list[dict] = [dict() for _ in range(NAME_SHARDS)]
    token_map: dict[str, set] = defaultdict(set)
    for name, recs in by_name.items():
        recs.sort(key=lambda r: (r["project"], r["file"], r["opt"]))
        name_shards[fnv1a32(name.lower()) % NAME_SHARDS].setdefault(name, recs)
        for t in tokens(name):
            token_map[t].add(name)

    sizes_n = [write_gz(a.out / "n" / f"{i:03d}.json.gz", s) for i, s in enumerate(name_shards)]

    token_shards: list[dict] = [dict() for _ in range(TOKEN_SHARDS)]
    for t, names in token_map.items():
        # names sorted by how often they occur, then alphabetically
        token_shards[fnv1a32(t) % TOKEN_SHARDS][t] = [[x, len(by_name[x])] for x in
                                                      sorted(names, key=lambda x: (-len(by_name[x]), x))]
    sizes_t = [write_gz(a.out / "t" / f"{i:02d}.json.gz", s) for i, s in enumerate(token_shards)]

    vocab = sorted(([t, len(ns)] for t, ns in token_map.items()), key=lambda x: x[0])
    size_v = write_gz(a.out / "tokens.json.gz", vocab)

    meta = {
        "format": 1,
        "built": date.today().isoformat(),
        "dataset": "krxi123/asmsense (config v4)",
        "predictions": "krxi123/asmsense-lora-v6 test_sabit-sonuc.jsonl",
        "records": n,
        "names": len(by_name),
        "projects": len(projects),
        "tokens": len(token_map),
        "name_shards": NAME_SHARDS,
        "token_shards": TOKEN_SHARDS,
        "asm_lines": ASM_LINES,
        "context_chars": CONTEXT_CHARS,
        "licenses": licenses,
        "inputs_sha256": inputs,
        "bytes": {"names_max": max(sizes_n), "names_total": sum(sizes_n),
                  "tokens_max": max(sizes_t), "tokens_total": sum(sizes_t), "vocab": size_v},
    }
    (a.out / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    print(json.dumps(meta["bytes"]), n, len(by_name), len(token_map))


if __name__ == "__main__":
    main()
