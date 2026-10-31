"""Comprehensive automated unit tests for Dynamic File Chunker.

Covers all 12 scenarios:
1. Empty file
2. File smaller than chunk size
3. File exactly equal to chunk size
4. File slightly larger than chunk size
5. File with an exact multiple of chunk size
6. File with a tiny final chunk
7. Large file
8. Binary file containing arbitrary byte values
9. Invalid input path
10. Invalid chunk size
11. Output directory already exists
12. Dynamic custom output directory and path validation

Verifies for all applicable tests:
- Every chunk is within the maximum size.
- Every chunk has the correct offset and index.
- Total chunk sizes equal original file size.
- Concatenating chunks in index order reproduces the original bytes exactly.
"""

import unittest
import tempfile
import shutil
import json
import os
import sys
from pathlib import Path

# Support direct execution: python file_chunker/tests/test_chunker.py
REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from file_chunker.chunker import (
    split_file,
    reassemble_file,
    validate_input_file,
    validate_chunk_size_mb,
    validate_output_directory,
    ValidationError,
    OutputDirectoryConflictError,
)


class TestDynamicFileChunker(unittest.TestCase):
    """Test suite covering file chunking, validation, error safety, and reconstruction."""

    def setUp(self) -> None:
        """Create an isolated temporary directory for test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="chunker_test_"))
        self.input_dir = self.test_dir / "inputs"
        self.output_dir = self.test_dir / "output"
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        """Clean up temporary test directory."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def _verify_chunk_properties_and_reconstruction(
        self,
        input_file: Path,
        metadata_file: Path,
        original_bytes: bytes,
        configured_max_chunk_size: int,
    ) -> None:
        """Common assertion helper to verify all 4 core chunking invariants."""
        with open(metadata_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        chunks = meta.get("chunks", [])
        total_chunks = meta.get("total_chunks", 0)

        self.assertEqual(len(chunks), total_chunks, "Metadata total_chunks must match chunks list length")
        self.assertEqual(meta["original_filename"], input_file.name)
        self.assertEqual(meta["original_extension"], input_file.suffix)
        self.assertEqual(meta["original_size"], len(original_bytes))
        self.assertEqual(meta["chunk_size"], configured_max_chunk_size)

        # Invariant 1: Total chunk sizes equal original file size
        total_chunk_bytes = sum(c["size"] for c in chunks)
        self.assertEqual(
            total_chunk_bytes,
            len(original_bytes),
            f"Sum of chunk sizes ({total_chunk_bytes}) must equal original size ({len(original_bytes)})",
        )

        expected_offset = 0
        chunks_dir = metadata_file.parent / "chunks"

        for idx, chunk in enumerate(chunks):
            # Invariant 2: Correct index and offset
            self.assertEqual(chunk["index"], idx, f"Chunk index {chunk['index']} does not match expected {idx}")
            self.assertEqual(
                chunk["offset"],
                expected_offset,
                f"Chunk offset {chunk['offset']} does not match expected {expected_offset}",
            )

            # Invariant 3: Every chunk is within the maximum size
            self.assertLessEqual(
                chunk["size"],
                configured_max_chunk_size,
                f"Chunk {chunk['chunk_id']} size ({chunk['size']}) exceeds max size ({configured_max_chunk_size})",
            )

            # Full chunks (all except possibly the last one) must equal configured chunk size
            if idx < total_chunks - 1:
                self.assertEqual(
                    chunk["size"],
                    configured_max_chunk_size,
                    f"Intermediate chunk {chunk['chunk_id']} size ({chunk['size']}) must equal max size",
                )

            # Check that actual physical file on disk matches chunk metadata
            chunk_file_path = chunks_dir / chunk["filename"]
            self.assertTrue(chunk_file_path.exists(), f"Physical chunk file '{chunk_file_path}' does not exist")
            self.assertEqual(chunk_file_path.stat().st_size, chunk["size"])

            expected_offset += chunk["size"]

        # Invariant 4: Concatenating chunks in index order reproduces the original bytes exactly
        reconstructed_file = self.test_dir / f"reconstructed_{input_file.name}"
        reconstructed_bytes_count = reassemble_file(metadata_file, reconstructed_file)
        self.assertEqual(reconstructed_bytes_count, len(original_bytes))

        with open(reconstructed_file, "rb") as rf:
            reconstructed_content = rf.read()
        self.assertEqual(reconstructed_content, original_bytes, "Reconstructed bytes do not match original bytes!")

    # --------------------------------------------------------------------------
    # Test 1: Empty file
    # --------------------------------------------------------------------------
    def test_01_empty_file(self) -> None:
        """Test that an empty input file creates 0 chunks and empty chunks array."""
        empty_file = self.input_dir / "empty.txt"
        empty_file.write_bytes(b"")

        metadata = split_file(
            input_file=empty_file,
            chunk_size_mb=1,
            base_output_dir=self.output_dir,
        )

        metadata_file = self.output_dir / "empty" / "chunk_metadata.json"
        self.assertTrue(metadata_file.exists(), "Metadata file must exist for empty file")

        with open(metadata_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["total_chunks"], 0, "total_chunks must be 0 for empty file")
        self.assertEqual(data["chunks"], [], "chunks must be empty list for empty file")
        self.assertEqual(data["original_size"], 0)

        chunks_dir = self.output_dir / "empty" / "chunks"
        chunk_files = list(chunks_dir.glob("*.bin"))
        self.assertEqual(len(chunk_files), 0, "No .bin chunk files should be created for empty file")

    # --------------------------------------------------------------------------
    # Test 2: File smaller than chunk size
    # --------------------------------------------------------------------------
    def test_02_file_smaller_than_chunk_size(self) -> None:
        """Test file smaller than chunk size creates exactly 1 chunk smaller than max."""
        chunk_size_bytes = 100 * 1024  # 100 KB
        file_size = 45 * 1024  # 45 KB (< 100 KB)
        content = b"S" * file_size

        test_file = self.input_dir / "small.dat"
        test_file.write_bytes(content)

        metadata = split_file(
            input_file=test_file,
            chunk_size_bytes=chunk_size_bytes,
            base_output_dir=self.output_dir,
        )

        metadata_file = self.output_dir / "small" / "chunk_metadata.json"
        self.assertEqual(metadata.total_chunks, 1)
        self.assertEqual(metadata.chunks[0].size, file_size)

        self._verify_chunk_properties_and_reconstruction(
            input_file=test_file,
            metadata_file=metadata_file,
            original_bytes=content,
            configured_max_chunk_size=chunk_size_bytes,
        )

    # --------------------------------------------------------------------------
    # Test 3: File exactly equal to chunk size
    # --------------------------------------------------------------------------
    def test_03_file_exactly_equal_to_chunk_size(self) -> None:
        """Test file whose size is exactly equal to chunk size creates 1 full chunk."""
        chunk_size_mb = 1
        chunk_size_bytes = chunk_size_mb * 1024 * 1024
        content = b"E" * chunk_size_bytes

        test_file = self.input_dir / "exact_one.bin"
        test_file.write_bytes(content)

        metadata = split_file(
            input_file=test_file,
            chunk_size_mb=chunk_size_mb,
            base_output_dir=self.output_dir,
        )

        metadata_file = self.output_dir / "exact_one" / "chunk_metadata.json"
        self.assertEqual(metadata.total_chunks, 1)
        self.assertEqual(metadata.chunks[0].size, chunk_size_bytes)

        self._verify_chunk_properties_and_reconstruction(
            input_file=test_file,
            metadata_file=metadata_file,
            original_bytes=content,
            configured_max_chunk_size=chunk_size_bytes,
        )

    # --------------------------------------------------------------------------
    # Test 4: File slightly larger than chunk size
    # --------------------------------------------------------------------------
    def test_04_file_slightly_larger_than_chunk_size(self) -> None:
        """Test file slightly larger than chunk size (e.g., chunk size + 42 bytes)."""
        chunk_size_bytes = 64 * 1024  # 64 KB
        extra_bytes = 42
        file_size = chunk_size_bytes + extra_bytes
        content = b"A" * chunk_size_bytes + b"B" * extra_bytes

        test_file = self.input_dir / "slightly_larger.dat"
        test_file.write_bytes(content)

        metadata = split_file(
            input_file=test_file,
            chunk_size_bytes=chunk_size_bytes,
            base_output_dir=self.output_dir,
        )

        metadata_file = self.output_dir / "slightly_larger" / "chunk_metadata.json"
        self.assertEqual(metadata.total_chunks, 2)
        self.assertEqual(metadata.chunks[0].size, chunk_size_bytes)
        self.assertEqual(metadata.chunks[1].size, extra_bytes)

        self._verify_chunk_properties_and_reconstruction(
            input_file=test_file,
            metadata_file=metadata_file,
            original_bytes=content,
            configured_max_chunk_size=chunk_size_bytes,
        )

    # --------------------------------------------------------------------------
    # Test 5: File with an exact multiple of chunk size
    # --------------------------------------------------------------------------
    def test_05_file_exact_multiple_of_chunk_size(self) -> None:
        """Test file with size exactly 3 times chunk size creates 3 full chunks."""
        chunk_size_mb = 1
        chunk_size_bytes = chunk_size_mb * 1024 * 1024
        multiplier = 3
        content = b"X" * (chunk_size_bytes * multiplier)

        test_file = self.input_dir / "multiple.dat"
        test_file.write_bytes(content)

        metadata = split_file(
            input_file=test_file,
            chunk_size_mb=chunk_size_mb,
            base_output_dir=self.output_dir,
        )

        metadata_file = self.output_dir / "multiple" / "chunk_metadata.json"
        self.assertEqual(metadata.total_chunks, multiplier)
        for i in range(multiplier):
            self.assertEqual(metadata.chunks[i].size, chunk_size_bytes)

        self._verify_chunk_properties_and_reconstruction(
            input_file=test_file,
            metadata_file=metadata_file,
            original_bytes=content,
            configured_max_chunk_size=chunk_size_bytes,
        )

    # --------------------------------------------------------------------------
    # Test 6: File with a tiny final chunk
    # --------------------------------------------------------------------------
    def test_06_file_with_tiny_final_chunk(self) -> None:
        """Test file whose final chunk is only 1 single byte."""
        chunk_size_bytes = 32 * 1024  # 32 KB
        file_size = (chunk_size_bytes * 2) + 1  # 2 full chunks + 1 byte
        content = os.urandom(file_size)

        test_file = self.input_dir / "tiny_last.bin"
        test_file.write_bytes(content)

        metadata = split_file(
            input_file=test_file,
            chunk_size_bytes=chunk_size_bytes,
            base_output_dir=self.output_dir,
        )

        metadata_file = self.output_dir / "tiny_last" / "chunk_metadata.json"
        self.assertEqual(metadata.total_chunks, 3)
        self.assertEqual(metadata.chunks[0].size, chunk_size_bytes)
        self.assertEqual(metadata.chunks[1].size, chunk_size_bytes)
        self.assertEqual(metadata.chunks[2].size, 1)

        self._verify_chunk_properties_and_reconstruction(
            input_file=test_file,
            metadata_file=metadata_file,
            original_bytes=content,
            configured_max_chunk_size=chunk_size_bytes,
        )

    # --------------------------------------------------------------------------
    # Test 7: Large file
    # --------------------------------------------------------------------------
    def test_07_large_file(self) -> None:
        """Test large multi-megabyte file chunking (e.g., 10 MB with 3 MB chunks)."""
        chunk_size_mb = 3
        chunk_size_bytes = chunk_size_mb * 1024 * 1024
        file_size = 10 * 1024 * 1024  # 10 MB
        # Pattern repeated to verify byte integrity
        pattern = b"0123456789ABCDEF"
        content = (pattern * (file_size // len(pattern))) + pattern[: file_size % len(pattern)]

        test_file = self.input_dir / "large_video.mp4"
        test_file.write_bytes(content)

        metadata = split_file(
            input_file=test_file,
            chunk_size_mb=chunk_size_mb,
            base_output_dir=self.output_dir,
        )

        metadata_file = self.output_dir / "large_video" / "chunk_metadata.json"
        # 10 MB / 3 MB = 3 full chunks (3 MB each) + 1 partial chunk (1 MB)
        self.assertEqual(metadata.total_chunks, 4)
        self.assertEqual(metadata.chunks[0].size, chunk_size_bytes)
        self.assertEqual(metadata.chunks[1].size, chunk_size_bytes)
        self.assertEqual(metadata.chunks[2].size, chunk_size_bytes)
        self.assertEqual(metadata.chunks[3].size, 1 * 1024 * 1024)

        self._verify_chunk_properties_and_reconstruction(
            input_file=test_file,
            metadata_file=metadata_file,
            original_bytes=content,
            configured_max_chunk_size=chunk_size_bytes,
        )

    # --------------------------------------------------------------------------
    # Test 8: Binary file containing arbitrary byte values
    # --------------------------------------------------------------------------
    def test_08_binary_file_arbitrary_bytes(self) -> None:
        """Test binary file containing all 256 possible byte values (0x00 to 0xFF)."""
        all_bytes = bytes(range(256))
        # Repeat 100 times to test 25,600 arbitrary byte combinations
        content = all_bytes * 100
        chunk_size_bytes = 4096  # 4 KB chunk

        test_file = self.input_dir / "arbitrary.bin"
        test_file.write_bytes(content)

        metadata = split_file(
            input_file=test_file,
            chunk_size_bytes=chunk_size_bytes,
            base_output_dir=self.output_dir,
        )

        metadata_file = self.output_dir / "arbitrary" / "chunk_metadata.json"

        self._verify_chunk_properties_and_reconstruction(
            input_file=test_file,
            metadata_file=metadata_file,
            original_bytes=content,
            configured_max_chunk_size=chunk_size_bytes,
        )

    # --------------------------------------------------------------------------
    # Test 9: Invalid input path
    # --------------------------------------------------------------------------
    def test_09_invalid_input_path(self) -> None:
        """Test that invalid paths (non-existent, directory, empty) raise ValidationError."""
        # Non-existent file
        non_existent = self.input_dir / "does_not_exist.bin"
        with self.assertRaises(ValidationError) as ctx:
            validate_input_file(str(non_existent))
        self.assertIn("File not found", str(ctx.exception))

        # Directory path instead of file
        with self.assertRaises(ValidationError) as ctx:
            validate_input_file(str(self.input_dir))
        self.assertIn("directory", str(ctx.exception).lower())

        # Empty string path
        with self.assertRaises(ValidationError) as ctx:
            validate_input_file("   ")
        self.assertIn("cannot be empty", str(ctx.exception).lower())

    # --------------------------------------------------------------------------
    # Test 10: Invalid chunk size
    # --------------------------------------------------------------------------
    def test_10_invalid_chunk_size(self) -> None:
        """Test that non-positive integers, decimals, and non-numeric sizes raise ValidationError."""
        invalid_cases = [0, -1, -100, "0", "-5", "abc", "2.5", ""]
        for case in invalid_cases:
            with self.subTest(case=case):
                with self.assertRaises(ValidationError):
                    validate_chunk_size_mb(case)

        # Valid positive cases should pass
        self.assertEqual(validate_chunk_size_mb(1), 1)
        self.assertEqual(validate_chunk_size_mb("10"), 10)
        self.assertEqual(validate_chunk_size_mb(" 5 "), 5)

    # --------------------------------------------------------------------------
    # Test 11: Output directory already exists
    # --------------------------------------------------------------------------
    def test_11_output_directory_already_exists(self) -> None:
        """Test that attempting to write to an existing output directory raises error unless overwrite is True."""
        test_file = self.input_dir / "collision.dat"
        test_file.write_bytes(b"initial data")

        # First run creates output/collision
        split_file(
            input_file=test_file,
            chunk_size_bytes=1024,
            base_output_dir=self.output_dir,
        )

        target_dir = self.output_dir / "collision"
        self.assertTrue(target_dir.exists())

        # Second run with overwrite=False must raise OutputDirectoryConflictError
        with self.assertRaises(OutputDirectoryConflictError) as ctx:
            split_file(
                input_file=test_file,
                chunk_size_bytes=1024,
                base_output_dir=self.output_dir,
                overwrite=False,
            )
        self.assertIn("already exists", str(ctx.exception))

        # Third run with overwrite=True must succeed safely
        updated_content = b"new replaced data here"
        test_file.write_bytes(updated_content)

        split_file(
            input_file=test_file,
            chunk_size_bytes=1024,
            base_output_dir=self.output_dir,
            overwrite=True,
        )

        metadata_file = target_dir / "chunk_metadata.json"
        self.assertTrue(metadata_file.exists())
        with open(metadata_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual(meta["original_size"], len(updated_content))

    # --------------------------------------------------------------------------
    # Test 12: Dynamic custom output directory and validation
    # --------------------------------------------------------------------------
    def test_12_dynamic_custom_output_directory_and_validation(self) -> None:
        """Test user-specified dynamic output directory resolution, validation, and file chunking."""
        # Test default fallback when input is empty or None
        self.assertEqual(validate_output_directory(None), Path("output").resolve())
        self.assertEqual(validate_output_directory(""), Path("output").resolve())
        self.assertEqual(validate_output_directory("   "), Path("output").resolve())

        # Test valid custom path with whitespace and quotes
        custom_target = self.test_dir / "custom_user_folder"
        resolved = validate_output_directory(f'  "{custom_target}"  ')
        self.assertEqual(resolved, custom_target.resolve())

        # Test error when output directory points to an existing regular file
        sample_file = self.input_dir / "existing_file.txt"
        sample_file.write_text("not a directory")
        with self.assertRaises(ValidationError) as ctx:
            validate_output_directory(str(sample_file))
        self.assertIn("regular file, not a directory", str(ctx.exception))

        # Test chunking directly into the custom dynamic output directory
        data_file = self.input_dir / "dynamic_sample.bin"
        payload = b"Hello, Dynamic World!" * 50
        data_file.write_bytes(payload)

        metadata = split_file(
            input_file=data_file,
            chunk_size_bytes=100,
            base_output_dir=custom_target,
        )

        expected_meta_file = custom_target / "dynamic_sample" / "chunk_metadata.json"
        self.assertTrue(expected_meta_file.exists(), "Chunks must be saved in user-specified dynamic folder")

        self._verify_chunk_properties_and_reconstruction(
            input_file=data_file,
            metadata_file=expected_meta_file,
            original_bytes=payload,
            configured_max_chunk_size=100,
        )


if __name__ == "__main__":
    unittest.main()
