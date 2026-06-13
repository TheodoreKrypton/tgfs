"""Unit tests for :mod:`tgfs.crypto.kdf`.

Argon2id is intentionally slow, so we use the minimum-acceptable cost
parameters for the master-key tests. The cipher and HKDF paths are tested
with fixed inputs so they remain deterministic.
"""

from __future__ import annotations

import pytest

from tgfs.crypto.kdf import (
    MASTER_SALT_SIZE,
    derive_file_key,
    derive_master_key,
    fingerprint,
)

# Argon2 parameters tuned for test speed (much lower than the defaults).
_T = 1
_M = 8 * 1024  # 8 MiB
_P = 1


class TestMasterKey:
    def test_deterministic_given_salt(self) -> None:
        salt = b"\xab" * MASTER_SALT_SIZE
        a = derive_master_key(
            "correct horse battery staple",
            salt=salt,
            time_cost=_T,
            memory_cost=_M,
            parallelism=_P,
        )
        b = derive_master_key(
            "correct horse battery staple",
            salt=salt,
            time_cost=_T,
            memory_cost=_M,
            parallelism=_P,
        )
        assert a.key == b.key
        assert a.salt == salt
        assert len(a.key) == 32

    def test_different_passphrase_changes_key(self) -> None:
        salt = b"\x01" * MASTER_SALT_SIZE
        a = derive_master_key(
            "pw-a", salt=salt, time_cost=_T, memory_cost=_M, parallelism=_P
        )
        b = derive_master_key(
            "pw-b", salt=salt, time_cost=_T, memory_cost=_M, parallelism=_P
        )
        assert a.key != b.key

    def test_different_salt_changes_key(self) -> None:
        a = derive_master_key(
            "pw", salt=b"\x01" * MASTER_SALT_SIZE,
            time_cost=_T, memory_cost=_M, parallelism=_P,
        )
        b = derive_master_key(
            "pw", salt=b"\x02" * MASTER_SALT_SIZE,
            time_cost=_T, memory_cost=_M, parallelism=_P,
        )
        assert a.key != b.key

    def test_fresh_salt_is_random(self) -> None:
        a = derive_master_key(
            "pw", time_cost=_T, memory_cost=_M, parallelism=_P
        )
        b = derive_master_key(
            "pw", time_cost=_T, memory_cost=_M, parallelism=_P
        )
        assert a.salt != b.salt

    def test_short_salt_rejected(self) -> None:
        with pytest.raises(ValueError):
            derive_master_key(
                "pw",
                salt=b"\x00" * 4,
                time_cost=_T,
                memory_cost=_M,
                parallelism=_P,
            )

    def test_repr_does_not_leak_key(self) -> None:
        mk = derive_master_key(
            "pw", time_cost=_T, memory_cost=_M, parallelism=_P
        )
        text = repr(mk)
        assert "redacted" in text
        assert mk.key.hex() not in text


class TestFileKey:
    def test_deterministic(self) -> None:
        mk = b"\x07" * 32
        salt = b"\x42" * 32
        a = derive_file_key(mk, salt)
        b = derive_file_key(mk, salt)
        assert a == b
        assert len(a) == 32

    def test_different_salt_changes_file_key(self) -> None:
        mk = b"\x07" * 32
        a = derive_file_key(mk, b"\x01" * 32)
        b = derive_file_key(mk, b"\x02" * 32)
        assert a != b

    def test_different_master_changes_file_key(self) -> None:
        salt = b"\x42" * 32
        a = derive_file_key(b"\x00" * 32, salt)
        b = derive_file_key(b"\xff" * 32, salt)
        assert a != b

    def test_short_master_rejected(self) -> None:
        with pytest.raises(ValueError):
            derive_file_key(b"\x00" * 16, b"\x42" * 32)

    def test_short_salt_rejected(self) -> None:
        with pytest.raises(ValueError):
            derive_file_key(b"\x00" * 32, b"\x42" * 8)


class TestFingerprint:
    def test_stable(self) -> None:
        mk = b"\x07" * 32
        assert fingerprint(mk) == fingerprint(mk)

    def test_short(self) -> None:
        assert len(fingerprint(b"\x07" * 32)) == 8

    def test_changes_with_key(self) -> None:
        assert fingerprint(b"\x00" * 32) != fingerprint(b"\x01" * 32)
