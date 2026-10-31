"""
Module: core.manifest
Author: Shlok Shah (@ShlokShah2007)
Purpose: Master Manifest Cataloging, Schema Validation & Serialization Engine
"""

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class ChunkEntry:
    """Represents metadata for a single fragmented and encrypted chunk."""
    chunk_id: int
    sha256: str
    nonce: str
    size_bytes: int
    target_node: str
    stored_name: str


@dataclass
class FileMetadata:
    """Source file attributes."""
    file_name: str
    total_size_bytes: int
    chunk_size_bytes: int
    total_chunks: int
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SecurityConfig:
    """Cryptographic configuration parameters."""
    cipher: str = "AES-256-GCM"
    kdf: str = "PBKDF2-HMAC-SHA256"
    salt: str = ""


@dataclass
class MasterManifest:
    """The master blueprint required to locate, authenticate, and reconstruct a file."""
    file_metadata: FileMetadata
    security: SecurityConfig
    chunks: List[ChunkEntry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the manifest instance to a serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MasterManifest":
        """Constructs a MasterManifest instance from a dictionary."""
        file_meta = FileMetadata(**data["file_metadata"])
        security = SecurityConfig(**data["security"])
        chunks = [ChunkEntry(**chunk) for chunk in data.get("chunks", [])]
        return cls(file_metadata=file_meta, security=security, chunks=chunks)


class ManifestManager:
    """
    Manages manifest lifecycle: creation, chunk cataloging, disk persistence, and validation.
    """

    @staticmethod
    def create(
        file_name: str,
        total_size_bytes: int,
        chunk_size_bytes: int,
        salt_hex: str
    ) -> MasterManifest:
        """
        Creates a new, initialized MasterManifest.
        """
        if total_size_bytes <= 0:
            raise ValueError("Total size must be greater than 0.")
        if chunk_size_bytes <= 0:
            raise ValueError("Chunk size must be greater than 0.")

        total_chunks = (total_size_bytes + chunk_size_bytes - 1) // chunk_size_bytes

        meta = FileMetadata(
            file_name=file_name,
            total_size_bytes=total_size_bytes,
            chunk_size_bytes=chunk_size_bytes,
            total_chunks=total_chunks
        )
        sec = SecurityConfig(salt=salt_hex)
        return MasterManifest(file_metadata=meta, security=sec, chunks=[])

    @staticmethod
    def add_chunk(
        manifest: MasterManifest,
        chunk_id: int,
        sha256: str,
        nonce: str,
        size_bytes: int,
        target_node: str,
        stored_name: Optional[str] = None
    ) -> None:
        """
        Adds a validated chunk record to the manifest.
        """
        if stored_name is None:
            stored_name = f"{sha256[:16]}_{chunk_id}.enc"

        entry = ChunkEntry(
            chunk_id=chunk_id,
            sha256=sha256,
            nonce=nonce,
            size_bytes=size_bytes,
            target_node=target_node,
            stored_name=stored_name
        )
        manifest.chunks.append(entry)

    @staticmethod
    def validate(manifest: MasterManifest) -> bool:
        """
        Validates completeness and integrity of the manifest.
        - Ensures total_chunks matches chunk array length.
        - Checks that chunk_ids are strictly 0, 1, ..., N-1 without missing gaps.
        - Verifies non-empty hashes and nonces.
        """
        expected_count = manifest.file_metadata.total_chunks
        if len(manifest.chunks) != expected_count:
            return False

        # Sort by chunk_id to verify sequence
        sorted_chunks = sorted(manifest.chunks, key=lambda c: c.chunk_id)
        for expected_id, chunk in enumerate(sorted_chunks):
            if chunk.chunk_id != expected_id:
                return False
            if not chunk.sha256 or len(chunk.sha256) != 64:
                return False
            if not chunk.nonce or len(chunk.nonce) != 24:  # 12 bytes = 24 hex characters
                return False
            if chunk.size_bytes <= 0:
                return False

        return True

    @staticmethod
    def save(manifest: MasterManifest, destination_path: str) -> None:
        """Saves manifest to a formatted JSON file."""
        path = Path(destination_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)

    @staticmethod
    def load(source_path: str) -> MasterManifest:
        """Loads and parses a manifest from a JSON file."""
        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"Manifest file not found: {source_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        manifest = MasterManifest.from_dict(data)
        if not ManifestManager.validate(manifest):
            raise ValueError("Manifest validation failed: Corrupted or incomplete chunk records.")
        return manifest
