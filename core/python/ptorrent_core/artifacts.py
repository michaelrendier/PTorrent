"""BinaryArtifactStore — the one centralized binary writer.

The artifact-before-stream invariant (the formal spec that matters): for any job
producing a stream S derived from bytes B, the core MUST

  1. write B to the store,
  2. compute h(B),
  3. commit the ACQUIRE custody tx for h(B),

BEFORE emitting the first event of S. Every downstream stream event carries
`parent_hash = h(B)`. If B is not retained (transient HTML feeding only a
σ-eval) an ACQUIRE tx is still committed with retained=false + source_url +
fetched_at, so lineage exists without the bytes.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from . import chain as _chain
from ._util import now_iso, sha256_bytes


@dataclass
class Artifact:
    file_hash: str
    file_name: str
    kind: str
    size: int
    retained: bool
    producer_orcid: str
    source_url: str = ""
    fetched_at: str = ""
    parent_hash: str = ""
    job_id: str = ""
    labels_hash: str = ""
    tlp: str = "CLEAR"

    def to_dict(self) -> dict:
        return {
            "file_hash": self.file_hash, "file_name": self.file_name, "kind": self.kind,
            "size": self.size, "retained": self.retained,
            "producer_orcid": self.producer_orcid, "source_url": self.source_url,
            "fetched_at": self.fetched_at, "parent_hash": self.parent_hash,
            "job_id": self.job_id, "labels_hash": self.labels_hash, "tlp": self.tlp,
        }


class BinaryArtifactStore:
    def __init__(self, data_root: str, db, custody: "_chain.CustodyChain"):
        self.root = data_root
        self.db = db
        self.custody = custody
        os.makedirs(self.root, exist_ok=True)

    def _path(self, job_id: str, file_hash: str, ext: str) -> str:
        d = os.path.join(self.root, job_id or "_")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, f"{file_hash[:16]}{ext}")

    def _record(self, art: Artifact) -> None:
        self.db.execute(
            "INSERT INTO artifacts(file_hash,file_name,kind,size,retained,producer_orcid,"
            "source_url,fetched_at,parent_hash,job_id,labels_hash,tlp) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(file_hash) DO UPDATE SET "
            "retained=excluded.retained, job_id=excluded.job_id, parent_hash=excluded.parent_hash",
            (art.file_hash, art.file_name, art.kind, art.size, int(art.retained),
             art.producer_orcid, art.source_url, art.fetched_at, art.parent_hash,
             art.job_id, art.labels_hash, art.tlp))

    def acquire(self, data: bytes, *, kind: str, job_id: str, producer_orcid: str,
                file_name: str = "", source_url: str = "", parent_hash: str = "",
                marking: dict | None = None, retain: bool = True, ext: str = ".bin") -> Artifact:
        """Write (optionally), hash, and commit ACQUIRE — the three steps, in order.
        Returns the Artifact. Callers MUST call this before emitting derived events."""
        h = sha256_bytes(data)
        marking = marking or {}
        art = Artifact(
            file_hash=h, file_name=file_name or f"{h[:16]}{ext}", kind=kind,
            size=len(data), retained=retain, producer_orcid=producer_orcid,
            source_url=source_url, fetched_at=now_iso(), parent_hash=parent_hash,
            job_id=job_id, labels_hash=marking.get("labels_hash", ""),
            tlp=marking.get("tlp", "CLEAR"),
        )
        if retain:
            with open(self._path(job_id, h, ext), "wb") as f:
                f.write(data)
        self._record(art)
        self.custody.add_tx(
            _chain.ACQUIRE, actor=producer_orcid, object_hash=h, parent_hash=parent_hash,
            file_name=art.file_name, file_size=art.size, marking=marking,
            note=f"kind={kind} retained={int(retain)} src={source_url}", commit=True)
        return art

    def get(self, file_hash: str) -> Artifact | None:
        r = self.db.query_one("SELECT * FROM artifacts WHERE file_hash=?", (file_hash,))
        if not r:
            return None
        return Artifact(
            file_hash=r["file_hash"], file_name=r["file_name"], kind=r["kind"],
            size=r["size"], retained=bool(r["retained"]),
            producer_orcid=r["producer_orcid"], source_url=r["source_url"],
            fetched_at=r["fetched_at"], parent_hash=r["parent_hash"], job_id=r["job_id"],
            labels_hash=r["labels_hash"] or "", tlp=r["tlp"] or "CLEAR")

    def bytes_for(self, file_hash: str) -> bytes | None:
        art = self.get(file_hash)
        if not art or not art.retained:
            return None
        p = self._path(art.job_id, file_hash, os.path.splitext(art.file_name)[1] or ".bin")
        return open(p, "rb").read() if os.path.exists(p) else None
