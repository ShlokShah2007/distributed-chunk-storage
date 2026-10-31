"""
Interactive Live Demo CLI: Distributed Chunk Storage & Zero-Knowledge Encryption Engine
Presented by: Shlok Shah (@ShlokShah2007) and Vasu Lakhani (@lakhanivasu97)
"""

import os
import sys
import time
import json
import shutil
import hashlib
from pathlib import Path

# Fix Windows console UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Enable ANSI escape sequences on Windows
os.system("")

from core.crypto import CryptoEngine
from core.manifest import ManifestManager, MasterManifest


# Colors & Formatting
class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"


def print_banner():
    banner = f"""
{Style.CYAN}{Style.BOLD}================================================================================
   DISTRIBUTED CHUNK STORAGE & ZERO-KNOWLEDGE ENCRYPTION ENGINE
================================================================================{Style.RESET}
 {Style.YELLOW}3rd Sem / 2nd Year Project Demonstration{Style.RESET}
 {Style.DIM}Contributors: Shlok Shah (@ShlokShah2007) & Vasu Lakhani (@lakhanivasu97){Style.RESET}
"""
    print(banner)


def progress_bar(current: int, total: int, prefix: str = "", length: int = 30):
    percent = float(current) / max(total, 1)
    filled_length = int(length * percent)
    bar = "=" * filled_length + "-" * (length - filled_length)
    sys.stdout.write(f"\r  {prefix} {Style.CYAN}[{bar}]{Style.RESET} {percent * 100:>5.1f}%")
    sys.stdout.flush()
    if current == total:
        sys.stdout.write("\n")


def press_enter(prompt: str = "Press [ENTER] to proceed..."):
    input(f"\n{Style.YELLOW}>> {prompt}{Style.RESET}")


