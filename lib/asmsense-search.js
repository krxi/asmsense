// asmsense-search: look up function names in the asmsense v4 dataset from static shards.
//
//   import { openIndex } from "https://cdn.jsdelivr.net/gh/krxi/asmsense@<commit>/lib/asmsense-search.js";
//   const idx = await openIndex("https://cdn.jsdelivr.net/gh/krxi/asmsense@<commit>/v1/");
//   const hits = await idx.search("crc32");     // [{ name, count, exact }]
//   const recs = await idx.lookup(hits[0].name); // records for that exact name
//
// Every file is gzip-compressed JSON. A search reads tokens.json.gz once, then one token shard per
// query word; a lookup reads one name shard. Shards are picked with fnv1a32(key) % shardCount,
// the same function the Python builder uses (tools/build_index.py).

const TOKEN_RE = /[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+/g;

export function fnv1a32(s) {
  let h = 0x811c9dc5;
  for (const b of new TextEncoder().encode(s)) {
    h ^= b;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h;
}

// Same rules as tokens() in build_index.py.
export function tokens(name) {
  const out = [];
  for (const part of name.split(/[^A-Za-z0-9]+/)) {
    if (!part) continue;
    const pieces = part.match(TOKEN_RE) || [];
    for (const p of pieces) out.push(p.toLowerCase());
    for (let i = 0; i + 1 < pieces.length; i++) {
      if (/^[A-Za-z]+$/.test(pieces[i]) && /^\d+$/.test(pieces[i + 1])) out.push((pieces[i] + pieces[i + 1]).toLowerCase());
    }
  }
  return [...new Set(out.filter((t) => t.length >= 2 && !/^\d+$/.test(t)))];
}

async function readJson(res) {
  const buf = new Uint8Array(await res.arrayBuffer());
  // Some CDNs pass the file through as-is, some decode it on the way; handle both.
  if (buf[0] === 0x1f && buf[1] === 0x8b) {
    const stream = new Blob([buf]).stream().pipeThrough(new DecompressionStream("gzip"));
    return JSON.parse(await new Response(stream).text());
  }
  return JSON.parse(new TextDecoder().decode(buf));
}

export async function openIndex(base, { fetch: fetchFn = fetch.bind(globalThis) } = {}) {
  if (!base.endsWith("/")) base += "/";
  const cache = new Map();
  const get = (path) => {
    if (!cache.has(path)) {
      cache.set(path, fetchFn(base + path).then((r) => {
        if (!r.ok) throw new Error(`${r.status} for ${path}`);
        return path.endsWith(".gz") ? readJson(r) : r.json();
      }).catch((e) => { cache.delete(path); throw e; }));
    }
    return cache.get(path);
  };

  const meta = await get("meta.json");
  const pad = (n, w) => String(n).padStart(w, "0");
  const tokenShard = (t) => get(`t/${pad(fnv1a32(t) % meta.token_shards, 2)}.json.gz`).then((s) => s[t] || []);
  const nameShard = (name) => get(`n/${pad(fnv1a32(name.toLowerCase()) % meta.name_shards, 3)}.json.gz`);

  // Prefix completion over the token vocabulary, most common first.
  async function complete(prefix, limit = 8) {
    prefix = prefix.toLowerCase();
    if (prefix.length < 2) return [];
    const vocab = await get("tokens.json.gz");
    let lo = 0, hi = vocab.length;
    while (lo < hi) { const m = (lo + hi) >> 1; if (vocab[m][0] < prefix) lo = m + 1; else hi = m; }
    const out = [];
    for (let i = lo; i < vocab.length && vocab[i][0].startsWith(prefix); i++) out.push(vocab[i]);
    return out.sort((a, b) => b[1] - a[1]).slice(0, limit);
  }

  // Names that contain every query token. The last word may be a prefix ("sqlite3_ope").
  async function search(query, { limit = 60 } = {}) {
    query = query.trim();
    if (!query) return [];
    const words = tokens(query);
    const exactKey = query.replace(/\s+/g, "_");
    const exact = (await nameShard(exactKey))[exactKey] ? exactKey : null;

    let sets = [];
    for (const [i, w] of words.entries()) {
      let names = await tokenShard(w);
      if (!names.length && i === words.length - 1) {
        // treat an unknown last word as a prefix of a known token
        const cands = await complete(w, 3);
        const lists = await Promise.all(cands.map(([t]) => tokenShard(t)));
        names = lists.flat();
      }
      sets.push(new Map(names.map(([n, c]) => [n, c])));
    }
    let hits = sets.length ? [...sets[0]] : [];
    for (const s of sets.slice(1)) hits = hits.filter(([n]) => s.has(n));

    const q = query.toLowerCase();
    const scored = hits.map(([name, count]) => {
      const l = name.toLowerCase();
      const rank = l === q ? 0 : l.includes(q.replace(/\s+/g, "_")) ? 1 : 2;
      return { name, count, exact: name === exact, rank };
    });
    if (exact && !scored.some((h) => h.name === exact)) {
      scored.push({ name: exact, count: (await lookup(exact)).length, exact: true, rank: 0 });
    }
    scored.sort((a, b) => a.rank - b.rank || a.name.length - b.name.length || b.count - a.count || a.name.localeCompare(b.name));
    return scored.slice(0, limit).map(({ name, count, exact }) => ({ name, count, exact }));
  }

  // All records for one exact function name, with the license name resolved.
  async function lookup(name) {
    const recs = (await nameShard(name))[name] || [];
    return recs.map((r) => ({ name, ...r, license: meta.licenses[r.license] }));
  }

  return { meta, search, lookup, complete };
}
