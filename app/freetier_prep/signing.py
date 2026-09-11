"""Ed25519 transcript signing.

The signature binds the platform's attestation (user, module, task
outcomes, date) and only *references* the artifact repo — verification
never depends on student-owned mutable files.
"""

import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

PRIVATE_PEM = "transcript-signing.pem"
PUBLIC_PEM = "transcript-signing.pub.pem"


def canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class TranscriptSigner:
    def __init__(self, keys_dir: Path):
        self.keys_dir = Path(keys_dir)
        self._private = self._load_or_create()

    def _load_or_create(self) -> Ed25519PrivateKey:
        priv_path = self.keys_dir / PRIVATE_PEM
        if priv_path.exists():
            return serialization.load_pem_private_key(
                priv_path.read_bytes(), password=None
            )
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        key = Ed25519PrivateKey.generate()
        priv_path.write_bytes(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ))
        (self.keys_dir / PUBLIC_PEM).write_bytes(key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ))
        return key

    @property
    def public_key_pem(self) -> str:
        return (self.keys_dir / PUBLIC_PEM).read_text()

    def sign(self, payload: dict) -> tuple[str, str]:
        """Returns (canonical_json, signature_hex)."""
        doc = canonical_json(payload)
        sig = self._private.sign(doc.encode())
        return doc, sig.hex()

    def verify(self, payload_json: str, signature_hex: str) -> bool:
        pub: Ed25519PublicKey = self._private.public_key()
        try:
            pub.verify(bytes.fromhex(signature_hex), payload_json.encode())
            return True
        except Exception:
            return False
