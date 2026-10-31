"""Core chunking and validation logic for Dynamic File Chunker.

Implements streaming binary chunking with configurable buffer sizes,
thorough path/argument validation, safe directory handling, and cleanup on failure.
"""

from pathlib import Path
from typing import Optional, Callable, Any, Union
import shutil
import os

from file_chunker.models import ChunkInfo, ChunkMetadata

# Default incremental read buffer size: 64 KB (65,536 bytes)
# Reads are kept small to prevent high memory usage, regardless of chunk or file size.
DEFAULT_BUFFER_SIZE = 64 * 1024


class ChunkerError(Exception):
    """Base exception for chunker errors with clear, user-friendly messages."""
    pass


class ValidationError(ChunkerError):
    """Raised when user inputs fail validation rules."""
    pass


class OutputDirectoryConflictError(ChunkerError):
    """Raised when the target output directory already exists and overwrite is not confirmed."""
    pass


def validate_input_file(file_path_str: str) -> Path:
    """Validate that the specified path points to an existing, readable regular file.

    Args:
        file_path_str: Path string provided by the user (quotes and whitespace stripped).

    Returns:
        Path: Resolved, validated pathlib.Path object.

    Raises:
        ValidationError: If the path does not exist, is a directory, or cannot be read.
    """
    clean_path = file_path_str.strip().strip('"').strip("'")
    if not clean_path:
        raise ValidationError("File path cannot be empty.")

    path = Path(clean_path).expanduser().resolve()

    if not path.exists():
        raise ValidationError(f"File not found: '{path}'. Please verify the path.")

    if not path.is_file():
        raise ValidationError(f"The path '{path}' is a directory or special device, not a regular file.")

    # Test read access
    try:
        with open(path, "rb") as test_f:
            test_f.read(1)
    except PermissionError:
        raise ValidationError(f"Permission denied: Unable to read file '{path}'.")
    except OSError as err:
        raise ValidationError(f"Cannot read file '{path}': {err}")

    return path


def validate_chunk_size_mb(chunk_size_input: Any) -> int:
    """Validate that the chunk size is a positive integer.

    Args:
        chunk_size_input: Raw input string or integer representing size in megabytes.

    Returns:
        int: Validated positive integer chunk size in megabytes.

    Raises:
        ValidationError: If chunk size is not a valid positive integer.
    """
    if isinstance(chunk_size_input, str):
        cleaned = chunk_size_input.strip()
        if not cleaned:
            raise ValidationError("Chunk size cannot be empty.")
        try:
            # Check for non-integers (e.g., decimals like '2.5')
            val = int(cleaned)
        except ValueError:
            raise ValidationError(f"Chunk size must be a whole positive integer (got '{cleaned}').")
    elif isinstance(chunk_size_input, int):
        val = chunk_size_input
    else:
        raise ValidationError(f"Invalid chunk size type: {type(chunk_size_input).__name__}.")

    if val <= 0:
        raise ValidationError(f"Chunk size must be strictly greater than 0 MB (got {val}).")

    return val


def validate_output_directory(output_dir_input: Optional[Union[str, Path]] = None) -> Path:
    """Validate user-provided base output directory path.

    Args:
        output_dir_input: Path string or Path object provided by the user.
            If empty, whitespace-only, or None, defaults to 'output'.

    Returns:
        Path: Resolved, validated pathlib.Path object.

    Raises:
        ValidationError: If the specified path points to an existing regular file instead of a directory.
    """
    if output_dir_input is None:
        return Path("output").resolve()

    if isinstance(output_dir_input, Path):
        path = output_dir_input.expanduser().resolve()
    else:
        clean_path = str(output_dir_input).strip().strip('"').strip("'")
        if not clean_path:
            return Path("output").resolve()
        path = Path(clean_path).expanduser().resolve()

    if path.exists() and path.is_file():
        raise ValidationError(f"The path '{path}' is a regular file, not a directory.")

    return path


