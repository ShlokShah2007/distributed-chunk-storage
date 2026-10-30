# Distributed Chunk Storage & Zero-Knowledge Encryption Engine

> High-volume data fragmentation, client-side encryption, and deterministic reconstruction workflow.

---

## 👥 Contributors & Task Assignment

| Contributor | GitHub Profile | Assigned Tasks |
| :--- | :--- | :--- |
| **Shlok Shah** | [@ShlokShah2007](https://github.com/ShlokShah2007) | • System Architecture & Design<br>• Client-Side AES-256-GCM Encryption & SHA-256 Checksums<br>• Master Manifest Generation & Cataloging |
| **Vasu Lakhani** | [@lakhanivasu97](https://github.com/lakhanivasu97) | • Stream Chunking & File Slicing (10 MB / 16 MB buffers)<br>• Concurrent Network I/O & Failed-Chunk Retry Logic<br>• Parallel Retrieval & Deterministic File Reconstruction |

---

## 📌 Project Overview

Uploading massive files (50 GB to 1 TB+) across public networks is prone to connection drops, transfer timeouts, and strict single-file gateway restrictions. 

This project implements a **zero-knowledge, chunk-based distributed storage pipeline** that:
1. Slices large files into manageable fixed-size blocks (e.g., 10 MB or 16 MB).
2. Encrypts every chunk on the client machine using **AES-256-GCM** prior to network transmission.
3. Generates cryptographic checksums using **SHA-256** for real-time tamper and corruption detection.
4. Generates an index manifest mapping chunks to target storage nodes.
5. Reconstructs files deterministically with parallel downloads and integrity verification.

---

## 🏗️ Architecture & Workflow

```text
[Original Large File]
         │
         ▼
[Stage 1: Stream Chunking] ──────► Slices data into fixed-size chunks (10 MB - 16 MB)
         │
         ▼
[Stage 2: Client-Side Encryption] ─► AES-256-GCM encryption + SHA-256 integrity hash
         │
         ▼
[Stage 3: Master Manifest] ──────► Lightweight catalog storing chunk order and locations
         │
         ▼
[Stage 4: Reconstruction] ───────► Multi-threaded retrieval, checksum verification & merge
```

### 1. Stream Chunking
A stream-based reader slices files without loading the entire payload into RAM. If any single piece fails during transmission, only that chunk is retried rather than the entire file.

### 2. Zero-Knowledge Cryptography
- **AES-256-GCM:** Keys are held exclusively by the client. Even compromised backend nodes store only unintelligible ciphertext.
- **SHA-256 Checksums:** Fingerprint validation guarantees bit-level data integrity.

### 3. Master Manifest
A structured catalog (JSON / SQLite) keeping track of:
- Source file metadata (name, total byte size, MIME type).
- Ordered chunk list with corresponding SHA-256 digests.
- Target storage node endpoints.

### 4. Parallel Retrieval & Assembly
Workers pull chunks concurrently, validate each digest against the manifest, decrypt the payload, and reassemble the original file.

---

## 🌿 Branching Strategy & Individual Scope

To maintain an isolated and clean collaborative workflow, specific project components are assigned to individual branches:

| Branch | Contributor | Assigned Scope |
| :--- | :--- | :--- |
| `main` | Both | Production-ready, stable codebase |
| `shlok` | [@ShlokShah2007](https://github.com/ShlokShah2007) | Architecture, AES-256-GCM Encryption & Master Manifest Engine |
| `vasu` | [@lakhanivasu97](https://github.com/lakhanivasu97) | Stream Chunking, Network I/O & File Reconstruction |

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
