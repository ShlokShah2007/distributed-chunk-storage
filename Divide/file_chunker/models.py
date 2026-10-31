"""Data models for Dynamic File Chunker.

Defines structured data representations for chunk details and overall chunk metadata.
Designed to be lightweight, standard-library only, and easily serialized to JSON.
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any
import json


@dataclass
class ChunkInfo:
    """Represents metadata for an individual file chunk.

    Attributes:
        chunk_id: Unique identifier for the chunk, formatted as 'chunk_XXXXXX'.
        filename: Name of the binary chunk file on disk (e.g., 'chunk_000000.bin').
        index: Zero-based sequential index of the chunk.
        offset: Starting byte position of this chunk within the original file.
        size: Size of this chunk in bytes.
    """
    chunk_id: str
    filename: str
    index: int
    offset: int
    size: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk information into a dictionary representation."""
        return {
            "chunk_id": self.chunk_id,
            "filename": self.filename,
            "index": self.index,
            "offset": self.offset,
            "size": self.size,
        }


@dataclass
class ChunkMetadata:
    """Represents overall metadata for the chunked file and all its parts.

    Attributes:
        original_filename: Complete name of the original input file (e.g., 'video.mp4').
        original_extension: File extension including leading dot (e.g., '.mp4').
        original_size: Total size of the original input file in bytes.
        chunk_size: Configured maximum chunk size in bytes.
        total_chunks: Number of chunks generated (0 for empty files).
        chunks: List of ChunkInfo objects representing each generated chunk.
    """
    original_filename: str
    original_extension: str
    original_size: int
    chunk_size: int
    total_chunks: int = 0
    chunks: List[ChunkInfo] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert overall metadata into a dictionary conforming to project specification."""
        return {
            "original_filename": self.original_filename,
            "original_extension": self.original_extension,
            "original_size": self.original_size,
            "chunk_size": self.chunk_size,
            "total_chunks": self.total_chunks,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }

    def save_json(self, output_file: Path) -> None:
        """Serialize metadata to a formatted JSON file.

        Args:
            output_file: Path to destination JSON file (e.g., chunk_metadata.json).
        """
        data = self.to_dict()
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
