# asmsense name index

This branch holds a static index of the [asmsense v4 dataset](https://huggingface.co/datasets/krxi123/asmsense)
(228,177 x86-64 functions from 341 C projects) so that a browser can look up a function name without
downloading the whole dataset. It is not merged into `main`; it only carries generated files and the
script that builds them.

The browse and search page at <https://asmsense.luxurycashew.com/search/> reads these files through jsDelivr.

## What a lookup returns

For every function in the dataset with a given name: project, source file, source revision, compiler
optimization level, dataset split, instruction count, whether the symbol is exported, its license, the
first 24 lines of its disassembly (Intel syntax, internal calls renamed to `sub_XXXX`), and the start of
its call context. For the 2,000 functions in the fixed test sample, it also includes the name and
English description predicted by the [v6 adapter](https://huggingface.co/krxi123/asmsense-lora-v6).

Only functions defined inside a project are in the dataset. A libc name such as `memcpy` appears only
where a project ships its own copy; calls into the system C library have no body here. A search for
`memcpy` also lists functions whose own name contains it, such as `XXH_memcpy`.

## Layout

```
v1/meta.json         counts, shard counts, license names, SHA-256 of the inputs
v1/tokens.json.gz    every name token and how many names contain it
v1/t/NN.json.gz      token -> [[name, record count], ...]        64 files
v1/n/NNN.json.gz     exact name -> records                       512 files
v1/projects.json.gz  every project: [name, license, files, functions, records]
v1/p/<project>.json.gz   one project's files, functions and resolved calls   341 files
lib/asmsense-search.js   browser module that reads the files above
tools/build_index.py     builds the name and token shards
tools/build_tree.py      builds projects.json.gz and p/
```

## Browse tree and calls

`p/<project>.json.gz` lists the project's files and, for each (file, function name), one entry:
`[name, file index, levels present, instructions, level shown, callees in the dataset, callees not in
the dataset, library calls]`. Calls are read from one build per function, `-O0` when it exists.
Each project's object files are linked into one dylib per level, so `sub_XXXX` ids are unique per
project and level, and a call can go to a function in another file. A call is resolved to a name when a
record with that `sub_XXXX` exists for the same project and level: 69% of all 406,194 internal calls,
80% in the builds the tree uses. For the rest, the call context still gives their size and the library
functions they call. `ext_XXXX` names are symbols from project files that did not compile. The largest
project file is 87 KB; all 341 together are 1.4 MB.

A name is split into lowercase tokens on `_`, camelCase boundaries and digits (`ComputeCRC32` →
`compute`, `crc`, `crc32`). The shard for a key is `fnv1a32(key) % count`; the token shards use the
token, the name shards use the lowercased name. All files are gzip-compressed JSON. A typical search
reads 70–160 KB; a prefix search on a common word reads up to about 360 KB.

## Use from JavaScript

```js
const base = "https://cdn.jsdelivr.net/gh/krxi/asmsense@<commit>/";
const { openIndex } = await import(base + "lib/asmsense-search.js");
const idx = await openIndex(base + "v1/");
const hits = await idx.search("crc32");   // [{ name, count, exact }]
const recs = await idx.lookup("crc32");   // records for the exact name
const tree = await idx.project("sqlite"); // files, functions, calls
```

Pin a commit rather than the branch name: jsDelivr caches commit URLs permanently.

## Rebuild

```
python3 tools/build_index.py --v4 <dir with data/v4/*.jsonl.gz> --v6 test_sabit-sonuc.jsonl --out v1
python3 tools/build_tree.py  --v4 <dir with data/v4/*.jsonl.gz> --out v1
```

The output is deterministic for the same inputs. `meta.json` records the SHA-256 of each input file.

## Licenses

The disassembly comes from compiling third-party open-source projects; each record carries the license
of its project. License texts and sources: [`licenses/` on Hugging Face](https://huggingface.co/datasets/krxi123/asmsense/tree/main/licenses)
and [`veri/LISANSLAR.md`](https://github.com/krxi/asmsense/blob/main/veri/LISANSLAR.md). The scripts on
this branch are MIT, like the rest of the repository.