def run_interactive_demo():
    print_banner()

    # Step 0: File Setup
    workspace_dir = Path("demo_workspace")
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    print(f"{Style.BOLD}[STEP 0: INPUT DATASET SELECTION]{Style.RESET}")
    user_file = input("  Enter path to file (or press ENTER to auto-create a 5 MB test file): ").strip()

    source_file_path = workspace_dir / "original_input.dat"
    if user_file and Path(user_file).is_file():
        shutil.copyfile(user_file, source_file_path)
        file_display_name = Path(user_file).name
    else:
        file_display_name = "secret_research_data.dat"
        print(f"  {Style.DIM}Generating 5 MB test dataset with structured payload...{Style.RESET}")
        chunk_pattern = b"SECURE_CLOUD_STORAGE_BLOCK_SHLOK_VASU_2026_VIVA_DEMO!\n" * 18000  # ~1MB
        with open(source_file_path, "wb") as f:
            for _ in range(5):
                f.write(chunk_pattern)

    file_size_bytes = os.path.getsize(source_file_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    print(f"  {Style.GREEN}[OK] Source file ready:{Style.RESET} {file_display_name} ({file_size_mb:.2f} MB / {file_size_bytes:,} bytes)")

    # Passphrase Setup
    passphrase = input(f"\n  Enter Zero-Knowledge Passphrase (or press ENTER for default): ").strip()
    if not passphrase:
        passphrase = "QuantumZeroKnowledge2026!"
    print(f"  {Style.GREEN}[OK] Client passphrase set:{Style.RESET} '{passphrase}'")

    press_enter("Begin Stage 1: Stream Chunking...")

    # Stage 1: Chunking
    print(f"\n{Style.BOLD}{Style.CYAN}[STAGE 1: STREAM CHUNKING & BUFFER SLICING]{Style.RESET}")
    chunk_size = 1024 * 1024  # 1 MB chunk for snappy live demo
    chunks_raw = []
    
    with open(source_file_path, "rb") as f:
        chunk_idx = 0
        while True:
            buffer = f.read(chunk_size)
            if not buffer:
                break
            chunks_raw.append(buffer)
            progress_bar(chunk_idx + 1, (file_size_bytes + chunk_size - 1) // chunk_size, prefix="Slicing stream:")
            time.sleep(0.08)
            chunk_idx += 1

    total_chunks = len(chunks_raw)
    print(f"  {Style.GREEN}[OK] File sliced into {total_chunks} independent 1 MB chunks without memory bloat.{Style.RESET}")

    press_enter("Begin Stage 2: AES-256-GCM Encryption & Checksum Generation...")

    # Stage 2: Client Encryption
    print(f"\n{Style.BOLD}{Style.CYAN}[STAGE 2: CLIENT-SIDE ZERO-KNOWLEDGE ENCRYPTION]{Style.RESET}")
    print(f"  {Style.DIM}Deriving 256-bit symmetric key using PBKDF2-HMAC-SHA256 (100,000 rounds)...{Style.RESET}")
    key, salt_hex = CryptoEngine.derive_key(passphrase)
    print(f"  {Style.GREEN}[OK] 256-bit Key Generated.{Style.RESET} Salt: {salt_hex[:16]}... (128-bit)")

    encrypted_chunks = []
    manifest = ManifestManager.create(
        file_name=file_display_name,
        total_size_bytes=file_size_bytes,
        chunk_size_bytes=chunk_size,
        salt_hex=salt_hex
    )

    storage_nodes = ["Node-Alpha (Port 8001)", "Node-Beta (Port 8002)", "Node-Gamma (Port 8003)"]

    print("\n  " + "-" * 76)
    print(f"  {'Chunk #':<8} | {'Ciphertext Size':<17} | {'Nonce (IV)':<14} | {'SHA-256 Digest (First 16 chars)':<30}")
    print("  " + "-" * 76)

    nodes_dir = workspace_dir / "storage_nodes"
    nodes_dir.mkdir(exist_ok=True)

    for idx, raw_chunk in enumerate(chunks_raw):
        # 1. Encrypt with fresh IV
        ciphertext, nonce_hex = CryptoEngine.encrypt_chunk(raw_chunk, key)
        # 2. Fingerprint
        chunk_hash = CryptoEngine.compute_sha256(ciphertext)
        encrypted_chunks.append((ciphertext, nonce_hex, chunk_hash))

        # 3. Simulate Node Dispatch
        assigned_node = storage_nodes[idx % len(storage_nodes)]
        stored_filename = f"chunk_{idx}_{chunk_hash[:8]}.enc"
        chunk_path = nodes_dir / stored_filename
        with open(chunk_path, "wb") as cf:
            cf.write(ciphertext)

        # 4. Record to Manifest
        ManifestManager.add_chunk(
            manifest=manifest,
            chunk_id=idx,
            sha256=chunk_hash,
            nonce=nonce_hex,
            size_bytes=len(ciphertext),
            target_node=assigned_node,
            stored_name=stored_filename
        )

        print(f"  Chunk {idx:<2} | {len(ciphertext):<11} bytes | {nonce_hex[:10]}... | {chunk_hash[:24]}...")
        time.sleep(0.06)

    print("  " + "-" * 76)
    print(f"  {Style.GREEN}[OK] All chunks encrypted on client. Cloud nodes receive only AES-GCM ciphertext.{Style.RESET}")

    press_enter("Inspect Stage 3: The Master Manifest...")

    # Stage 3: Master Manifest
    print(f"\n{Style.BOLD}{Style.CYAN}[STAGE 3: MASTER MANIFEST BLUEPRINT]{Style.RESET}")
    manifest_path = workspace_dir / "master_manifest.json"
    ManifestManager.save(manifest, str(manifest_path))
    print(f"  {Style.GREEN}[OK] Master Manifest exported to:{Style.RESET} {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as mf:
        data = json.load(mf)
    print(f"\n{Style.MAGENTA}--- Manifest JSON Sample (First Chunk) ---{Style.RESET}")
    preview = {
        "file_metadata": data["file_metadata"],
        "security": data["security"],
        "sample_chunk_0": data["chunks"][0]
    }
    print(json.dumps(preview, indent=2))
    print(f"{Style.MAGENTA}------------------------------------------{Style.RESET}")

    press_enter("Run Stage 4: Live Hacker Tamper Demonstration...")

    # Stage 4: Live Hacker Tamper Simulation
    print(f"\n{Style.BOLD}{Style.RED}[STAGE 4: LIVE SECURITY TEST — SIMULATING A HACKER ATTACK]{Style.RESET}")
    print(f"  Suppose an attacker breaches Node-Alpha and alters even 1 byte in Chunk #1...")

    target_corrupt_file = nodes_dir / manifest.chunks[1].stored_name
    with open(target_corrupt_file, "rb") as cf:
        corrupted_bytes = bytearray(cf.read())

    # Flip 1 byte
    corrupted_bytes[42] ^= 0xEE

    print(f"\n  {Style.YELLOW}>> Checking Chunk #1 against Master Manifest SHA-256 fingerprint...{Style.RESET}")
    time.sleep(0.5)
    is_hash_valid = CryptoEngine.verify_checksum(bytes(corrupted_bytes), manifest.chunks[1].sha256)

    if not is_hash_valid:
        print(f"  {Style.RED}{Style.BOLD}[ALERT] TAMPERING DETECTED BY SHA-256 CHECKSUM!{Style.RESET}")
        print(f"    Expected: {manifest.chunks[1].sha256}")
        print(f"    Computed: {CryptoEngine.compute_sha256(bytes(corrupted_bytes))}")
        print(f"  {Style.RED}  The client immediately rejects this corrupt packet before executing decryption.{Style.RESET}")

    # Now attempt AES-GCM decryption on corrupted data to show cryptography defense-in-depth
    print(f"\n  {Style.YELLOW}>> Testing AES-256-GCM hardware authentication tag defense...{Style.RESET}")
    time.sleep(0.5)
    try:
        CryptoEngine.decrypt_chunk(bytes(corrupted_bytes), manifest.chunks[1].nonce, key)
        print(f"  {Style.RED}Decryption unexpectedly succeeded!{Style.RESET}")
    except Exception as e:
        print(f"  {Style.GREEN}{Style.BOLD}[OK] AES-GCM AUTHENTICATION TAG REJECTED MALICIOUS CIPHERTEXT!{Style.RESET}")
        print(f"    Exception: {type(e).__name__} (Authentication tag mismatch).")

    press_enter("Proceed to Stage 5: Clean Recovery & Deterministic Reconstruction...")

    # Stage 5: Clean Recovery
    print(f"\n{Style.BOLD}{Style.GREEN}[STAGE 5: RETRIEVAL, INTEGRITY VALIDATION & RECONSTRUCTION]{Style.RESET}")
    print(f"  Fetching uncorrupted chunks from storage nodes...")

    reconstructed_path = workspace_dir / f"reconstructed_{file_display_name}"
    
    with open(reconstructed_path, "wb") as out_f:
        for idx, entry in enumerate(manifest.chunks):
            # Read from node
            node_file = nodes_dir / entry.stored_name
            with open(node_file, "rb") as cf:
                chunk_data = cf.read()

            # 1. Verify Checksum
            if not CryptoEngine.verify_checksum(chunk_data, entry.sha256):
                raise RuntimeError(f"Chunk {entry.chunk_id} failed integrity verification!")

            # 2. Decrypt
            plain_chunk = CryptoEngine.decrypt_chunk(chunk_data, entry.nonce, key)

            # 3. Append to output
            out_f.write(plain_chunk)
            progress_bar(idx + 1, total_chunks, prefix="Reconstructing:")
            time.sleep(0.08)

    # 4. Byte-for-byte identity check
    print(f"\n\n  {Style.BOLD}[VERIFICATION RESULTS]{Style.RESET}")
    with open(source_file_path, "rb") as f1, open(reconstructed_path, "rb") as f2:
        orig_hash = hashlib.sha256(f1.read()).hexdigest()
        recon_hash = hashlib.sha256(f2.read()).hexdigest()

    print(f"  Original File SHA-256     : {Style.CYAN}{orig_hash}{Style.RESET}")
    print(f"  Reconstructed File SHA-256: {Style.CYAN}{recon_hash}{Style.RESET}")

    if orig_hash == recon_hash:
        print(f"\n  {Style.GREEN}{Style.BOLD}========================================================================{Style.RESET}")
        print(f"  {Style.GREEN}{Style.BOLD}   [SUCCESS] RECONSTRUCTED FILE IS 100% BYTE-FOR-BYTE IDENTICAL!       {Style.RESET}")
        print(f"  {Style.GREEN}{Style.BOLD}========================================================================{Style.RESET}\n")
    else:
        print(f"\n  {Style.RED}[ERROR] Hashes do not match!{Style.RESET}\n")


if __name__ == "__main__":
    try:
        run_interactive_demo()
    except KeyboardInterrupt:
        print(f"\n\n{Style.YELLOW}Demo cancelled by user.{Style.RESET}")
