# PTorrent Chain Specification — v1.0

**Author:** Cody Michael Allison  
**Built:** Claude Code (claude-sonnet-4-6)  
**Status:** Implemented — `android/PtolemySeeder/app/src/main/python/ptorrent_chain.py`  
**License:** GNU GPL v3

---

## Purpose

The PTorrent Chain is an append-only distributed ledger that tracks the complete
lifecycle of `.ptorrent` descriptor files and `.bin` checkpoint binaries:

- **Publication** — a file exists at this hash and size
- **Version updates** — old hash is retired, new hash is canonical
- **Seeder registry** — which peers have which files, live
- **Merge provenance** — β-weighted bin merges recorded with full ancestry
- **Update distribution** — every device running the chain can detect when a
  `.ptorrent` they hold has been superseded

The chain is not a cryptocurrency. There is no token, no financial layer, and no
mining reward. Proof of Work exists solely for Sybil resistance — to make it
non-trivial to flood the ledger with fake announcements.

---

## Design Constraints

- **Stdlib only.** Runs on Chaquopy 15.0.1 / Python 3.12 on Android ARM64.
  No external dependencies. `hashlib`, `json`, `os`, `time`, `dataclasses`.
- **Human-readable persistence.** Chain stored as `ptorrent_chain.json` —
  inspectable with any text editor or `jq`.
- **Atomic writes.** Chain file written to `.tmp` then `os.replace()` —
  safe against mid-write crashes on Android.
- **Lightweight PoW.** difficulty=2 requires finding a SHA-256 hash with 2
  leading zero hex chars (~256 hashes average). Fast on ARM64, slow enough
  to deter spam.

---

## Data Structures

### Transaction

The atomic unit of the ledger. Every event is a Transaction.

```json
{
  "type":       "ANNOUNCE",
  "timestamp":  1748822400.0,
  "file_hash":  "a3f2c1...(SHA-256 hex, 64 chars)",
  "file_name":  "monad_physics.bin",
  "file_size":  10485760,
  "peer_id":    "192.168.1.5:6881",
  "prev_hash":  "",
  "merge_a":    "",
  "merge_b":    "",
  "note":       "human-readable annotation",
  "tx_hash":    "b7e3a9...(SHA-256 of all other fields, 64 chars)"
}
```

**`tx_hash`** is computed as SHA-256 of the canonical JSON of all other fields
(keys sorted, `ensure_ascii=False`). It is the transaction ID and integrity check.
On deserialisation, `tx_hash` is recomputed and compared to the stored value —
any mismatch raises `ValueError`.

#### Transaction Types

| Type | Meaning | Key fields |
|------|---------|------------|
| `GENESIS` | Chain genesis marker | `note` |
| `ANNOUNCE` | File exists at this hash | `file_name`, `file_hash`, `file_size`, `peer_id` |
| `UPDATE` | New version of a named file | `file_name`, `file_hash`, `prev_hash`, `peer_id` |
| `RETIRE` | This hash is superseded | `file_name`, `file_hash` (= old hash), `prev_hash` (= old hash) |
| `SEED` | Peer is actively seeding | `file_hash`, `peer_id` |
| `UNSEED` | Peer has stopped seeding | `file_hash`, `peer_id` |
| `MERGE` | Two bins merged into one | `file_hash` (result), `merge_a`, `merge_b`, `peer_id` |

`UPDATE` always pairs with `RETIRE` — the `update()` method stages both
atomically. `RETIRE` is staged first so the ledger always has a clear
retirement record before the successor is announced.

---

### Block

```json
{
  "index":         42,
  "timestamp":     1748822400.0,
  "previous_hash": "0a3f2c...(hash of block 41)",
  "merkle":        "7b9e1d...(Merkle root of transaction tx_hashes)",
  "difficulty":    2,
  "nonce":         317,
  "hash":          "003a7f...(starts with 'difficulty' zero chars)",
  "transactions":  [ ...Transaction objects... ]
}
```

**`hash`** = SHA-256 of the canonical JSON of `{index, timestamp, previous_hash,
merkle, difficulty, nonce}`. Must start with `difficulty` zero hex nibbles.

**Block 0** (genesis) has `previous_hash = "0" * 64`.

---

### Chain file (`ptorrent_chain.json`)

```json
{
  "ptorrent_chain_version": "1.0",
  "difficulty":   2,
  "chain_length": 5,
  "tip_hash":     "003a7f...",
  "blocks":       [ ...Block objects... ]
}
```

`tip_hash` is the hash of the last committed block — quick-check for sync.

---

## Merkle Tree

Standard binary Merkle tree over the `tx_hash` values of a block's transactions.

```
Algorithm:
  layer = [tx.tx_hash for tx in transactions]
  while len(layer) > 1:
      if len(layer) is odd: layer.append(layer[-1])   # duplicate last
      layer = [SHA-256(layer[i] + layer[i+1]) for i in range(0, len(layer), 2)]
  merkle_root = layer[0]

Empty transaction list: merkle_root = SHA-256("")
```

---

## Proof of Work

```
target = "0" * difficulty
nonce  = 0
while True:
    header = canonical_json({index, timestamp, previous_hash, merkle, difficulty, nonce})
    h      = SHA-256(header)
    if h.startswith(target): break
    nonce += 1

block.nonce = nonce
block.hash  = h
```

