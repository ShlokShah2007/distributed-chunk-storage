# 🤝 API Contract & Developer Guide for Vasu (@lakhanivasu97)

> **Prepared by Shlok Shah (@ShlokShah2007)**  
> This document provides the complete API specifications, data models, authentication keys, and ready-to-use code examples so you can implement the **Stream Chunker**, **Network Dispatcher**, and **Reconstruction Engine** without friction.

---

## 🔑 1. API Keys & Storage Node Configuration

All storage nodes require authentication via the `X-API-Key` HTTP header.

### Shared Node API Key:
```text
X-API-Key: chunk_sec_key_9f82ab71c94e01d8
```

### Registered Node Endpoints:
| Node ID | Port | Base URL | Storage Directory |
| :--- | :--- | :--- | :--- |
| **Node-1** | `8001` | `http://127.0.0.1:8001` | `storage_data/node-1/` |
| **Node-2** | `8002` | `http://127.0.0.1:8002` | `storage_data/node-2/` |
| **Node-3** | `8003` | `http://127.0.0.1:8003` | `storage_data/node-3/` |

### To Start the 3-Node Cluster:
Run this single command in a terminal:
```bash
python storage_nodes/start_all_nodes.py
```

---

## 📡 2. Storage Node HTTP Endpoints

### A. Upload Chunk (POST)
* **Endpoint:** `POST /upload/<chunk_filename>`
* **Headers:**
  * `X-API-Key: chunk_sec_key_9f82ab71c94e01d8`
  * `Content-Type: application/octet-stream`
* **Body:** Raw encrypted bytes (`ciphertext`)
* **Response (200 OK):**
  ```json
  {
    "status": "success",
    "node_id": "node-1",
    "chunk_name": "chunk_0_bd4e1f0d.enc",
    "bytes_stored": 1048592
  }
  ```
* **Failure (401 Unauthorized):**
  ```json
  {
    "status": "error",
    "message": "Unauthorized. Missing or invalid 'X-API-Key' header."
  }
  ```

### B. Download Chunk (GET)
* **Endpoint:** `GET /download/<chunk_filename>`
* **Headers:**
  * `X-API-Key: chunk_sec_key_9f82ab71c94e01d8`
* **Response (200 OK):** Binary stream of encrypted chunk.
* **Failure (404 Not Found):**
  ```json
  {
    "status": "error",
    "message": "Chunk '...' not found on node-1."
  }
  ```

---

## 🛠️ 3. How to Use Shlok's Modules in Your Code

### A. Deriving the 256-bit Key & Generating a Manifest
```python
from core.crypto import CryptoEngine
from core.manifest import ManifestManager

# 1. Derive key from user password
passphrase = "mySecretPassword123"
key, salt_hex = CryptoEngine.derive_key(passphrase)

# 2. Initialize Master Manifest
manifest = ManifestManager.create(
    file_name="backup.zip",
    total_size_bytes=total_file_size,
    chunk_size_bytes=10 * 1024 * 1024,  # 10 MB
    salt_hex=salt_hex
)
```

### B. Encrypting & Cataloging Each Chunk
```python
# Raw chunk bytes from your chunker
raw_chunk = file_stream.read(10 * 1024 * 1024)

# Encrypt chunk using AES-256-GCM
ciphertext, nonce_hex = CryptoEngine.encrypt_chunk(raw_chunk, key)

# Compute SHA-256 fingerprint for integrity check
chunk_hash = CryptoEngine.compute_sha256(ciphertext)
stored_name = f"chunk_{chunk_id}_{chunk_hash[:8]}.enc"

# Add entry to manifest
ManifestManager.add_chunk(
    manifest=manifest,
    chunk_id=chunk_id,
    sha256=chunk_hash,
    nonce=nonce_hex,
    size_bytes=len(ciphertext),
    target_node="http://127.0.0.1:8001",
    stored_name=stored_name
)
```

### C. Uploading to Storage Node via HTTP (Requests)
```python
import requests
from core.config import STORAGE_API_KEY

headers = {
    "X-API-Key": STORAGE_API_KEY,
    "Content-Type": "application/octet-stream"
}

response = requests.post(
    f"http://127.0.0.1:8001/upload/{stored_name}",
    data=ciphertext,
    headers=headers,
    timeout=10
)

if response.status_code == 200:
    print("Chunk uploaded successfully!")
```

### D. Downloading, Verifying & Decrypting During Reconstruction
```python
# 1. Fetch chunk from node
headers = {"X-API-Key": STORAGE_API_KEY}
res = requests.get(f"{entry.target_node}/download/{entry.stored_name}", headers=headers)
downloaded_bytes = res.content

# 2. Verify SHA-256 fingerprint before touching the data
if not CryptoEngine.verify_checksum(downloaded_bytes, entry.sha256):
    raise ValueError(f"Tamper alert! Chunk {entry.chunk_id} checksum failed!")

# 3. Decrypt with AES-GCM
decrypted_chunk = CryptoEngine.decrypt_chunk(downloaded_bytes, entry.nonce, key)

# 4. Append to your reconstructed file stream
out_file.write(decrypted_chunk)
```

---

## 🎯 4. What Vasu Should Build on Branch `vasu`:
1. **`core/chunker.py`**: Stream generator that yields 10 MB byte chunks without loading the entire file into RAM.
2. **`core/dispatcher.py`**: `ThreadPoolExecutor` worker pool that distributes chunks across `NODE_1_URL`, `NODE_2_URL`, `NODE_3_URL` with retry logic.
3. **`core/assembler.py`**: Reconstructs chunks sequentially back into the original file.
4. **`cli.py`**: User CLI commands: `upload <file>` and `download <manifest.json>`.
