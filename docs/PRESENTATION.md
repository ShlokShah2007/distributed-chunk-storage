# Project Presentation: Distributed Chunk Storage & Zero-Knowledge Encryption Engine

> **High-volume data fragmentation, encryption, and reconstruction workflow**  
> **Presented by:** Shlok Shah and Vasu Lakhani  
> **Presentation File:** [`Distributed_Chunk_Storage_Presentation.pptx`](./Distributed_Chunk_Storage_Presentation.pptx)

---

## Slide 1: Title Slide
* **Title:** Distributed Chunk Storage & Zero-Knowledge Encryption Engine
* **Subtitle:** High-volume data fragmentation, encryption, and reconstruction workflow
* **Presenters:** Shlok Shah and Vasu Lakhani

---

## Slide 2: The Core Problem & The Intuition
* **The Problem:**
  * Uploading one massive file (50 GB or 1 TB) over the internet often fails midway because of network drops, timeouts, or strict single-file upload limits.
* **The Intuition:**
  * A large jigsaw puzzle is transported in small pieces and assembled at home. So why not chop huge files into bite-sized, encrypted pieces?

---

## Slide 3: High-Level Workflow: The 4 Stages
Workflow pipeline for an original 100 GB file:
1. **Chunking:** Sliced into 10 MB pieces (`Chunk_001` ... `Chunk_n`).
2. **Client Encryption:** Encrypted with AES-256 before leaving your computer.
3. **Master Manifest:** A recipe table mapping chunks, hashes, and sequence.
4. **Reconstruction:** Download chunks, verify integrity, decrypt, and merge.

---

## Slide 4: Step 1: Chunking (Slicing the Data)
* **Example:** Original file of 50 GB sliced into numbered chunks (e.g., chunks 39 to 48). If chunk 42 fails, only that one piece is re-uploaded.
* **How it works:**
  * A stream reader reads the original file in fixed-size buffers (e.g., 10 MB or 16 MB).
* **Why it matters:**
  * **Fault tolerance:** If chunk #42 fails, re-upload only that 10 MB, not the whole 50 GB.
  * **Parallel uploads:** Send 10+ chunks at once over multiple threads.

---

## Slide 5: Step 2: Encryption & Hashing
* **AES-256 Encryption:**
  * Data is encrypted on the user's laptop before it touches any network or storage server.
  * If the storage server is compromised, attackers see only random, meaningless ciphertext (`0x4F A1 9C ...`).
* **SHA-256 Hashing:**
  * Every chunk gets a unique digital fingerprint (checksum).
  * If a single bit is corrupted during download, the system detects it immediately.
* **Flow:** `Plain Chunk` ➔ `AES-256` ➔ `Ciphertext (0x4F A1...)` ➔ `Storage Server`

---

## Slide 6: Step 3: The Master Manifest
* **What is it?**
  * A lightweight JSON or SQLite database that tracks:
    1. File name and total size
    2. Ordered list of chunk hashes
    3. Storage location of each chunk
* **Example Manifest:**
  | # | SHA-256 Hash | Location |
  |---|---|---|
  | 1 | `a3f9...c1` | `node-A` |
  | 2 | `7be2...90` | `node-B` |
  | 3 | `1d4c...ee` | `node-A` |
* **Analogy:**
  * Chunks are bricks scattered across a warehouse. The manifest is the blueprint to rebuild the building.

---

## Slide 7: Step 4: Retrieval & Reconstruction
1. The client app reads the Manifest.
2. It fetches all chunks in parallel.
3. It validates each chunk's SHA-256 checksum.
4. It decrypts each chunk with the user's private key.
5. It stitches the 10 MB chunks back together.
* **Result:** **100% identical** to the original file.

---

## Slide 8: Reality Check: Why Not GitHub?
* **Scale Issue:** 5 million chunks for 50 TB at 10 MB each — enough to freeze `git push` and `git status`.
* **Built for code, not blobs:** Git keeps full commit history, so a 10 MB file uploaded and then deleted still consumes repository history space. Millions of files crash RAM and freeze Git commands.
* **TOS & Account Termination:** GitHub's automated security systems flag repos uploading non-code binary chunks at scale, which can lead to permanent account termination.

---

## Slide 9: The Upgrade: What to Build Instead
*Alternatives to replace raw Git storage with production-grade architectures:*
1. **MinIO / Ceph (Self-hosted):**
   * Run 2 or 3 cheap local drives or laptops as distributed storage nodes with S3-compatible APIs.
2. **Hybrid Cloud (Multi-target):**
   * Split chunks across free-tier buckets (AWS S3, Cloudflare R2, Google Cloud Storage) with RAID 5-style parity so the file survives if one provider goes down.
3. **IPFS / Web3 (Decentralized):**
   * Push encrypted chunks to IPFS, which is designed natively for decentralized, content-addressed file storage.

---

## Slide 10: Conclusion & Key Learnings
Built a fundamental understanding of:
* 🗄️ **Distributed File Systems:** Principles similar to Google File System (GFS) and AWS S3.
* 🔐 **Cryptographic Security:** AES-256-GCM authenticated encryption paired with SHA-256 integrity verification.
* ⚡ **Concurrent File Streaming:** Multi-threaded streaming, slicing, and reconstruction pipelines.
