"""
Demo: Zero-Knowledge Encryption & Master Manifest Engine
Author: Shlok Shah (@ShlokShah2007)
"""

from core.crypto import CryptoEngine
from core.manifest import ManifestManager


def run_demo():
    print("=" * 60)
    print("  Zero-Knowledge Encryption & Manifest Demo — Shlok Shah")
    print("=" * 60)

    # 1. User Passphrase & Key Derivation
    passphrase = "MySecretCloudPassphrase2026!"
    print(f"\n[1] Deriving 256-bit AES key from passphrase: '{passphrase}'...")
    key, salt_hex = CryptoEngine.derive_key(passphrase)
    print(f"    - Generated Salt (Hex) : {salt_hex}")
    print(f"    - Derived Key Length   : {len(key) * 8} bits")

    # 2. Simulate File Slicing & Chunk Encryption
    file_name = "college_project_video.mp4"
    simulated_chunk = b"Dummy video data chunk bytes for testing... " * 500
    print(f"\n[2] Encrypting simulated chunk ({len(simulated_chunk)} bytes)...")
    
    ciphertext, nonce_hex = CryptoEngine.encrypt_chunk(simulated_chunk, key)
    chunk_hash = CryptoEngine.compute_sha256(ciphertext)
    print(f"    - Nonce (IV Hex)       : {nonce_hex}")
    print(f"    - Ciphertext Size      : {len(ciphertext)} bytes (includes 16-byte GCM tag)")
    print(f"    - SHA-256 Checksum     : {chunk_hash}")

    # 3. Create Master Manifest
    print("\n[3] Cataloging chunk into Master Manifest...")
    manifest = ManifestManager.create(
        file_name=file_name,
        total_size_bytes=len(simulated_chunk),
        chunk_size_bytes=len(simulated_chunk),
        salt_hex=salt_hex
    )
    ManifestManager.add_chunk(
        manifest=manifest,
        chunk_id=0,
        sha256=chunk_hash,
        nonce=nonce_hex,
        size_bytes=len(ciphertext),
        target_node="storage-node-alpha"
    )

    manifest_file = "demo_manifest.json"
    ManifestManager.save(manifest, manifest_file)
    print(f"    - Saved manifest to '{manifest_file}' (Valid: {ManifestManager.validate(manifest)})")

    # 4. Decrypt & Verify
    print("\n[4] Simulating retrieval, integrity check, and decryption...")
    loaded_manifest = ManifestManager.load(manifest_file)
    entry = loaded_manifest.chunks[0]

    # Verify SHA-256
    is_intact = CryptoEngine.verify_checksum(ciphertext, entry.sha256)
    print(f"    - Integrity Verification: {'PASSED (Data intact)' if is_intact else 'FAILED'}")

    # Decrypt
    decrypted_bytes = CryptoEngine.decrypt_chunk(ciphertext, entry.nonce, key)
    matches = (decrypted_bytes == simulated_chunk)
    print(f"    - Decryption Match      : {'100% IDENTICAL TO ORIGINAL' if matches else 'FAILED'}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_demo()
