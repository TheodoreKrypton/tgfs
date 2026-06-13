"""Bootstrap helpers that wire :mod:`tgfs.crypto` into the runtime config.

This module is intentionally tiny -- it lives outside the ``crypto`` package
so that pulling it in does not force everyone to take the Argon2 / OpenSSL
dependencies at import time.
"""

from __future__ import annotations

import logging
import os
import secrets

from tgfs.config import EncryptionConfig
from tgfs.crypto.kdf import MASTER_SALT_SIZE, MasterKey, derive_master_key, fingerprint

logger = logging.getLogger(__name__)


def _load_or_create_master_salt(path: str) -> bytes:
    """Load the master salt from ``path`` or create it on first run.

    The salt is *not* secret. We persist it with mode 0600 anyway, just to
    keep it neatly grouped with other TGFS state.
    """
    if os.path.exists(path):
        with open(path, "rb") as fh:
            salt = fh.read()
        if len(salt) < 8:
            raise ValueError(
                f"master salt file '{path}' is too short ({len(salt)} bytes)"
            )
        return salt

    logger.info("Generating fresh master salt at %s", path)
    salt = secrets.token_bytes(MASTER_SALT_SIZE)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    # Write then chmod (rather than open with mode) so we work on systems
    # whose umask is stricter than 0600.
    with open(path, "wb") as fh:
        fh.write(salt)
    try:
        os.chmod(path, 0o600)
    except OSError as exc:  # pragma: no cover -- best effort
        logger.warning("Could not chmod %s: %s", path, exc)
    return salt


def load_master_key(cfg: EncryptionConfig) -> MasterKey:
    """Resolve the passphrase, load/persist the salt, derive the master key.

    Logs a short fingerprint (not the key) so operators can confirm at a
    glance that the same key is being used after a restart.
    """
    passphrase = cfg.resolve_passphrase()
    salt = _load_or_create_master_salt(cfg.master_salt_file)
    master = derive_master_key(passphrase, salt=salt)
    logger.info(
        "Master key ready (fingerprint=%s, salt=%s)",
        fingerprint(master.key),
        cfg.master_salt_file,
    )
    return master
