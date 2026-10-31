"""
Unit Tests for Shlok's Modules: core.crypto and core.manifest
Using Python Standard Library unittest (no external test runner required).
"""

import os
import tempfile
import unittest
from core.crypto import CryptoEngine
from core.manifest import ManifestManager, MasterManifest


class TestCryptoEngine(unittest.TestCase):
    def test_key_derivation_deterministic(self):
        """Verify that same passphrase and salt always derive identical 256-bit key."""
        passphrase = "UltraSecureCollegeProjectKey2026!"
        salt = CryptoEngine.generate_salt()

        key1, salt_hex1 = CryptoEngine.derive_key(passphrase, salt)
        key2, salt_hex2 = CryptoEngine.derive_key(passphrase, bytes.fromhex(salt_hex1))

        self.assertEqual(key1, key2)
        self.assertEqual(salt_hex1, salt_hex2)
        self.assertEqual(len(key1), 32)  # 256 bits

    def test_encrypt_decrypt_roundtrip(self):
        """Verify that data encrypts and decrypts back to byte-identical plaintext."""
        passphrase = "mySecretPassword123"
        key, _ = CryptoEngine.derive_key(passphrase)
        
        original_data = b"Hello Vasu, this is a simulated 10MB chunk piece of binary data!" * 1000

        ciphertext, nonce_hex = CryptoEngine.encrypt_chunk(original_data, key)
        self.assertNotEqual(ciphertext, original_data)
        self.assertEqual(len(nonce_hex), 24)

        decrypted_data = CryptoEngine.decrypt_chunk(ciphertext, nonce_hex, key)
        self.assertEqual(decrypted_data, original_data)

    def test_tamper_detection(self):
        """Verify that tampering with 1 bit of ciphertext causes decryption to fail."""
        passphrase = "testPassword"
        key, _ = CryptoEngine.derive_key(passphrase)
        original_data = b"Mission critical financial data"

        ciphertext, nonce_hex = CryptoEngine.encrypt_chunk(original_data, key)

        # Flip 1 byte in the ciphertext
        tampered_bytes = bytearray(ciphertext)
        tampered_bytes[5] ^= 0xFF
        tampered_ciphertext = bytes(tampered_bytes)

        # Decryption MUST raise an exception due to AES-GCM tag mismatch
        with self.assertRaises(Exception):
            CryptoEngine.decrypt_chunk(tampered_ciphertext, nonce_hex, key)

    def test_sha256_checksum(self):
        """Verify SHA-256 fingerprint generation and validation."""
        data = b"Distributed systems chunk test data"
        digest = CryptoEngine.compute_sha256(data)
        self.assertEqual(len(digest), 64)
        self.assertTrue(CryptoEngine.verify_checksum(data, digest))
        self.assertFalse(CryptoEngine.verify_checksum(data + b"extra", digest))


class TestManifestManager(unittest.TestCase):
    def test_manifest_lifecycle(self):
        """Verify manifest creation, chunk addition, validation, save and reload."""
        total_size = 30 * 1024 * 1024  # 30 MB
        chunk_size = 10 * 1024 * 1024  # 10 MB (should produce 3 chunks)

        _, salt_hex = CryptoEngine.derive_key("passphrase")
        manifest = ManifestManager.create("video.mp4", total_size, chunk_size, salt_hex)

        self.assertEqual(manifest.file_metadata.total_chunks, 3)
        self.assertFalse(ManifestManager.validate(manifest))  # Not yet valid, no chunks

        # Add 3 chunks
        for i in range(3):
            fake_chunk = f"chunk_content_{i}".encode("utf-8")
            h = CryptoEngine.compute_sha256(fake_chunk)
            nonce = os.urandom(12).hex()
            ManifestManager.add_chunk(
                manifest=manifest,
                chunk_id=i,
                sha256=h,
                nonce=nonce,
                size_bytes=len(fake_chunk),
                target_node=f"node-{i + 1}"
            )

        self.assertTrue(ManifestManager.validate(manifest))

        # Test JSON save and reload
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = os.path.join(tmpdir, "test_manifest.json")
            ManifestManager.save(manifest, manifest_path)

            loaded_manifest = ManifestManager.load(manifest_path)
            self.assertEqual(loaded_manifest.file_metadata.file_name, "video.mp4")
            self.assertEqual(len(loaded_manifest.chunks), 3)
            self.assertEqual(loaded_manifest.chunks[0].chunk_id, 0)
            self.assertEqual(loaded_manifest.chunks[1].target_node == "node-2", True)


if __name__ == "__main__":
    unittest.main()
