from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from services.integrations.ports import CredentialResolverPort

LOGGER = logging.getLogger(__name__)

_KEY_ID_LENGTH = 8


def _derive_key(master_key: bytes, key_id: str) -> bytes:
    return hashlib.sha256(master_key + key_id.encode()).digest()


def _generate_key_id() -> str:
    return secrets.token_hex(_KEY_ID_LENGTH)


class CredentialEncryptionService:
    def __init__(self, master_key: bytes | None = None):
        self._master_key = master_key or self._load_master_key()

    @staticmethod
    def _load_master_key() -> bytes:
        env_key = os.getenv("INTEGRATION_MASTER_KEY", "")
        if env_key:
            return hashlib.sha256(env_key.encode()).digest()
        key_file = os.getenv("INTEGRATION_KEY_FILE", "app_data/.integration_key")
        if os.path.isfile(key_file):
            with open(key_file, "rb") as fh:
                return fh.read()[:64]
        generated = secrets.token_bytes(64)
        os.makedirs(os.path.dirname(key_file) or ".", exist_ok=True)
        with open(key_file, "wb") as fh:
            fh.write(generated)
        return generated

    def encrypt(self, secret: dict[str, object]) -> tuple[str, str, bytes]:
        key_id = _generate_key_id()
        key = _derive_key(self._master_key, key_id)
        nonce = secrets.token_bytes(12)
        plaintext = json.dumps(secret, ensure_ascii=False, default=str).encode()
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
        fingerprint = hashlib.sha256(plaintext).hexdigest()[:16]
        return key_id, fingerprint, nonce + ciphertext

    def decrypt(self, key_id: str, encrypted_blob: bytes) -> dict[str, object]:
        key = _derive_key(self._master_key, key_id)
        nonce, ciphertext = encrypted_blob[:12], encrypted_blob[12:]
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
        return json.loads(plaintext)


class DbCredentialResolver:
    def __init__(self, encryption_service: CredentialEncryptionService | None = None):
        self._encryption = encryption_service or CredentialEncryptionService()

    async def resolve(self, credential_ref: str | None) -> dict[str, object] | None:
        if not credential_ref:
            return None

        from models.sql.integration_credential import IntegrationCredentialModel
        from services.database import async_session_maker

        async with async_session_maker() as session:
            from sqlmodel import select

            result = await session.scalar(
                select(IntegrationCredentialModel).where(
                    IntegrationCredentialModel.id == credential_ref,
                    IntegrationCredentialModel.status == "active",
                )
            )
            if result is None:
                return None

            secret = self._encryption.decrypt(result.key_id, result.encrypted_secret)
            return {
                "type": result.type,
                "module": result.module,
                "label": result.label,
                **secret,
            }

__all__ = ["CredentialEncryptionService", "DbCredentialResolver"]
