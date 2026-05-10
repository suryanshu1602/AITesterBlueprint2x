"""CLI ingest fallback: same logic as the /ingest endpoint, runnable from the shell.

Usage:
  python ingest.py path/to/file.csv \\
      --text-cols summary,steps,expected_result,labels \\
      --meta-cols id,jira_id,priority,module \\
      [--chunk-size 1000] [--chunk-overlap 150] [--recreate]

Defaults pick the columns the Flask UI defaults to.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

from lib import chunking, embeddings, store

load_dotenv()

DEFAULT_TEXT = "summary,steps,expected_result,labels,preconditions"
DEFAULT_META = "id,jira_id,priority,severity,module,owner,test_type,sprint,status"


def _read(path: Path):
    import pandas as pd
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("file")
    p.add_argument("--text-cols", default=DEFAULT_TEXT)
    p.add_argument("--meta-cols", default=DEFAULT_META)
    p.add_argument("--chunk-size", type=int, default=1000)
    p.add_argument("--chunk-overlap", type=int, default=150)
    p.add_argument("--collection", default=os.environ.get("COLLECTION_NAME", "vwo_test_cases"))
    p.add_argument("--recreate", action="store_true")
    p.add_argument("--batch", type=int, default=int(os.environ.get("INGEST_BATCH", "16")))
    args = p.parse_args()

    fpath = Path(args.file)
    if not fpath.exists():
        print(f"File not found: {fpath}", file=sys.stderr)
        return 2

    text_cols = [c.strip() for c in args.text_cols.split(",") if c.strip()]
    meta_cols = [c.strip() for c in args.meta_cols.split(",") if c.strip()]

    print(f"Reading {fpath} ...")
    df = _read(fpath)
    have = set(df.columns)
    text_cols = [c for c in text_cols if c in have] or list(have)
    meta_cols = [c for c in meta_cols if c in have]
    print(f"  rows={len(df)}  columns={list(df.columns)}")
    print(f"  text_cols={text_cols}")
    print(f"  meta_cols={meta_cols}")

    rows = df.to_dict(orient="records")
    print(f"Chunking (size={args.chunk_size}, overlap={args.chunk_overlap}) ...")
    chunks = chunking.chunk_dataframe(
        rows, text_cols=text_cols, meta_cols=meta_cols,
        size=args.chunk_size, overlap=args.chunk_overlap, source_file=fpath.name,
    )
    print(f"  produced {len(chunks)} chunks from {len(rows)} rows")
    if not chunks:
        print("  (nothing to ingest)", file=sys.stderr)
        return 1

    print(f"Loading bge-m3 and embedding ...")
    bs = args.batch
    all_dense = []
    all_sparse: list[dict] = []
    texts = [c["text"] for c in chunks]
    for i in range(0, len(texts), bs):
        sub = texts[i:i + bs]
        res = embeddings.embed_batch(sub, batch_size=len(sub))
        all_dense.append(res["dense"])
        all_sparse.extend(res["sparse"])
        done = min(i + bs, len(texts))
        print(f"  embedded {done}/{len(texts)}")
    dense = np.vstack(all_dense)

    print(f"Indexing into Qdrant collection '{args.collection}' ...")
    client = store.get_client()
    store.bootstrap(client, args.collection, recreate=args.recreate)
    written = store.upsert_chunks(client, args.collection, chunks, dense, all_sparse, batch_size=64)
    info = store.collection_info(client, args.collection)
    print(f"  wrote {written} points  (collection now has {info['points']})")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
