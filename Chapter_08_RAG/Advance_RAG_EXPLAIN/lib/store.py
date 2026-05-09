"""Qdrant client wrapper: bootstrap, upsert, hybrid query.

Supports two modes:
  * Server: set QDRANT_URL=http://host:port
  * Embedded (default): set QDRANT_PATH=/abs/path/to/dir  (or omit both - uses ./qdrant_data)

Embedded mode runs Qdrant as an in-process file store - no Docker required.
"""
from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

DENSE_DIM = 1024

_CLIENT = None
_CLIENT_LOCK = threading.Lock()


def get_client() -> QdrantClient:
    """Return a process-wide Qdrant client (singleton).

    Embedded mode requires a singleton because the local file store is locked
    per process. We cache it here so every Flask request reuses the same client.
    """
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    with _CLIENT_LOCK:
        if _CLIENT is not None:
            return _CLIENT
        url = os.environ.get("QDRANT_URL", "").strip()
        if url:
            _CLIENT = QdrantClient(url=url, timeout=60.0)
        else:
            path = os.environ.get("QDRANT_PATH", "").strip() or str(
                Path(__file__).resolve().parent.parent / "qdrant_data"
            )
            Path(path).mkdir(parents=True, exist_ok=True)
            _CLIENT = QdrantClient(path=path)
    return _CLIENT


def collection_exists(client: QdrantClient, name: str) -> bool:
    try:
        return client.collection_exists(name)
    except Exception:
        cols = client.get_collections().collections
        return any(c.name == name for c in cols)


def bootstrap(client: QdrantClient, name: str, recreate: bool = False) -> None:
    """Create collection with named dense + sparse vectors. Idempotent."""
    if collection_exists(client, name):
        if not recreate:
            return
        client.delete_collection(name)
    client.create_collection(
        collection_name=name,
        vectors_config={
            "dense": qm.VectorParams(size=DENSE_DIM, distance=qm.Distance.COSINE),
        },
        sparse_vectors_config={
            "sparse": qm.SparseVectorParams(),
        },
    )


def _stable_uuid(chunk_id: str) -> str:
    """Map our chunk id ('rN-cM') to a stable Qdrant point id (UUID)."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"advrag/{chunk_id}"))


def upsert_chunks(
    client: QdrantClient,
    name: str,
    chunks: list[dict],
    dense,            # np.ndarray [N, 1024]
    sparse: list[dict],
    batch_size: int = 64,
) -> int:
    """Upsert chunks into Qdrant in batches. Returns number written."""
    n = len(chunks)
    written = 0
    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        points = []
        for i in range(start, end):
            ch = chunks[i]
            pid = _stable_uuid(ch["id"])
            payload = {
                **{k: v for k, v in ch["metadata"].items() if v is not None},
                "chunk_id": ch["id"],
                "text": ch["text"],
            }
            sp = sparse[i]
            points.append(qm.PointStruct(
                id=pid,
                vector={
                    "dense": dense[i].tolist(),
                    "sparse": qm.SparseVector(indices=sp["indices"], values=sp["values"]),
                },
                payload=payload,
            ))
        client.upsert(collection_name=name, points=points)
        written += len(points)
    return written


def count(client: QdrantClient, name: str) -> int:
    if not collection_exists(client, name):
        return 0
    return int(client.count(collection_name=name, exact=True).count)


def collection_info(client: QdrantClient, name: str) -> dict:
    if not collection_exists(client, name):
        return {"exists": False, "points": 0}
    info = client.get_collection(name)
    points = getattr(info, "points_count", None)
    vectors = getattr(info, "vectors_count", None)
    if points is None:
        try:
            points = int(client.count(collection_name=name, exact=True).count)
        except Exception:
            points = 0
    return {
        "exists": True,
        "points": int(points or 0),
        "vectors": int(vectors) if vectors is not None else None,
        "status": str(getattr(info, "status", "")),
    }


def dense_search(
    client: QdrantClient,
    name: str,
    query_dense,
    limit: int = 20,
    flt: dict | None = None,
):
    return client.query_points(
        collection_name=name,
        query=query_dense.tolist() if hasattr(query_dense, "tolist") else list(query_dense),
        using="dense",
        limit=limit,
        with_payload=True,
        query_filter=_build_filter(flt),
    ).points


def sparse_search(
    client: QdrantClient,
    name: str,
    query_sparse: dict,
    limit: int = 20,
    flt: dict | None = None,
):
    return client.query_points(
        collection_name=name,
        query=qm.SparseVector(
            indices=query_sparse["indices"],
            values=query_sparse["values"],
        ),
        using="sparse",
        limit=limit,
        with_payload=True,
        query_filter=_build_filter(flt),
    ).points


def _build_filter(flt: dict | None):
    if not flt:
        return None
    must = []
    for k, v in flt.items():
        if v is None or v == "":
            continue
        must.append(qm.FieldCondition(key=k, match=qm.MatchValue(value=v)))
    if not must:
        return None
    return qm.Filter(must=must)


def iter_points(
    client: QdrantClient,
    name: str,
    limit: int = 50,
    offset: str | None = None,
    flt: dict | None = None,
):
    """Scroll through stored points; returns (points, next_offset)."""
    points, next_off = client.scroll(
        collection_name=name,
        scroll_filter=_build_filter(flt),
        limit=limit,
        offset=offset,
        with_payload=True,
        with_vectors=False,
    )
    return points, next_off


def get_by_chunk_ids(client: QdrantClient, name: str, chunk_ids: list[str]):
    if not chunk_ids:
        return []
    flt = qm.Filter(must=[qm.FieldCondition(
        key="chunk_id",
        match=qm.MatchAny(any=chunk_ids),
    )])
    points, _ = client.scroll(
        collection_name=name,
        scroll_filter=flt,
        limit=len(chunk_ids),
        with_payload=True,
        with_vectors=False,
    )
    return points
