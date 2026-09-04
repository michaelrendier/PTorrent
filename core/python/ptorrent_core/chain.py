"""PTorrent custody chain — append-only, hash-linked, ORCID-attributed.

Adapted from android/PtolemySeeder/app/src/main/python/ptorrent_chain.py
(Cody Michael Allison, LGPL-3.0-or-later). Kept: Merkle root, light PoW, prev_hash
linkage, per-tx integrity hash, atomic JSON persistence. Added for core v1:

  * every tx carries `actor`, `object_hash`, `parent_hash`, and a `marking`
    digest {tlp, level, labels_hash}
  * new tx classes: ACQUIRE, PHONEBOOK_ADD, PHONEBOOK_VERIFY, REQUEST, GRANT,
    DENY, VOTE, VOTE_ADDRESSED, VOTE_DISPUTED, SEED_LISTED, SEED_UNLISTED
  * marking inheritance + no-silent-downgrade is enforced in engine/custody,
    the chain only records facts.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field

from ._util import sha256_text

GENESIS = "GENESIS"
ANNOUNCE = "ANNOUNCE"
ACQUIRE = "ACQUIRE"
UPDATE = "UPDATE"
RETIRE = "RETIRE"
SEED = "SEED"
UNSEED = "UNSEED"
SEED_LISTED = "SEED_LISTED"
SEED_UNLISTED = "SEED_UNLISTED"
MERGE = "MERGE"
EVALUATE = "EVALUATE"
PHONEBOOK_ADD = "PHONEBOOK_ADD"
PHONEBOOK_VERIFY = "PHONEBOOK_VERIFY"
CLASSIFY = "CLASSIFY"
ACKNOWLEDGE = "ACKNOWLEDGE"
DISCLOSE = "DISCLOSE"
REVOKE = "REVOKE"
FLAG = "FLAG"
NOTIFY = "NOTIFY"
REQUEST = "REQUEST"
GRANT = "GRANT"
DENY = "DENY"
VOTE = "VOTE"
VOTE_ADDRESSED = "VOTE_ADDRESSED"
VOTE_DISPUTED = "VOTE_DISPUTED"


def _sha(s: str) -> str:
    return sha256_text(s)


def merkle_root(hashes: list[str]) -> str:
    if not hashes:
        return _sha("")
    layer = list(hashes)
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [_sha(layer[i] + layer[i + 1]) for i in range(0, len(layer), 2)]
    return layer[0]


@dataclass
class Tx:
    type: str
    timestamp: float
    actor: str = ""              # ORCID:xxxx-xxxx-xxxx-xxxx@device  or  anon:<peer>
    object_hash: str = ""
    parent_hash: str = ""        # lineage: the artifact this one descends from
    prev_hash: str = ""          # supersede link (UPDATE/RETIRE/VOTE_*)
    file_name: str = ""
    file_size: int = 0
    merge_a: str = ""
    merge_b: str = ""
    marking: dict = field(default_factory=dict)   # {tlp, level, labels_hash}
    note: str = ""
    sig: str = ""
    tx_hash: str = field(default="", init=False)

    def __post_init__(self):
        self.tx_hash = self._compute()

    def _compute(self) -> str:
        payload = json.dumps({
            "type": self.type, "timestamp": self.timestamp, "actor": self.actor,
            "object_hash": self.object_hash, "parent_hash": self.parent_hash,
            "prev_hash": self.prev_hash, "file_name": self.file_name,
            "file_size": self.file_size, "merge_a": self.merge_a, "merge_b": self.merge_b,
            "marking": self.marking, "note": self.note, "sig": self.sig,
        }, sort_keys=True, ensure_ascii=False)
        return _sha(payload)

    def valid(self) -> bool:
        return self.tx_hash == self._compute()

    def to_dict(self) -> dict:
        return asdict(self) | {"tx_hash": self.tx_hash}

    @classmethod
    def from_dict(cls, d: dict) -> "Tx":
        t = cls(
            type=d["type"], timestamp=d["timestamp"], actor=d.get("actor", ""),
            object_hash=d.get("object_hash", ""), parent_hash=d.get("parent_hash", ""),
            prev_hash=d.get("prev_hash", ""), file_name=d.get("file_name", ""),
            file_size=d.get("file_size", 0), merge_a=d.get("merge_a", ""),
            merge_b=d.get("merge_b", ""), marking=d.get("marking", {}),
            note=d.get("note", ""), sig=d.get("sig", ""),
        )
        stored = d.get("tx_hash", "")
        if stored and stored != t.tx_hash:
            raise ValueError(f"tx integrity failure stored={stored[:12]} computed={t.tx_hash[:12]}")
        return t


@dataclass
class Block:
    index: int
    timestamp: float
    previous_hash: str
    transactions: list
    difficulty: int = 2
    nonce: int = field(default=0, init=False)
    merkle: str = field(default="", init=False)
    hash: str = field(default="", init=False)

    def __post_init__(self):
        self.merkle = merkle_root([t.tx_hash for t in self.transactions])
        self._mine()

    def _header(self, nonce: int) -> str:
        return json.dumps({"index": self.index, "timestamp": self.timestamp,
                           "previous_hash": self.previous_hash, "merkle": self.merkle,
                           "difficulty": self.difficulty, "nonce": nonce}, sort_keys=True)

    def _mine(self):
        target = "0" * self.difficulty
        n = 0
        while True:
            h = _sha(self._header(n))
            if h.startswith(target):
                self.nonce, self.hash = n, h
                return
            n += 1

    def valid(self) -> bool:
        if not all(t.valid() for t in self.transactions):
            return False
        if merkle_root([t.tx_hash for t in self.transactions]) != self.merkle:
            return False
        return _sha(self._header(self.nonce)) == self.hash and self.hash.startswith("0" * self.difficulty)

    def to_dict(self) -> dict:
        return {"index": self.index, "timestamp": self.timestamp,
                "previous_hash": self.previous_hash, "merkle": self.merkle,
                "difficulty": self.difficulty, "nonce": self.nonce, "hash": self.hash,
                "transactions": [t.to_dict() for t in self.transactions]}

    @classmethod
    def from_dict(cls, d: dict) -> "Block":
        b = object.__new__(cls)
        b.index = d["index"]; b.timestamp = d["timestamp"]
        b.previous_hash = d["previous_hash"]; b.difficulty = d.get("difficulty", 2)
        b.transactions = [Tx.from_dict(x) for x in d.get("transactions", [])]
        b.nonce = d["nonce"]; b.merkle = d["merkle"]; b.hash = d["hash"]
        if not b.valid():
            raise ValueError(f"block {b.index} integrity failure")
        return b


class CustodyChain:
    GENESIS_HASH = "0" * 64

    def __init__(self, store_path: str, difficulty: int = 2):
        self.store_path = store_path
        self.difficulty = difficulty
        self._pending: list[Tx] = []
        self._chain: list[Block] = []
        self._load()
        if not self._chain:
            self._genesis()

    # ── staging + commit ──
    def stage(self, tx: Tx) -> Tx:
        self._pending.append(tx)
        return tx

    def commit(self) -> Block | None:
        if not self._pending:
            return None
        block = Block(index=len(self._chain), timestamp=time.time(),
                      previous_hash=self._chain[-1].hash,
                      transactions=list(self._pending), difficulty=self.difficulty)
        self._chain.append(block)
        self._pending.clear()
        self._save()
        return block

    # ── convenience constructors ──
    def add_tx(self, type: str, *, actor="", object_hash="", parent_hash="", prev_hash="",
               file_name="", file_size=0, merge_a="", merge_b="", marking=None,
               note="", sig="", commit=True) -> Tx:
        tx = self.stage(Tx(type=type, timestamp=time.time(), actor=actor,
                           object_hash=object_hash, parent_hash=parent_hash,
                           prev_hash=prev_hash, file_name=file_name, file_size=file_size,
                           merge_a=merge_a, merge_b=merge_b, marking=marking or {},
                           note=note, sig=sig))
        if commit:
            self.commit()
        return tx

    # ── queries ──
    def all_tx(self):
        for b in self._chain:
            yield from b.transactions
        yield from self._pending

    def by_object(self, object_hash: str) -> list[Tx]:
        return [t for t in self.all_tx()
                if object_hash in (t.object_hash, t.parent_hash, t.merge_a, t.merge_b)]

    def latest_of_type(self, type: str, object_hash: str) -> Tx | None:
        out = None
        for t in self.all_tx():
            if t.type == type and t.object_hash == object_hash:
                out = t
        return out

    def seeders(self, object_hash: str) -> list[str]:
        live: set[str] = set()
        for t in self.all_tx():
            if t.object_hash != object_hash:
                continue
            if t.type == SEED:
                live.add(t.actor)
            elif t.type == UNSEED:
                live.discard(t.actor)
        return sorted(live)

    def classification(self, object_hash: str) -> dict | None:
        t = self.latest_of_type(CLASSIFY, object_hash)
        if not t:
            return None
        parts = dict(p.split("=", 1) for p in t.note.split() if "=" in p)
        return {"classification": parts.get("class", "public"),
                "level": int(parts.get("level", 0)),
                "embargo_until": parts.get("embargo", ""),
                "contact_orcid": parts.get("contact", ""),
                "marking": t.marking, "classified_by": t.actor, "ts": t.timestamp}

    def is_flagged(self, object_hash: str) -> Tx | None:
        for t in self.all_tx():
            if t.type == FLAG and t.object_hash == object_hash:
                return t
        return None

    def valid_chain(self) -> bool:
        for i, b in enumerate(self._chain):
            if not b.valid():
                return False
            if i and b.previous_hash != self._chain[i - 1].hash:
                return False
        return True

    def tip(self) -> str:
        return self._chain[-1].hash if self._chain else ""

    @property
    def height(self) -> int:
        return len(self._chain)

    def export_native(self) -> dict:
        return {"ptorrent_chain_version": "1.1", "difficulty": self.difficulty,
                "tip_hash": self.tip(), "height": self.height,
                "blocks": [b.to_dict() for b in self._chain]}

    # ── internal ──
    def _genesis(self):
        gtx = Tx(type=GENESIS, timestamp=time.time(),
                 note="PTorrent custody chain genesis")
        self._chain.append(Block(0, time.time(), self.GENESIS_HASH, [gtx], self.difficulty))
        self._save()

    def _save(self):
        tmp = self.store_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.export_native(), f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.store_path)

    def _load(self):
        if not os.path.exists(self.store_path):
            return
        with open(self.store_path, encoding="utf-8") as f:
            data = json.load(f)
        self.difficulty = data.get("difficulty", self.difficulty)
        self._chain = [Block.from_dict(b) for b in data.get("blocks", [])]
