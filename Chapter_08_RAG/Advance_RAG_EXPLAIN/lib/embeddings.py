"""bge-m3 wrapper producing dense + sparse vectors from one model."""
from __future__ import annotations

import os
import threading
from typing import Iterable

import numpy as np

_MODEL = None
_LOCK = threading.Lock()


def get_embedder():
    """Lazy-load BGEM3FlagModel singleton."""
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    with _LOCK:
        if _MODEL is not None:
            return _MODEL
        from FlagEmbedding import BGEM3FlagModel
        use_fp16 = os.environ.get("BGE_USE_FP16", "1") != "0"
        _MODEL = BGEM3FlagModel("BAAI/bge-m3", use_fp16=use_fp16)
    return _MODEL


def _format_sparse(raw_sparse) -> list[dict]:
    """Normalise FlagEmbedding sparse output to [{indices, values}, ...]."""
    out: list[dict] = []
    for item in raw_sparse:
        if isinstance(item, dict):
            indices = list(item.keys())
            values = list(item.values())
        else:
            indices = list(getattr(item, "indices", []))
            values = list(getattr(item, "values", []))
        indices = [int(i) for i in indices]
        values = [float(v) for v in values]
        out.append({"indices": indices, "values": values})
    return out


def embed_batch(texts: list[str], batch_size: int = 16) -> dict:
    """Return {'dense': np.ndarray[N,1024], 'sparse': list[dict]} for texts."""
    model = get_embedder()
    out_dense: list[np.ndarray] = []
    out_sparse: list[dict] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = model.encode(
            batch,
            batch_size=len(batch),
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )
        dense = np.asarray(result["dense_vecs"], dtype=np.float32)
        out_dense.append(dense)
        out_sparse.extend(_format_sparse(result["lexical_weights"]))
    if not out_dense:
        return {"dense": np.zeros((0, 1024), dtype=np.float32), "sparse": []}
    return {"dense": np.vstack(out_dense), "sparse": out_sparse}


def embed_query(text: str) -> dict:
    """Return {'dense': np.ndarray[1024], 'sparse': {indices, values}}."""
    res = embed_batch([text], batch_size=1)
    return {"dense": res["dense"][0], "sparse": res["sparse"][0]}


def sparse_top_terms(sparse_vec: dict, k: int = 5) -> list[tuple[int, float]]:
    """Return top-k (token_id, weight) pairs sorted by weight descending."""
    pairs = list(zip(sparse_vec.get("indices", []), sparse_vec.get("values", [])))
    pairs.sort(key=lambda p: p[1], reverse=True)
    return pairs[:k]


def decode_sparse_terms(sparse_vec: dict, k: int = 5) -> list[tuple[str, float]]:
    """Decode top sparse term ids back to tokens via the model tokenizer."""
    model = get_embedder()
    tok = getattr(model, "tokenizer", None)
    pairs = sparse_top_terms(sparse_vec, k)
    out: list[tuple[str, float]] = []
    for idx, weight in pairs:
        try:
            term = tok.decode([idx]) if tok is not None else str(idx)
        except Exception:
            term = str(idx)
        out.append((term.strip() or str(idx), float(weight)))
    return out
