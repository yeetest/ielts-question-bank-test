#!/usr/bin/env python3
"""
Query ConceptNet API for keyword → semantic relations.
Batch processing with local cache to avoid re-querying.

Usage:
  python3 pipeline/query_conceptnet.py --batch 1          # keywords 1-50
  python3 pipeline/query_conceptnet.py --batch 2          # keywords 51-100
  python3 pipeline/query_conceptnet.py --batch all        # all keywords
  python3 pipeline/query_conceptnet.py --batch 1 --dry-run  # preview only
"""
import json, time, urllib.request, urllib.parse, re, argparse, os

BATCH_SIZE = 50
KEYWORDS_FILE = "keywords_nouns_verbs_filtered.txt"
CACHE_DIR = "human-in-the-loop/conceptnet_cache"
OUTPUT_FILE = "human-in-the-loop/conceptnet_raw.json"

# Relations we care about, in priority order
USEFUL_RELATIONS = [
    "IsA",          # best for L1 categorisation
    "AtLocation",   # place signals
    "RelatedTo",    # broad thematic L2
    "UsedFor",      # functional, helps L2/L3
    "HasProperty",  # qualities, helps L3
    "PartOf",       # part-whole, helps hierarchy
    "HasA",         # possession/composition
    "CapableOf",    # what it can do (verbs especially)
]

API_BASE = "http://api.conceptnet.io"


def parse_keywords(filepath):
    """Parse keywords_nouns_verbs_filtered.txt → list of (word, pos, score)."""
    keywords = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # format: word(POS,score)
            m = re.match(r"^(.+?)\((\w+),([\d.]+)\)$", line)
            if m:
                keywords.append((m.group(1), m.group(2), float(m.group(3))))
    return keywords


def get_cache_path(word):
    return os.path.join(CACHE_DIR, f"{word}.json")


def query_conceptnet(word):
    """Query ConceptNet for a word, return filtered edges."""
    cache_path = get_cache_path(word)
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)

    url = f"{API_BASE}/c/en/{urllib.parse.quote(word)}?limit=100"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  ERROR querying '{word}': {e}")
        return {"word": word, "edges": [], "error": str(e)}

    # Filter to useful English-only edges
    edges = []
    for edge in data.get("edges", []):
        rel = edge.get("rel", {}).get("label", "")
        if rel not in USEFUL_RELATIONS:
            continue

        start = edge.get("start", {})
        end = edge.get("end", {})

        # Only keep English edges
        if start.get("language", "en") != "en" or end.get("language", "en") != "en":
            continue

        start_label = start.get("label", "")
        end_label = end.get("label", "")
        weight = edge.get("weight", 0)

        edges.append({
            "rel": rel,
            "start": start_label,
            "end": end_label,
            "weight": round(weight, 3),
        })

    # Sort by weight descending
    edges.sort(key=lambda x: x["weight"], reverse=True)

    result = {"word": word, "edges": edges}

    # Cache locally
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result


def summarize_edges(result):
    """Group edges by relation type for readable output."""
    word = result["word"]
    by_rel = {}
    for e in result["edges"]:
        rel = e["rel"]
        # Get the "other" concept (not our keyword)
        other = e["end"] if e["start"].lower() == word.lower() else e["start"]
        by_rel.setdefault(rel, []).append((other, e["weight"]))

    return by_rel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", required=True, help="Batch number (1,2,...) or 'all'")
    parser.add_argument("--dry-run", action="store_true", help="Preview which keywords will be queried")
    args = parser.parse_args()

    os.makedirs(CACHE_DIR, exist_ok=True)

    keywords = parse_keywords(KEYWORDS_FILE)
    print(f"Total keywords: {len(keywords)}")

    if args.batch == "all":
        batch_keywords = keywords
    else:
        batch_num = int(args.batch)
        start = (batch_num - 1) * BATCH_SIZE
        end = start + BATCH_SIZE
        batch_keywords = keywords[start:end]
        print(f"Batch {batch_num}: keywords {start+1}-{min(end, len(keywords))}")

    if not batch_keywords:
        print("No keywords in this batch range.")
        return

    if args.dry_run:
        print("\nDry run — keywords to query:")
        for i, (word, pos, score) in enumerate(batch_keywords, 1):
            cached = "CACHED" if os.path.exists(get_cache_path(word)) else "TO QUERY"
            print(f"  {i}. {word} ({pos}) [{cached}]")
        to_query = sum(1 for w, _, _ in batch_keywords if not os.path.exists(get_cache_path(w)))
        print(f"\n{to_query} to query, ~{to_query} seconds estimated")
        return

    # Query and collect
    all_results = []
    for i, (word, pos, score) in enumerate(batch_keywords, 1):
        cached = os.path.exists(get_cache_path(word))
        status = "cached" if cached else "querying"
        print(f"  [{i}/{len(batch_keywords)}] {word} ({pos}) — {status}")

        result = query_conceptnet(word)
        result["pos"] = pos
        result["score"] = score
        all_results.append(result)

        # Rate limit: ~1 req/sec for uncached
        if not cached:
            time.sleep(1.0)

    # Merge with existing output
    existing = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            for item in json.load(f):
                existing[item["word"]] = item

    for r in all_results:
        existing[r["word"]] = r

    # Write merged output
    merged = sorted(existing.values(), key=lambda x: x["word"])
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Results saved to {OUTPUT_FILE} ({len(merged)} total keywords)")
    print(f"{'='*60}\n")

    for r in all_results:
        by_rel = summarize_edges(r)
        print(f"\n--- {r['word']} ({r.get('pos','')}) ---")
        if not by_rel:
            print("  (no useful edges found)")
        for rel, items in by_rel.items():
            top = items[:5]  # show top 5 per relation
            concepts = ", ".join(f"{c}({w})" for c, w in top)
            print(f"  {rel}: {concepts}")


if __name__ == "__main__":
    main()
