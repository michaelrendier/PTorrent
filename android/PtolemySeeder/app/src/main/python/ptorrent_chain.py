#!/usr/bin/env python3
"""
ptorrent_chain.py — PTorrent Blockchain Engine v1.0

Append-only distributed ledger for:
  - .ptorrent descriptor publication and version tracking
  - .bin checkpoint file announcement and seeder registry
  - Merge events  (bin A + bin B → bin C, β-weighted A-matrix union)
  - Retirement    (old hash superseded by new hash)

Designed to run on CPython 3.12 (desktop) and Chaquopy 15.0.1 (Android/ARM64).
No external dependencies — stdlib only: hashlib, json, os, time, dataclasses.

Author:  Cody Michael Allison <the.wandering.god@gmail.com>
Built:   Claude Code (claude-sonnet-4-6)
License: GNU GPL v3
Spec:    spec/ptorrent-chain-v1.md
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Transaction types
# ---------------------------------------------------------------------------

GENESIS     = "GENESIS"     # chain genesis marker
ANNOUNCE    = "ANNOUNCE"    # publish: this file exists at this hash and size
UPDATE      = "UPDATE"      # new version of a named resource (links prev_hash)
SEED        = "SEED"        # peer is actively seeding this hash
UNSEED      = "UNSEED"      # peer has stopped seeding this hash
RETIRE      = "RETIRE"      # this hash is superseded (always paired with UPDATE)
MERGE       = "MERGE"       # merge_a + merge_b → file_hash (β-weighted bin merge)
EVALUATE    = "EVALUATE"    # dataset evaluated under terms → .peval result
CLASSIFY    = "CLASSIFY"    # assign security classification to a file hash
ACKNOWLEDGE = "ACKNOWLEDGE" # researcher explicitly accepted the security notice
DISCLOSE    = "DISCLOSE"    # embargo lifted; classification drops to public
REVOKE      = "REVOKE"      # access withdrawn for a specific peer_id
FLAG        = "FLAG"        # file flagged as malicious / unsafe — blocks execution


# ---------------------------------------------------------------------------
# Merkle tree
# ---------------------------------------------------------------------------

def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def merkle_root(hashes: list[str]) -> str:
    """
    Compute the Merkle root of a list of SHA-256 hex strings.
    Empty list returns SHA-256 of empty string.
    Odd-length layers duplicate the last node before pairing.
    """
    if not hashes:
        return _sha256("")
    layer = list(hashes)
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [_sha256(layer[i] + layer[i + 1]) for i in range(0, len(layer), 2)]
    return layer[0]


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

@dataclass
class Transaction:
    """
    A single event in the PTorrent ledger.

    All fields are strings or ints so the dataclass serialises cleanly to JSON.
    tx_hash is computed from all other fields — acts as the transaction ID and
    integrity check. It is recomputed on deserialisation and verified against
    the stored value.
    """
    type:       str
    timestamp:  float
    file_hash:  str = ""   # SHA-256 of the file content (hex)
    file_name:  str = ""   # e.g. monad_physics.bin, physics.ptorrent
    file_size:  int = 0    # bytes; 0 if unknown
    peer_id:    str = ""   # device identifier or addr:port
    prev_hash:  str = ""   # UPDATE/RETIRE: hash this replaces
    merge_a:    str = ""   # MERGE: first source hash
    merge_b:    str = ""   # MERGE: second source hash
    note:       str = ""   # human-readable annotation
    tx_hash:    str = field(default="", init=False)

    def __post_init__(self) -> None:
        self.tx_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = json.dumps({
            "type":      self.type,
            "timestamp": self.timestamp,
            "file_hash": self.file_hash,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "peer_id":   self.peer_id,
            "prev_hash": self.prev_hash,
            "merge_a":   self.merge_a,
            "merge_b":   self.merge_b,
            "note":      self.note,
        }, sort_keys=True, ensure_ascii=False)
        return _sha256(payload)

    def is_valid(self) -> bool:
        return self.tx_hash == self._compute_hash()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Transaction:
        tx = cls(
            type=d["type"],
            timestamp=d["timestamp"],
            file_hash=d.get("file_hash", ""),
            file_name=d.get("file_name", ""),
            file_size=d.get("file_size", 0),
            peer_id=d.get("peer_id", ""),
            prev_hash=d.get("prev_hash", ""),
            merge_a=d.get("merge_a", ""),
            merge_b=d.get("merge_b", ""),
            note=d.get("note", ""),
        )
        stored = d.get("tx_hash", "")
        if stored and stored != tx.tx_hash:
            raise ValueError(
                f"Transaction integrity failure: stored={stored[:12]} "
                f"computed={tx.tx_hash[:12]}"
            )
        return tx


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------

@dataclass
class Block:
    """
    One block in the PTorrent chain.

    Lightweight PoW: find nonce such that SHA-256(header_string + nonce)
    begins with `difficulty` zero nibbles (hex chars). difficulty=2 requires
    ~256 hashes on average — fast on ARM64, still provides Sybil resistance.

    Blocks are mined on construction. Use Block.from_dict() to restore a
    persisted block without re-mining (integrity is verified instead).
    """
    index:         int
    timestamp:     float
    previous_hash: str
    transactions:  list[Transaction]
    difficulty:    int = 2

    # Computed — not constructor args
    nonce:       int = field(default=0,  init=False)
    merkle:      str = field(default="", init=False)
    hash:        str = field(default="", init=False)

    def __post_init__(self) -> None:
        self.merkle = merkle_root([tx.tx_hash for tx in self.transactions])
        self._mine()

    # --- header --------------------------------------------------------

    def _header(self, nonce: int) -> str:
        return json.dumps({
            "index":         self.index,
            "timestamp":     self.timestamp,
            "previous_hash": self.previous_hash,
            "merkle":        self.merkle,
            "difficulty":    self.difficulty,
            "nonce":         nonce,
        }, sort_keys=True)

    # --- PoW -----------------------------------------------------------

    def _mine(self) -> None:
        target = "0" * self.difficulty
        n = 0
        while True:
            h = _sha256(self._header(n))
            if h.startswith(target):
                self.nonce = n
                self.hash  = h
                return
            n += 1

    # --- validation ----------------------------------------------------

    def is_valid(self) -> bool:
        # All transactions internally consistent
        if not all(tx.is_valid() for tx in self.transactions):
            return False
        # Merkle root matches transaction set
        expected_merkle = merkle_root([tx.tx_hash for tx in self.transactions])
        if expected_merkle != self.merkle:
            return False
        # PoW satisfied
        recomputed = _sha256(self._header(self.nonce))
        return recomputed == self.hash and self.hash.startswith("0" * self.difficulty)

    # --- serialisation -------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "index":         self.index,
            "timestamp":     self.timestamp,
            "previous_hash": self.previous_hash,
            "merkle":        self.merkle,
            "difficulty":    self.difficulty,
            "nonce":         self.nonce,
            "hash":          self.hash,
            "transactions":  [tx.to_dict() for tx in self.transactions],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Block:
        """Restore a block from JSON without re-mining. Verifies integrity."""
        transactions = [Transaction.from_dict(t) for t in d.get("transactions", [])]
        b = object.__new__(cls)
        b.index         = d["index"]
        b.timestamp     = d["timestamp"]
        b.previous_hash = d["previous_hash"]
        b.transactions  = transactions
        b.difficulty    = d.get("difficulty", 2)
        b.nonce         = d["nonce"]
        b.merkle        = d["merkle"]
        b.hash          = d["hash"]
        if not b.is_valid():
            raise ValueError(
                f"Block {b.index} integrity failure (hash={b.hash[:12]})"
            )
        return b


# ---------------------------------------------------------------------------
# PTorrentChain
# ---------------------------------------------------------------------------

class PTorrentChain:
    """
    The PTorrent distributed ledger.

    Transactions are accumulated in a pending pool; call commit() to mine them
    into a new block. On Android, commit() after every significant event.
    On desktop, batch many transactions then commit.

    Chain is persisted to a human-readable JSON file (atomic write via tmp).

    Quick start:
        chain = PTorrentChain()

        # Register a file
        h = PTorrentChain.hash_file("monad_physics.bin")
        chain.announce("monad_physics.bin", h, file_size=10_485_760, peer_id="mydevice")

        # Mark as being seeded
        chain.seed(h, peer_id="192.168.1.5:6881")

        # New version of a .ptorrent
        new_h = PTorrentChain.hash_ptorrent("physics.ptorrent")
        chain.update("physics.ptorrent", old_hash=old_h, new_hash=new_h, peer_id="mydevice")

        # Mine pending transactions into a block
        chain.commit()

        # Query
        print(chain.get_seeders(h))
        print(chain.summary())
    """

    GENESIS_HASH = "0" * 64

    def __init__(
        self,
        store_path: str = "ptorrent_chain.json",
        difficulty: int = 2,
    ) -> None:
        self.store_path = store_path
        self.difficulty = difficulty
        self._pending: list[Transaction] = []
        self._chain:   list[Block]       = []
        self._load()
        if not self._chain:
            self._genesis()

    # -----------------------------------------------------------------------
    # Transaction API
    # -----------------------------------------------------------------------

    def announce(
        self,
        file_name: str,
        file_hash: str,
        file_size: int = 0,
        peer_id:   str = "",
        note:      str = "",
    ) -> Transaction:
        """Register that a file exists at file_hash."""
        return self._stage(Transaction(
            type=ANNOUNCE, timestamp=time.time(),
            file_name=file_name, file_hash=file_hash,
            file_size=file_size, peer_id=peer_id, note=note,
        ))

    def update(
        self,
        file_name: str,
        old_hash:  str,
        new_hash:  str,
        file_size: int = 0,
        peer_id:   str = "",
        note:      str = "",
    ) -> Transaction:
        """
        Record a new version of file_name, linking old_hash → new_hash.
        Automatically stages a RETIRE transaction for old_hash followed by
        an UPDATE transaction for new_hash.
        """
        self._stage(Transaction(
            type=RETIRE, timestamp=time.time(),
            file_name=file_name, file_hash=old_hash, prev_hash=old_hash,
            peer_id=peer_id, note=f"superseded by {new_hash[:16]}",
        ))
        return self._stage(Transaction(
            type=UPDATE, timestamp=time.time(),
            file_name=file_name, file_hash=new_hash, file_size=file_size,
            prev_hash=old_hash, peer_id=peer_id, note=note,
        ))

    def seed(
        self,
        file_hash: str,
        peer_id:   str,
        file_name: str = "",
        note:      str = "",
    ) -> Transaction:
        """Announce that peer_id is actively seeding file_hash."""
        return self._stage(Transaction(
            type=SEED, timestamp=time.time(),
            file_hash=file_hash, file_name=file_name,
            peer_id=peer_id, note=note,
        ))

    def unseed(self, file_hash: str, peer_id: str) -> Transaction:
        """Announce that peer_id has stopped seeding file_hash."""
        return self._stage(Transaction(
            type=UNSEED, timestamp=time.time(),
            file_hash=file_hash, peer_id=peer_id,
        ))

    def merge(
        self,
        hash_a:      str,
        hash_b:      str,
        result_hash: str,
        file_name:   str = "",
        file_size:   int = 0,
        peer_id:     str = "",
        note:        str = "",
    ) -> Transaction:
        """
        Record that hash_a and hash_b were β-weighted merged into result_hash.
        The merge operation is defined by the Ainulindale β-merge in monad.py:
        A_result = (β_a * A_a + β_b * A_b) / (β_a + β_b)  (A-matrix union).
        """
        return self._stage(Transaction(
            type=MERGE, timestamp=time.time(),
            file_hash=result_hash, file_name=file_name, file_size=file_size,
            merge_a=hash_a, merge_b=hash_b, peer_id=peer_id, note=note,
        ))

    # -----------------------------------------------------------------------
    # Security / evaluation transactions (v1.1)
    # -----------------------------------------------------------------------

    def evaluate(self, result_file: str, result_hash: str, result_size: int,
                 dataset_hash: str, terms_hash: str, peer_id: str,
                 note: str = "") -> "Transaction":
        """
        Record a Data Transversal evaluation result.

        :param result_file:  Output .peval filename.
        :param result_hash:  SHA-256 of the .peval file.
        :param result_size:  Byte size of .peval.
        :param dataset_hash: SHA-256 of the source dataset (from its ANNOUNCE tx).
        :param terms_hash:   SHA-256 of the monad .bin used as evaluation terms.
        :param peer_id:      ORCID:xxxx-xxxx-xxxx-xxxx@device_hash or plain peer.
        :param note:         Human-readable annotation.

        Parallel semantics: same dataset_hash + same terms_hash → β-mergeable.
        Different terms_hash → non-mergeable, both valid, tracked in parallel.
        """
        return self._stage(Transaction(
            type=EVALUATE, timestamp=time.time(),
            file_hash=result_hash, file_name=result_file, file_size=result_size,
            merge_a=dataset_hash, merge_b=terms_hash,
            peer_id=peer_id, note=note,
        ))

    def classify(self, file_hash: str, classification: str, level: int,
                 embargo_until: str, contact_orcid: str,
                 peer_id: str, disclosure_ref: str = "") -> "Transaction":
        """
        Assign a security classification to a file hash.

        :param file_hash:      Hash of the file being classified.
        :param classification: "public" | "sensitive" | "restricted" | "dual-use".
        :param level:          0-3 numeric level.
        :param embargo_until:  ISO date string "YYYY-MM-DD" or "" for no embargo.
        :param contact_orcid:  ORCID of the responsible researcher.
        :param peer_id:        Classifying peer.
        :param disclosure_ref: External reference (NIST, CVE, etc.).
        """
        note = (f"level={level} class={classification} "
                f"embargo={embargo_until or 'none'} "
                f"contact={contact_orcid} ref={disclosure_ref}")
        return self._stage(Transaction(
            type=CLASSIFY, timestamp=time.time(),
            file_hash=file_hash, file_name="",
            peer_id=peer_id, note=note,
        ))

    def acknowledge(self, file_hash: str, orcid_id: str,
                    warning_text: str, peer_id: str) -> "Transaction":
        """
        Record that a researcher read and accepted the security notice.
        warning_hash = SHA-256 of the warning text — proves which version
        of the warning was acknowledged.

        :param file_hash:     File hash of the classified dataset.
        :param orcid_id:      Researcher's ORCID (entered manually by researcher).
        :param warning_text:  Full warning text as displayed.
        :param peer_id:       Device peer_id.
        """
        warning_hash = hashlib.sha256(
            warning_text.encode("utf-8")
        ).hexdigest()
        note = f"orcid={orcid_id} warning_hash={warning_hash}"
        return self._stage(Transaction(
            type=ACKNOWLEDGE, timestamp=time.time(),
            file_hash=file_hash, file_name="",
            peer_id=peer_id, note=note,
        ))

    def disclose(self, file_hash: str, prev_classification: str,
                 new_classification: str, peer_id: str,
                 disclosure_ref: str = "") -> "Transaction":
        """
        Lift an embargo — classification drops (e.g. restricted → public).

        :param file_hash:           Hash of the file being disclosed.
        :param prev_classification: Previous classification level string.
        :param new_classification:  New classification after disclosure.
        :param peer_id:             Disclosing peer (must be original classifier).
        :param disclosure_ref:      External reference number.
        """
        note = (f"prev={prev_classification} new={new_classification} "
                f"ref={disclosure_ref}")
        return self._stage(Transaction(
            type=DISCLOSE, timestamp=time.time(),
            file_hash=file_hash, file_name="",
            peer_id=peer_id, note=note,
        ))

    def revoke(self, file_hash: str, revoked_peer_id: str,
               reason: str, peer_id: str) -> "Transaction":
        """
        Withdraw access to a file from a specific peer.

        :param file_hash:        Hash of the file.
        :param revoked_peer_id:  The peer being revoked.
        :param reason:           Reason string.
        :param peer_id:          Revoking authority's peer_id.
        """
        note = f"revoked={revoked_peer_id} reason={reason}"
        return self._stage(Transaction(
            type=REVOKE, timestamp=time.time(),
            file_hash=file_hash, file_name="",
            peer_id=peer_id, note=note,
        ))

    def flag(self, file_hash: str, reason: str, detail: str,
             evidence: str, peer_id: str) -> "Transaction":
        """
        Flag a file as malicious or unsafe. Blocks execution on all devices
        that check the chain before running.

        :param file_hash: Hash of the malicious file.
        :param reason:    "attempted_system_write" | "attempted_subprocess" |
                          "resource_exhaustion" | "malicious_payload" | "other"
        :param detail:    Human-readable description of what was observed.
        :param evidence:  SHA-256 of the error log / sandbox exception trace.
        :param peer_id:   Flagging researcher's peer_id (ORCID-attributed).
        """
        note = f"reason={reason} evidence={evidence} detail={detail[:200]}"
        return self._stage(Transaction(
            type=FLAG, timestamp=time.time(),
            file_hash=file_hash, file_name="",
            peer_id=peer_id, note=note,
        ))

    def is_flagged(self, file_hash: str) -> Optional["Transaction"]:
        """Return the FLAG transaction if this file has been flagged, else None."""
        for block in self._chain:
            for tx in block.transactions:
                if tx.type == FLAG and tx.file_hash == file_hash:
                    return tx
        for tx in self._pending:
            if tx.type == FLAG and tx.file_hash == file_hash:
                return tx
        return None

    def get_classification(self, file_hash: str) -> Optional[dict]:
        """
        Return the most recent CLASSIFY transaction for a file, parsed into
        a dict: classification, level, embargo_until, contact_orcid.
        Returns None if no classification exists (file is public by default).
        """
        latest = None
        for block in self._chain:
            for tx in block.transactions:
                if tx.type == CLASSIFY and tx.file_hash == file_hash:
                    latest = tx
        if latest is None:
            return None
        # Parse note field
        parts = dict(p.split("=", 1) for p in latest.note.split()
                     if "=" in p)
        return {
            "classification": parts.get("class", "public"),
            "level":          int(parts.get("level", 0)),
            "embargo_until":  parts.get("embargo", ""),
            "contact_orcid":  parts.get("contact", ""),
            "ref":            parts.get("ref", ""),
            "timestamp":      latest.timestamp,
            "classified_by":  latest.peer_id,
        }

    def is_embargoed(self, file_hash: str) -> bool:
        """Return True if this file is under active embargo."""
        cls = self.get_classification(file_hash)
        if not cls:
            return False
        embargo = cls.get("embargo_until", "")
        if not embargo:
            return False
        import time as _time
        today = _time.strftime("%Y-%m-%d")
        return today < embargo

    def get_evaluations(self, dataset_hash: str) -> list["Transaction"]:
        """Return all EVALUATE transactions for a given dataset hash."""
        result = []
        for block in self._chain:
            for tx in block.transactions:
                if tx.type == EVALUATE and tx.merge_a == dataset_hash:
                    result.append(tx)
        return result

    def commit(self) -> Optional[Block]:
        """
        Mine all pending transactions into a new block and persist the chain.
        Returns the new Block, or None if there were no pending transactions.
        """
        if not self._pending:
            return None
        block = Block(
            index=len(self._chain),
            timestamp=time.time(),
            previous_hash=self._chain[-1].hash,
            transactions=list(self._pending),
            difficulty=self.difficulty,
        )
        self._chain.append(block)
        self._pending.clear()
        self._save()
        return block

    def commit_and_report(self) -> str:
        """commit() then return a one-line summary of the new block."""
        block = self.commit()
        if block is None:
            return "Nothing to commit."
        return (
            f"Block {block.index} mined  "
            f"txns={len(block.transactions)}  "
            f"nonce={block.nonce}  "
            f"hash={block.hash[:16]}..."
        )

    # -----------------------------------------------------------------------
    # Query API
    # -----------------------------------------------------------------------

    def get_seeders(self, file_hash: str) -> list[str]:
        """
        Return all peers currently seeding file_hash.
        Walks the full chain; SEED adds a peer, UNSEED removes it.
        """
        seeding: set[str] = set()
        for block in self._chain:
            for tx in block.transactions:
                if tx.file_hash == file_hash:
                    if tx.type == SEED:
                        seeding.add(tx.peer_id)
                    elif tx.type == UNSEED:
                        seeding.discard(tx.peer_id)
        return sorted(seeding)

    def get_latest(self, file_name: str) -> Optional[Transaction]:
        """
        Return the most recent ANNOUNCE or UPDATE transaction for file_name.
        This is the canonical current version of the named resource.
        """
        latest: Optional[Transaction] = None
        for block in self._chain:
            for tx in block.transactions:
                if tx.file_name == file_name and tx.type in (ANNOUNCE, UPDATE):
                    if latest is None or tx.timestamp > latest.timestamp:
                        latest = tx
        return latest

    def get_history(self, file_name: str) -> list[Transaction]:
        """Return all transactions touching file_name, chronological."""
        return sorted(
            (tx for block in self._chain
                for tx in block.transactions
                if tx.file_name == file_name),
            key=lambda t: t.timestamp,
        )

    def get_by_hash(self, file_hash: str) -> list[Transaction]:
        """Return all transactions that reference file_hash in any field."""
        results = []
        for block in self._chain:
            for tx in block.transactions:
                if file_hash in (tx.file_hash, tx.prev_hash, tx.merge_a, tx.merge_b):
                    results.append(tx)
        return results

    def is_retired(self, file_hash: str) -> bool:
        """Return True if file_hash has a RETIRE record (i.e. superseded)."""
        return any(
            tx.type == RETIRE and tx.file_hash == file_hash
            for block in self._chain
            for tx in block.transactions
        )

    def all_files(self) -> dict[str, str]:
        """
        Return {file_name: current_hash} for every tracked file whose current
        hash is not retired. Represents the live state of the registry.
        """
        current: dict[str, str] = {}
        for block in self._chain:
            for tx in block.transactions:
                if tx.type in (ANNOUNCE, UPDATE) and tx.file_name:
                    current[tx.file_name] = tx.file_hash
        return {name: h for name, h in current.items() if not self.is_retired(h)}

    def merge_chain(self, file_name: str) -> list[tuple[str, str]]:
        """
        Return the merge ancestry of file_name as a list of (hash_a, hash_b) pairs,
        oldest first. Useful for reconstructing the provenance of a merged bin.
        """
        latest = self.get_latest(file_name)
        if latest is None:
            return []
        pairs: list[tuple[str, str]] = []
        queue = [latest.file_hash]
        seen: set[str] = set()
        while queue:
            h = queue.pop(0)
            if h in seen:
                continue
            seen.add(h)
            for block in self._chain:
                for tx in block.transactions:
                    if tx.type == MERGE and tx.file_hash == h:
                        pairs.append((tx.merge_a, tx.merge_b))
                        queue.extend([tx.merge_a, tx.merge_b])
        return pairs

    # -----------------------------------------------------------------------
    # Chain integrity
    # -----------------------------------------------------------------------

    def is_valid_chain(self) -> bool:
        """Verify every block's internal integrity and the hash chain linkage."""
        for i, block in enumerate(self._chain):
            if not block.is_valid():
                return False
            if i > 0 and block.previous_hash != self._chain[i - 1].hash:
                return False
        return True

    # -----------------------------------------------------------------------
    # File hashing utilities
    # -----------------------------------------------------------------------

    @staticmethod
    def hash_file(path: str, chunk_size: int = 1 << 20) -> str:
        """SHA-256 hash of any file on disk. Streams in 1MB chunks."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def hash_ptorrent(path: str) -> str:
        """
        SHA-256 of the canonical JSON form of a .ptorrent file.
        Canonical = keys sorted, no extra whitespace, UTF-8.
        Ensures the hash is stable regardless of how the file was formatted.
        """
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False,
                               separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        """SHA-256 of a bytes object (e.g. in-memory .bin checkpoint)."""
        return hashlib.sha256(data).hexdigest()

    # -----------------------------------------------------------------------
    # Summary / display
    # -----------------------------------------------------------------------

    def summary(self) -> str:
        files   = self.all_files()
        pending = len(self._pending)
        valid   = self.is_valid_chain()
        lines   = [
            f"PTorrentChain  blocks={len(self._chain)}  "
            f"valid={'YES' if valid else 'NO'}  "
            f"difficulty={self.difficulty}  "
            f"pending_txns={pending}",
            f"Tracked files ({len(files)}):",
        ]
        for name, h in sorted(files.items()):
            seeders = self.get_seeders(h)
            lines.append(
                f"  {name:<40}  [{h[:16]}...]  "
                f"seeders={len(seeders)}"
                + (f"  ({', '.join(seeders[:2])}{'...' if len(seeders)>2 else ''})"
                   if seeders else "")
            )
        if pending:
            lines.append(f"Pending (uncommitted): {pending} transactions")
        return "\n".join(lines)

    def block_summary(self, index: int) -> str:
        """One-line summary of a specific block."""
        b = self._chain[index]
        return (
            f"Block {b.index:>4}  "
            f"ts={b.timestamp:.0f}  "
            f"txns={len(b.transactions):>3}  "
            f"nonce={b.nonce:>6}  "
            f"hash={b.hash[:16]}..."
        )

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    def _stage(self, tx: Transaction) -> Transaction:
        self._pending.append(tx)
        return tx

    def _genesis(self) -> None:
        genesis_tx = Transaction(
            type=GENESIS,
            timestamp=time.time(),
            note="PTorrent chain genesis — github.com/michaelrendier/PTorrent",
        )
        block = Block(
            index=0,
            timestamp=time.time(),
            previous_hash=self.GENESIS_HASH,
            transactions=[genesis_tx],
            difficulty=self.difficulty,
        )
        self._chain.append(block)
        self._save()

    def _save(self) -> None:
        data = {
            "ptorrent_chain_version": "1.0",
            "difficulty": self.difficulty,
            "chain_length": len(self._chain),
            "tip_hash": self._chain[-1].hash if self._chain else "",
            "blocks": [b.to_dict() for b in self._chain],
        }
        tmp = self.store_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.store_path)

    def _load(self) -> None:
        if not os.path.exists(self.store_path):
            return
        with open(self.store_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.difficulty = data.get("difficulty", self.difficulty)
        self._chain = [Block.from_dict(b) for b in data.get("blocks", [])]


# ---------------------------------------------------------------------------
# CLI — standalone usage
# ---------------------------------------------------------------------------

def _cli() -> None:
    import sys

    store = os.environ.get("PTORRENT_CHAIN", "ptorrent_chain.json")
    chain = PTorrentChain(store_path=store)

    args = sys.argv[1:]

    if not args or args[0] == "summary":
        print(chain.summary())

    elif args[0] == "blocks":
        for i in range(len(chain._chain)):
            print(chain.block_summary(i))

    elif args[0] == "announce" and len(args) >= 2:
        path    = args[1]
        peer_id = args[2] if len(args) > 2 else os.uname().nodename
        note    = args[3] if len(args) > 3 else ""
        if path.endswith(".ptorrent"):
            h = PTorrentChain.hash_ptorrent(path)
        else:
            h = PTorrentChain.hash_file(path)
        size = os.path.getsize(path)
        chain.announce(os.path.basename(path), h, size, peer_id, note)
        print(chain.commit_and_report())
        print(f"  file={os.path.basename(path)}  hash={h[:32]}...")

    elif args[0] == "update" and len(args) >= 4:
        # update <file_name> <old_hash> <new_path> [peer_id]
        name     = args[1]
        old_hash = args[2]
        new_path = args[3]
        peer_id  = args[4] if len(args) > 4 else os.uname().nodename
        if new_path.endswith(".ptorrent"):
            new_hash = PTorrentChain.hash_ptorrent(new_path)
        else:
            new_hash = PTorrentChain.hash_file(new_path)
        size = os.path.getsize(new_path)
        chain.update(name, old_hash, new_hash, size, peer_id)
        print(chain.commit_and_report())
        print(f"  {name}  {old_hash[:12]}... → {new_hash[:12]}...")

    elif args[0] == "seed" and len(args) >= 3:
        # seed <file_hash> <peer_id>
        chain.seed(args[1], args[2])
        print(chain.commit_and_report())

    elif args[0] == "unseed" and len(args) >= 3:
        chain.unseed(args[1], args[2])
        print(chain.commit_and_report())

    elif args[0] == "merge" and len(args) >= 4:
        # merge <hash_a> <hash_b> <result_path> [peer_id]
        hash_a  = args[1]
        hash_b  = args[2]
        res_path = args[3]
        peer_id  = args[4] if len(args) > 4 else os.uname().nodename
        res_hash = PTorrentChain.hash_file(res_path)
        size     = os.path.getsize(res_path)
        chain.merge(hash_a, hash_b, res_hash,
                    os.path.basename(res_path), size, peer_id)
        print(chain.commit_and_report())
        print(f"  {hash_a[:12]}... + {hash_b[:12]}... → {res_hash[:12]}...")

    elif args[0] == "seeders" and len(args) >= 2:
        for p in chain.get_seeders(args[1]):
            print(p)

    elif args[0] == "latest" and len(args) >= 2:
        tx = chain.get_latest(args[1])
        if tx:
            print(json.dumps(tx.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(f"Not found: {args[1]}", file=sys.stderr)
            sys.exit(1)

    elif args[0] == "history" and len(args) >= 2:
        for tx in chain.get_history(args[1]):
            print(f"{tx.type:<8}  {tx.file_hash[:16]}...  "
                  f"peer={tx.peer_id or '-'}  ts={tx.timestamp:.0f}")

    elif args[0] == "verify":
        ok = chain.is_valid_chain()
        print(f"Chain valid: {'YES' if ok else 'NO'}  "
              f"blocks={len(chain._chain)}")
        sys.exit(0 if ok else 1)

    elif args[0] == "hash" and len(args) >= 2:
        path = args[1]
        if path.endswith(".ptorrent"):
            print(PTorrentChain.hash_ptorrent(path))
        else:
            print(PTorrentChain.hash_file(path))

    else:
        print(
            "PTorrent Chain Engine v1.0\n"
            "\n"
            "Usage:\n"
            "  chain.py summary\n"
            "  chain.py blocks\n"
            "  chain.py announce  <file_path>  [peer_id]  [note]\n"
            "  chain.py update    <name> <old_hash> <new_path>  [peer_id]\n"
            "  chain.py seed      <file_hash>  <peer_id>\n"
            "  chain.py unseed    <file_hash>  <peer_id>\n"
            "  chain.py merge     <hash_a> <hash_b> <result_path>  [peer_id]\n"
            "  chain.py seeders   <file_hash>\n"
            "  chain.py latest    <file_name>\n"
            "  chain.py history   <file_name>\n"
            "  chain.py verify\n"
            "  chain.py hash      <file_path>\n"
            "\n"
            "Env: PTORRENT_CHAIN=/path/to/chain.json  (default: ./ptorrent_chain.json)"
        )


if __name__ == "__main__":
    _cli()