**difficulty=2** requires an average of 256 SHA-256 hashes. On a 2.4GHz ARM64
Cortex-A78 (Snapdragon 888) this takes ~0.1ms. On a Cortex-A55 (low-end Android)
~0.5ms. Suitable for mobile — one block commit per corpus crawl event is fine.

For higher-security deployments, raise difficulty to 3 (4,096 hashes avg, ~2ms
on A78) or 4 (65,536 hashes, ~30ms). Set in `PTorrentChain(difficulty=N)`.

---

## Query Semantics

### `get_seeders(file_hash) → list[str]`

Walks the full chain from genesis. `SEED` adds `peer_id` to the seeder set;
`UNSEED` removes it. Returns the current set as a sorted list.
Correct even if SEED/UNSEED events span multiple blocks.

### `get_latest(file_name) → Transaction | None`

Returns the most recent `ANNOUNCE` or `UPDATE` transaction for `file_name`
by timestamp. This is the canonical current version.

### `is_retired(file_hash) → bool`

Returns `True` if any `RETIRE` transaction has `file_hash` as its `file_hash`
field. Retired hashes should not be used as starting points for new training.

### `all_files() → dict[str, str]`

Returns `{file_name: current_hash}` for all tracked files whose current hash
is not retired. The live state of the registry.

### `merge_chain(file_name) → list[tuple[str, str]]`

Reconstructs the merge ancestry of `file_name`'s current hash. Returns pairs
`(hash_a, hash_b)` in reverse merge order (most recent first). Enables full
provenance tracking of how a corpus bin was assembled.

---

## File Hashing

| File type | Method |
|-----------|--------|
| `.bin` (binary) | `SHA-256(file_bytes)` streamed in 1MB chunks |
| `.ptorrent` (JSON) | `SHA-256(canonical_json)` — keys sorted, no whitespace, UTF-8 |
| In-memory bytes | `SHA-256(data)` direct |

The `.ptorrent` canonical hash ensures stability regardless of how the JSON was
formatted (pretty-printed vs. minified, different key ordering). Two semantically
identical `.ptorrent` files produce the same hash.

---

## Android Integration

The chain engine runs inside the APK via Chaquopy. Recommended integration points:

**In `SeedService.kt`:** call `chain.announce()` + `chain.seed()` + `chain.commit()`
after each corpus checkpoint is written. The peer_id should be the device's
`android.provider.Settings.Secure.ANDROID_ID` (stable, anonymous).

**In `seed_runner.py`:** call `chain.announce()` after `save_session()`. The
file hash can be computed with `PTorrentChain.hash_file(bin_path)`.

**Chain file location:** `extDir()/ptorrent_chain.json` — same directory as
corpus bins and ptorrent inbox.

```python
# In seed_runner.py, after save_session():
from ptorrent_chain import PTorrentChain
chain = PTorrentChain(store_path=os.path.join(out_dir, "ptorrent_chain.json"))
h = PTorrentChain.hash_file(bin_path)
chain.announce(os.path.basename(bin_path), h, os.path.getsize(bin_path), peer_id)
chain.commit()
```

**In `CorpusDetailActivity.kt`:** expose chain summary via the MCP server
(future) or display tip_hash + block count in the corpus detail header.

---

## CLI Reference

```bash
# Set chain file location (default: ./ptorrent_chain.json)
export PTORRENT_CHAIN=/path/to/ptorrent_chain.json

# Register a file (computes hash automatically)
python ptorrent_chain.py announce monad_physics.bin mydevice

# Mark as being seeded
python ptorrent_chain.py seed <file_hash> mydevice:6881

# Stop seeding
python ptorrent_chain.py unseed <file_hash> mydevice:6881

# Record a new version of a .ptorrent
python ptorrent_chain.py update physics.ptorrent <old_hash> physics.ptorrent mydevice

# Record a β-merge
python ptorrent_chain.py merge <hash_a> <hash_b> monad_physics_merged.bin mydevice

# Query
python ptorrent_chain.py seeders <file_hash>
python ptorrent_chain.py latest  monad_physics.bin
python ptorrent_chain.py history physics.ptorrent

# Verify chain integrity
python ptorrent_chain.py verify

# Print chain hash of a file
python ptorrent_chain.py hash monad_physics.bin
python ptorrent_chain.py hash physics.ptorrent   # uses canonical JSON hash

# Block explorer
python ptorrent_chain.py blocks
python ptorrent_chain.py summary
```

---

## Future Extensions (not in v1.0)

| Feature | Notes |
|---------|-------|
| **Peer sync** | Share chain state between devices over LAN/WiFi — merge two chains by longest-valid-chain rule |
| **DHT integration** | Announce tip_hash + seeders to Kademlia DHT — enables peer discovery without adb |
| **Signed transactions** | Ed25519 signature on tx_hash — verify authorship without trusting peer_id string |
| **Compact proofs** | Merkle inclusion proofs — prove a transaction is in a block without sending the full block |
| **Chain pruning** | Remove retired/spent transactions from old blocks, retain only proofs |
| **Cross-chain sync** | Multiple chains (one per device fleet) merged at β-weighted consensus |

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 1.0 | 2026-06-02 | Initial implementation. 7 transaction types, Merkle tree, PoW difficulty 2, full query API, CLI, Chaquopy-compatible. |
