"""Dynamic File Chunker package.

A clean, beginner-friendly library for incrementally splitting files of any type
into binary chunks with structured JSON metadata.
"""

from file_chunker.models import ChunkInfo, ChunkMetadata
from file_chunker.chunker import (
    split_file,
    reassemble_file,
    validate_input_file,
    validate_chunk_size_mb,
    validate_output_directory,
    ChunkerError,
    ValidationError,
    OutputDirectoryConflictError,
    DEFAULT_BUFFER_SIZE,
)

__all__ = [
    "ChunkInfo",
    "ChunkMetadata",
    "split_file",
    "reassemble_file",
    "validate_input_file",
    "validate_chunk_size_mb",
    "validate_output_directory",
    "ChunkerError",
    "ValidationError",
    "OutputDirectoryConflictError",
    "DEFAULT_BUFFER_SIZE",
]
