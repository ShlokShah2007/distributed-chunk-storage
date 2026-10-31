# Dynamic File Chunker

A clean, robust, beginner-friendly Python application that splits any user-selected file into smaller binary `.bin` chunks with structured JSON metadata.

---

## Features

- **Any File Format Supported:** Works with video (`.mp4`), audio (`.mp3`), images (`.jpg`, `.png`), documents (`.pdf`, `.docx`), archives (`.zip`), text (`.txt`), and arbitrary raw binary data.
- **Zero External Dependencies:** Built strictly using the Python Standard Library (`pathlib`, `json`, `shutil`, `sys`, `dataclasses`, `unittest`).
- **Memory Efficient Streaming:** Incremental streaming with a configurable buffer (default 64 KB). The entire file is never loaded into memory.
- **Safe Directory Operations:** Does not silently overwrite existing output directories. Offers interactive replacement or custom folder paths.
- **Atomic Cleanup on Failure:** If an error occurs during chunking, incomplete outputs are removed automatically to avoid corrupt state.
- **Structured JSON Metadata:** Exports `chunk_metadata.json` containing original file details, offsets, chunk indices, and individual chunk file sizes.
- **Empty File Handling:** Appropriately sets `total_chunks: 0` and `chunks: []` without creating unnecessary binary data files.
- **Cross-Platform & Windows-Ready:** Handles Windows path quoting, spaces in paths, backslashes/forward slashes, and permission exceptions.

---

## Project Structure

```text
file_chunker/
│
├── __init__.py           # Package exports and module definitions
├── main.py               # Interactive CLI interface and user prompts
├── chunker.py            # Core streaming chunking and input validation logic
├── models.py             # Data models for ChunkInfo and ChunkMetadata
├── README.md             # Documentation, design notes, and usage guide
│
└── tests/
    ├── __init__.py
    └── test_chunker.py   # Comprehensive 12-scenario automated test suite
```

---

## Architecture & Code Explanation

### 1. `models.py`
Contains clean, strongly typed dataclasses representing chunks and overall metadata:
- **`ChunkInfo`**: Represents a single chunk file on disk. Holds `chunk_id` (`chunk_000000`), `filename` (`chunk_000000.bin`), zero-based `index`, starting byte `offset`, and byte `size`.
- **`ChunkMetadata`**: Holds `original_filename`, `original_extension`, `original_size`, `chunk_size`, `total_chunks`, and a list of `ChunkInfo` items. Provides `.to_dict()` and `.save_json()` methods.

### 2. `chunker.py`
Contains the core engine and validation helpers:
- **`validate_input_file(path_str)`**: Validates that the input path exists, is a regular file (not a folder or special device), and has active read permissions. Strips surrounding quotes often added when copying paths or dragging and dropping files in Windows.
- **`validate_chunk_size_mb(size_input)`**: Ensures the chunk size is a positive integer strictly greater than 0 MB.
- **`validate_output_directory(path_input)`**: Validates user-provided output directory, handles quote stripping and whitespace, and ensures target is not an existing file. Defaults to `output` if left blank.
- **`split_file(...)`**: Opens the target file in binary read mode (`rb`). Iterates through the file using a configurable read buffer (default 64 KB). Chunks are accumulated up to the exact configured chunk size in bytes, written sequentially into the `<destination>/<stem>/chunks/` directory, and saved alongside `chunk_metadata.json`. If an error occurs mid-operation, any partially created files are safely cleaned up.
- **`reassemble_file(metadata_path, destination_path)`**: Reconstructs the original file from chunks in index order. Used to guarantee 100% byte-for-byte fidelity in tests.

### 3. `main.py`
Interactive user CLI:
- Displays application banner.
- Prompts for complete file path (supports spaces and quotes).
- Prompts for maximum chunk size in MB.
- Prompts for dynamic destination directory (or press Enter to use default `output`).
- Checks if target output directory already exists. If so, gives the user options to:
  1. Safely replace the existing output directory.
  2. Choose an alternate output directory.
  3. Cancel cleanly.
- Displays real-time chunk progress and summary statistics.

---

## Output Structure

For an input file named `video.mp4` with 10 MB chunk size:

```text
output/
└── video/
    ├── chunks/
    │   ├── chunk_000000.bin
    │   ├── chunk_000001.bin
    │   └── chunk_000002.bin
    └── chunk_metadata.json
```

### Metadata Format (`chunk_metadata.json`)

```json
{
    "original_filename": "video.mp4",
    "original_extension": ".mp4",
    "original_size": 26214400,
    "chunk_size": 10485760,
    "total_chunks": 3,
    "chunks": [
        {
            "chunk_id": "chunk_000000",
            "filename": "chunk_000000.bin",
            "index": 0,
            "offset": 0,
            "size": 10485760
        },
        {
            "chunk_id": "chunk_000001",
            "filename": "chunk_000001.bin",
            "index": 1,
            "offset": 10485760,
            "size": 10485760
        },
        {
            "chunk_id": "chunk_000002",
            "filename": "chunk_000002.bin",
            "index": 2,
            "offset": 20971520,
            "size": 5242880
        }
    ]
}
```

*Note: For empty files (`0 bytes`), `total_chunks` is `0`, `chunks` is `[]`, and no `.bin` files are created in the `chunks/` folder.*

---

## How to Run

### Interactive Mode

Run the program using Python:

```bash
python file_chunker/main.py
```
or
```bash
python -m file_chunker.main
```

You will see:

```text
==================================================
DYNAMIC FILE CHUNKER
==================================================

Enter the complete path of the file: C:\path to my file\document.pdf
Enter maximum chunk size in MB: 2
```

---

## Running Automated Tests

Run the full automated test suite using Python's built-in `unittest` runner:

```bash
python -m unittest discover -s file_chunker/tests -v
```
or run directly:
```bash
python file_chunker/tests/test_chunker.py
```

### Verified Test Cases:
1. **Empty file:** Ensures 0 chunks and empty JSON array.
2. **File smaller than chunk size:** 1 partial chunk created.
3. **File exactly equal to chunk size:** 1 full chunk of exact size created.
4. **File slightly larger than chunk size:** 2 chunks created (1 full + small remainder).
5. **File with an exact multiple of chunk size:** Multiple full chunks created with zero remainder.
6. **File with a tiny final chunk:** Last chunk verified down to a single byte.
7. **Large file:** Multi-megabyte file chunking with buffer cycling.
8. **Binary file containing arbitrary byte values:** Full 0x00–0xFF byte space integrity verification.
9. **Invalid input path:** Verifies friendly error on missing files, directories, or blank paths.
10. **Invalid chunk size:** Verifies friendly error on 0, negative, decimal, or string sizes.
11. **Output directory collision:** Verifies safe conflict prevention and replacement.
