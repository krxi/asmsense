"""Build the browse tree and call graph for the asmsense v4 dataset.

Output (next to the name index, in v1/):
  projects.json.gz   one row per project: [name, license, files, functions, records]
  p/<project>.json.gz
      files: [file, ...]
      fns:   one entry per (file, function name):
             [name, file index, optimization levels present, instructions at the shown level,
              shown level, callees in the dataset (fn indices), callees not in the dataset, library calls]

Calls are read from the disassembly of one build of each function: -O0 when it exists, otherwise the
first of -O1, -Os, -O2, -O3. Inside a build, other project functions are named sub_XXXX; a call resolves
to a name when a record with that sub_XXXX exists for the same project, file and level. About a third
of the internal calls resolve; for the others the call context still gives their size and library
calls, which are kept as [instructions, [library calls]].

Usage: python3 tools/build_tree.py --v4 DIR --out v1
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from build_index import LICENSE_EN, SPLITS, write_gz

OPT_ORDER = ["-O0", "-O1", "-Os", "-O2", "-O3"]
CALL_RE = re.compile(r"^call\s+([A-Za-z_.$@][\w.$@]*)", re.M)
CTX_RE = re.compile(r"^(sub_[0-9a-f]+) \((\d+) (?:komut|insns)\): (?:çağırır|calls) (.+)$", re.M)
CTX_SIZE_RE = re.compile(r"^(sub_[0-9a-f]+) \((\d+) (?:komut|insns)\)", re.M)
NOT_A_TARGET = {"qword", "dword", "word", "byte", "ptr"}
MAX_EXT = 12


def library_calls(asm: str) -> list[str]:
    out = []
    for c in CALL_RE.findall(asm):
        if c.startswith("sub_") or c in NOT_A_TARGET or re.fullmatch(r"r\w+|e\w\w", c):
            continue
        if c not in out:
            out.append(c)
    return out[:MAX_EXT]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v4", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("v1"))
    a = ap.parse_args()

    # (project, file, opt) -> {sub_id: name};  (project, file, name) -> {opt: record}
    ids: dict[tuple, dict] = defaultdict(dict)
    rows: dict[tuple, dict] = defaultdict(dict)
    lic: dict[str, Counter] = defaultdict(Counter)
    for split in SPLITS:
        for line in gzip.open(a.v4 / f"{split}-00000.jsonl.gz", "rt", encoding="utf-8"):
            d = json.loads(line)
            key = (d["proje"], d["dosya"], d["opt"])
            ids[key][d["kimlik"]] = d["ad"]
            rows[(d["proje"], d["dosya"], d["ad"])][d["opt"]] = d
            l = d.get("lisans") or "unknown"
            lic[d["proje"]][LICENSE_EN.get(l, l)] += 1

    by_project: dict[str, list] = defaultdict(list)
    for (proj, file, name), opts in rows.items():
        by_project[proj].append((file, name, opts))

    table = []
    sizes = []
    for proj in sorted(by_project, key=str.lower):
        items = sorted(by_project[proj], key=lambda x: (x[0], x[1].lower()))
        files = sorted({f for f, _, _ in items})
        fidx = {f: i for i, f in enumerate(files)}
        pos = {(f, n): i for i, (f, n, _) in enumerate(items)}
        fns = []
        for file, name, opts in items:
            shown = next(o for o in OPT_ORDER if o in opts)
            d = opts[shown]
            sub_names = ids[(proj, file, shown)]
            ctx = d.get("baglam") or ""
            sizes_ctx = {s: int(n) for s, n in CTX_SIZE_RE.findall(ctx)}
            calls_ctx = {s: [c.strip() for c in cs.split(",") if not c.strip().startswith("sub_")]
                         for s, _, cs in CTX_RE.findall(ctx)}
            inside, outside = [], []
            for c in dict.fromkeys(re.findall(r"^call\s+(sub_[0-9a-f]+)", d["asm"], re.M)):
                callee = sub_names.get(c)
                if callee is not None and (file, callee) in pos and callee != name:
                    inside.append(pos[(file, callee)])
                elif callee is None:
                    outside.append([sizes_ctx.get(c, 0), calls_ctx.get(c, [])[:6]])
            fns.append([name, fidx[file], "".join(o[2:] for o in OPT_ORDER if o in opts), d["komut_sayisi"],
                        shown[2:], inside, outside, library_calls(d["asm"])])
        sizes.append(write_gz(a.out / "p" / f"{proj}.json.gz", {"project": proj, "files": files, "fns": fns}))
        recs = sum(len(o) for _, _, o in items)
        table.append([proj, lic[proj].most_common(1)[0][0], len(files), len(items), recs])

    write_gz(a.out / "projects.json.gz", table)
    print("projects", len(table), "max", max(sizes), "total", sum(sizes))


if __name__ == "__main__":
    main()