def split_file(
    input_file: Path,
    chunk_size_mb: Optional[int] = None,
    chunk_size_bytes: Optional[int] = None,
    base_output_dir: Optional[Path] = None,
    buffer_size: int = DEFAULT_BUFFER_SIZE,
    overwrite: bool = False,
    progress_callback: Optional[Callable[[int, int, int], None]] = None,
) -> ChunkMetadata:
    """Splits an input file into binary chunks using an incremental memory buffer.

    Creates the required directory structure:
        <base_output_dir>/
            <file_stem>/
                chunks/
                    chunk_000000.bin
                    chunk_000001.bin
                    ...
                chunk_metadata.json

    Args:
        input_file: Path to the validated source file.
        chunk_size_mb: Maximum chunk size in megabytes (positive integer).
        chunk_size_bytes: Optional direct chunk size in bytes (used in tests or programmatic calls).
        base_output_dir: Base directory where output will be stored (defaults to 'output').
        buffer_size: Internal read buffer in bytes (defaults to 64 KB). Must be <= chunk_size_bytes.
        overwrite: If True, safely replaces an existing output directory.
        progress_callback: Optional callback func(chunk_index, bytes_processed, total_bytes).

    Returns:
        ChunkMetadata: Fully populated metadata object.

    Raises:
        ValidationError: If neither valid chunk_size_mb nor chunk_size_bytes is provided.
        OutputDirectoryConflictError: If output directory exists and overwrite is False.
        ChunkerError: If an I/O error occurs during chunking.
    """
    if chunk_size_bytes is None:
        if chunk_size_mb is None:
            raise ValidationError("Either chunk_size_mb or chunk_size_bytes must be specified.")
        validated_mb = validate_chunk_size_mb(chunk_size_mb)
        chunk_size_bytes = validated_mb * 1024 * 1024
    else:
        if not isinstance(chunk_size_bytes, int) or chunk_size_bytes <= 0:
            raise ValidationError(f"chunk_size_bytes must be a positive integer (got {chunk_size_bytes}).")

    base_output_dir = validate_output_directory(base_output_dir)

    # Target folder: <base_output_dir>/<filename_stem>
    target_dir = (base_output_dir / input_file.stem).resolve()
    chunks_dir = target_dir / "chunks"
    metadata_path = target_dir / "chunk_metadata.json"

    # Directory collision check
    if target_dir.exists():
        if not overwrite:
            raise OutputDirectoryConflictError(
                f"Output directory already exists: '{target_dir}'. "
                "Specify a different location or enable safe overwrite."
            )
        # Safe replacement: remove existing content
        try:
            shutil.rmtree(target_dir)
        except OSError as e:
            raise ChunkerError(f"Failed to clear existing directory '{target_dir}': {e}")

    # Create directory structure
    target_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)

    original_size = input_file.stat().st_size
    actual_buffer_size = min(buffer_size, chunk_size_bytes)

    metadata = ChunkMetadata(
        original_filename=input_file.name,
        original_extension=input_file.suffix,
        original_size=original_size,
        chunk_size=chunk_size_bytes,
        total_chunks=0,
        chunks=[],
    )

    # Special case: Empty input file
    # Requirement: Handle empty input file without creating an unnecessary data chunk.
    # total_chunks must be 0, chunks must be an empty array.
    if original_size == 0:
        metadata.save_json(metadata_path)
        return metadata

    chunk_index = 0
    current_offset = 0

    try:
        with open(input_file, "rb") as src_f:
            while current_offset < original_size:
                chunk_id = f"chunk_{chunk_index:06d}"
                chunk_filename = f"{chunk_id}.bin"
                chunk_filepath = chunks_dir / chunk_filename

                chunk_bytes_written = 0

                with open(chunk_filepath, "wb") as chunk_f:
                    # Accumulate data up to configured maximum chunk size
                    while chunk_bytes_written < chunk_size_bytes:
                        bytes_needed = chunk_size_bytes - chunk_bytes_written
                        read_len = min(actual_buffer_size, bytes_needed)
                        buffer = src_f.read(read_len)

                        if not buffer:
                            # Reached end of file
                            break

                        chunk_f.write(buffer)
                        chunk_bytes_written += len(buffer)

                # Append chunk info to metadata
                metadata.chunks.append(
                    ChunkInfo(
                        chunk_id=chunk_id,
                        filename=chunk_filename,
                        index=chunk_index,
                        offset=current_offset,
                        size=chunk_bytes_written,
                    )
                )

                current_offset += chunk_bytes_written
                chunk_index += 1

                if progress_callback:
                    progress_callback(chunk_index, current_offset, original_size)

        metadata.total_chunks = len(metadata.chunks)
        metadata.save_json(metadata_path)
        return metadata

    except Exception as exc:
        # Failure safety: do not leave partial/broken outputs presented as successful
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
        raise ChunkerError(f"Error during chunking of '{input_file}': {exc}") from exc


def reassemble_file(metadata_path: Path, destination_path: Path) -> int:
    """Helper function to reconstruct the original file from chunks and metadata.

    Reads chunks sequentially by index order and writes them to destination_path.
    Used for verifying integrity and correctness in testing.

    Args:
        metadata_path: Path to chunk_metadata.json.
        destination_path: Destination path for the reconstructed file.

    Returns:
        int: Total number of bytes written.
    """
    import json

    with open(metadata_path, "r", encoding="utf-8") as f:
        meta_dict = json.load(f)

    chunks_dir = metadata_path.parent / "chunks"
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    bytes_written = 0
    # Chunks sorted strictly by index
    sorted_chunks = sorted(meta_dict.get("chunks", []), key=lambda c: c["index"])

    with open(destination_path, "wb") as dest_f:
        for chunk in sorted_chunks:
            chunk_file = chunks_dir / chunk["filename"]
            with open(chunk_file, "rb") as cf:
                data = cf.read()
                dest_f.write(data)
                bytes_written += len(data)

    return bytes_written
