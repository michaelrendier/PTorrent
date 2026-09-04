"""ORCID identity + the capability gate.

States: ANONYMOUS -> CLAIMED (checksum ok) -> VERIFIED.

`identity_verify()` does full OAuth 3-legged in production. This build ships the
stopgap that needs no registered client: checksum validation + a public-record
resolve against pub.orcid.org. `begin()/complete()` are the OAuth entry points
and raise E_UNSUPPORTED until a client id is configured.

Only VERIFIED unlocks: seeing another researcher's contact fields, sending
request_access / contact, seeding TLP>CLEAR, acknowledging Level 3, and voting.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass

from ._util import now_iso, orcid_checksum_ok, orcid_normalise
from .errors import PtErr, PtError

ANONYMOUS = "ANONYMOUS"
CLAIMED = "CLAIMED"
VERIFIED = "VERIFIED"


@dataclass
class Identity:
    state: str = ANONYMOUS
    orcid: str = ""
    name: str = ""
    verified_at: str = ""
    method: str = ""          # "public_api" | "oauth"

    def to_dict(self) -> dict:
        return {"state": self.state, "orcid": self.orcid, "name": self.name,
                "verified_at": self.verified_at, "method": self.method}

    @property
    def is_verified(self) -> bool:
        return self.state == VERIFIED


class IdentityManager:
    def __init__(self, token_path: str, db, oauth_client_id: str | None = None):
        self.token_path = token_path
        self.db = db
        self.oauth_client_id = oauth_client_id
        self._id = self._load()

    def current(self) -> Identity:
        return self._id

    # ── claim (offline checksum) ──
    def set_orcid(self, value: str) -> Identity:
        norm = orcid_normalise(value)
        if not norm or not orcid_checksum_ok(norm):
            raise PtError(PtErr.E_INVAL, f"{value!r} is not a valid ORCID (ISO 7064 check failed)")
        self._id = Identity(state=CLAIMED, orcid=norm)
        self._save()
        return self._id

    def clear(self) -> None:
        self._id = Identity()
        try:
            os.remove(self.token_path)
        except OSError:
            pass

    # ── verify (public API resolve — the stopgap) ──
    def verify_public(self, timeout: float = 8.0) -> Identity:
        if self._id.state == ANONYMOUS or not self._id.orcid:
            raise PtError(PtErr.E_INVAL, "set an ORCID before verifying")
        url = f"https://pub.orcid.org/v3.0/{self._id.orcid}/person"
        req = urllib.request.Request(url, headers={"Accept": "application/json",
                                                   "User-Agent": "PtorrentCore/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
        except Exception as e:
            raise PtError(PtErr.E_IO, f"ORCID public API unreachable: {e}") from None
        nm = (data.get("name") or {})
        given = ((nm.get("given-names") or {}) or {}).get("value", "")
        family = ((nm.get("family-name") or {}) or {}).get("value", "")
        self._id = Identity(state=VERIFIED, orcid=self._id.orcid,
                            name=(given + " " + family).strip() or self._id.orcid,
                            verified_at=now_iso(), method="public_api")
        self._save()
        return self._id

    # ── OAuth (entry points; require a registered client) ──
    def begin(self, redirect_uri: str) -> dict:
        if not self.oauth_client_id:
            raise PtError(PtErr.E_UNSUPPORTED,
                          "OAuth requires a registered ORCID client id; use verify_public() meanwhile")
        state = os.urandom(12).hex()
        auth = (f"https://orcid.org/oauth/authorize?client_id={self.oauth_client_id}"
                f"&response_type=code&scope=/authenticate&redirect_uri={redirect_uri}&state={state}")
        self.db.config_set("oauth_state", state)
        return {"authorize_url": auth, "state": state}

    def complete(self, code: str, state: str) -> Identity:
        raise PtError(PtErr.E_UNSUPPORTED,
                      "OAuth token exchange not enabled in this build")

    # ── capability gate ──
    def require_verified(self, action: str) -> Identity:
        if not self._id.is_verified:
            raise PtError(PtErr.E_IDENTITY, f"{action} requires a VERIFIED ORCID identity")
        return self._id

    def peer_id(self, device_hash: str = "") -> str:
        if self._id.orcid:
            return f"ORCID:{self._id.orcid}" + (f"@{device_hash}" if device_hash else "")
        return f"anon:{device_hash or 'local'}"

    # ── persistence ──
    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.token_path) or ".", exist_ok=True)
        with open(self.token_path, "w", encoding="utf-8") as f:
            json.dump(self._id.to_dict(), f)
        try:
            os.chmod(self.token_path, 0o600)
        except OSError:
            pass

    def _load(self) -> Identity:
        if not os.path.exists(self.token_path):
            return Identity()
        try:
            with open(self.token_path, encoding="utf-8") as f:
                d = json.load(f)
            return Identity(**{k: d.get(k, "") for k in
                               ("state", "orcid", "name", "verified_at", "method")})
        except Exception:
            return Identity()
