"""
Module: core.crypto
Author: Shlok Shah (@ShlokShah2007)
Purpose: Client-Side Zero-Knowledge Cryptography & Integrity Engine
"""

import os
import hmac
import hashlib
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


class CryptoEngine:
    """
    Zero-Knowledge Cryptographic Engine providing:
    1. Key derivation using PBKDF2-HMAC-SHA256 with cryptographically secure salt.
    2. Symmetric chunk encryption/decryption using AES-256-GCM.
    3. Tamper-evident checksum hashing using SHA-256.
    """

    KEY_LENGTH_BYTES = 32          # 256 bits for AES-256
    SALT_LENGTH_BYTES = 16         # 128-bit salt
    NONCE_LENGTH_BYTES = 12        # 96-bit nonce standard for AES-GCM
    KDF_ITERATIONS = 100_000       # Industry standard derivation work-factor

    @staticmethod
    def generate_salt() -> bytes:
        """Generates a cryptographically secure random salt."""
        return os.urandom(CryptoEngine.SALT_LENGTH_BYTES)

    @staticmethod
    def derive_key(passphrase: str, salt: bytes = None) -> Tuple[bytes, str]:
        """
        Derives a 256-bit AES encryption key from a user passphrase and salt.
        
        Args:
            passphrase: User's secret password/passphrase.
            salt: Optional existing salt (if decrypting). If None, generates new salt.

        Returns:
            Tuple of (derived_key_bytes, salt_hex_string)
        """
        if not passphrase:
            raise ValueError("Passphrase cannot be empty.")

        if salt is None:
            salt = CryptoEngine.generate_salt()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=CryptoEngine.KEY_LENGTH_BYTES,
            salt=salt,
            iterations=CryptoEngine.KDF_ITERATIONS,
        )
        key = kdf.derive(passphrase.encode("utf-8"))
        return key, salt.hex()

    @staticmethod
    def encrypt_chunk(chunk_bytes: bytes, key: bytes) -> Tuple[bytes, str]:
        """
        Encrypts a raw data chunk using AES-256-GCM.
        
        Args:
            chunk_bytes: Plaintext bytes to encrypt (e.g., 10MB chunk).
            key: 256-bit derived symmetric key.

        Returns:
            Tuple of (ciphertext_bytes, nonce_hex)
        """
        if not key or len(key) != CryptoEngine.KEY_LENGTH_BYTES:
            raise ValueError("AES-256 requires a 32-byte key.")

        # AES-GCM requires a fresh, unique nonce for every single chunk
        nonce = os.urandom(CryptoEngine.NONCE_LENGTH_BYTES)
        aesgcm = AESGCM(key)
        
        # In AESGCM, ciphertext includes the 16-byte authentication tag at the end
        ciphertext = aesgcm.encrypt(nonce, chunk_bytes, None)
        return ciphertext, nonce.hex()

    @staticmethod
    def decrypt_chunk(ciphertext: bytes, nonce_hex: str, key: bytes) -> bytes:
        """
        Decrypts an encrypted chunk and authenticates its integrity tag.
        
        Args:
            ciphertext: Encrypted chunk bytes.
            nonce_hex: Hexadecimal string of the 12-byte nonce used during encryption.
            key: 256-bit symmetric key.

        Returns:
            Decrypted plaintext bytes.

        Raises:
            cryptography.exceptions.InvalidTag: If data has been tampered with or key is wrong.
        """
        if not key or len(key) != CryptoEngine.KEY_LENGTH_BYTES:
            raise ValueError("AES-256 requires a 32-byte key.")

        nonce = bytes.fromhex(nonce_hex)
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        """Computes a SHA-256 cryptographic digest (digital fingerprint)."""
        hasher = hashlib.sha256()
        hasher.update(data)
        return hasher.hexdigest()

    @staticmethod
    def verify_checksum(data: bytes, expected_sha256: str) -> bool:
        """
        Verifies if data matches the expected SHA-256 digest in constant time.
        """
        actual_sha256 = CryptoEngine.compute_sha256(data)
        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(actual_sha256.lower(), expected_sha256.lower())
