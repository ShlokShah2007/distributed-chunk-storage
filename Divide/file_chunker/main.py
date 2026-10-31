"""Command-Line Interface for Dynamic File Chunker.

Prompts user for file path and chunk size, validates inputs,
handles directory collisions interactively, and executes safe streaming chunking.
"""

from pathlib import Path
import sys

# Support direct script execution: python file_chunker/main.py
PARENT_DIR = str(Path(__file__).resolve().parent.parent)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from file_chunker.chunker import (
    split_file,
    validate_input_file,
    validate_chunk_size_mb,
    validate_output_directory,
    ValidationError,
    OutputDirectoryConflictError,
    ChunkerError,
)


def format_bytes(byte_count: int) -> str:
    """Format byte counts into human-readable strings."""
    if byte_count < 1024:
        return f"{byte_count} B"
    elif byte_count < 1024 * 1024:
        return f"{byte_count / 1024:.2f} KB ({byte_count:,} bytes)"
    elif byte_count < 1024 * 1024 * 1024:
        return f"{byte_count / (1024 * 1024):.2f} MB ({byte_count:,} bytes)"
    else:
        return f"{byte_count / (1024 * 1024 * 1024):.2f} GB ({byte_count:,} bytes)"


def prompt_file_path() -> Path:
    """Prompt the user for the file path with validation and friendly retry."""
    while True:
        try:
            raw_input = input("Enter the complete path of the file: ")
            if raw_input.strip().lower() in ("q", "quit", "exit"):
                print("Operation cancelled by user.")
                sys.exit(0)
            valid_path = validate_input_file(raw_input)
            return valid_path
        except ValidationError as err:
            print(f"[Error] {err}")
            print("Please try again, or enter 'q' to quit.\n")


def prompt_chunk_size() -> int:
    """Prompt the user for chunk size in MB with validation and friendly retry."""
    while True:
        try:
            raw_input = input("Enter maximum chunk size in MB: ")
            if raw_input.strip().lower() in ("q", "quit", "exit"):
                print("Operation cancelled by user.")
                sys.exit(0)
            valid_size = validate_chunk_size_mb(raw_input)
            return valid_size
        except ValidationError as err:
            print(f"[Error] {err}")
            print("Please try again, or enter 'q' to quit.\n")


def prompt_output_directory(default_dir: str = "output") -> Path:
    """Prompt the user for output destination directory with validation and default fallback."""
    while True:
        try:
            raw_input = input(f"Enter destination directory path [press Enter for '{default_dir}']: ")
            if raw_input.strip().lower() in ("q", "quit", "exit"):
                print("Operation cancelled by user.")
                sys.exit(0)
            return validate_output_directory(raw_input)
        except ValidationError as err:
            print(f"[Error] {err}")
            print("Please try again, or enter 'q' to quit.\n")


def resolve_output_directory(input_file: Path, base_dir: Path) -> tuple[Path, bool]:
    """Check if the default output directory exists and ask user for confirmation/strategy.

    Returns:
        tuple[Path, bool]: (resolved_base_dir, overwrite_flag)
    """
    target_dir = base_dir / input_file.stem
    if not target_dir.exists():
        return base_dir, False

    print(f"\n[Notice] The output directory already exists:")
    print(f"         '{target_dir}'")
    print("Please choose a replacement strategy:")
    print("  [1] Safely replace/overwrite existing output directory")
    print("  [2] Specify an alternate base output directory")
    print("  [3] Cancel operation")

    while True:
        choice = input("Enter your choice (1/2/3): ").strip()
        if choice == "1":
            return base_dir, True
        elif choice == "2":
            alt_path_str = input("Enter new output folder path: ").strip().strip('"').strip("'")
            if not alt_path_str:
                print("Path cannot be empty. Please try again.")
                continue
            alt_base = Path(alt_path_str).resolve()
            # Recursively check if target still exists in new base
            return resolve_output_directory(input_file, alt_base)
        elif choice in ("3", "q", "quit", "exit"):
            print("Operation cancelled by user.")
            sys.exit(0)
        else:
            print("Invalid selection. Please choose 1, 2, or 3.")


def print_progress(chunk_index: int, bytes_processed: int, total_bytes: int) -> None:
    """Callback function to display chunking progress in the terminal."""
    percent = (bytes_processed / total_bytes * 100) if total_bytes > 0 else 100.0
    print(f" -> Generated chunk #{chunk_index:04d} | Processed: {bytes_processed:,}/{total_bytes:,} bytes ({percent:.1f}%)")


def run() -> None:
    """Main CLI execution routine."""
    print("=" * 50)
    print("DYNAMIC FILE CHUNKER")
    print("=" * 50)
    print()

    try:
        # Step 1: User interaction & validation
        input_file = prompt_file_path()
        chunk_size_mb = prompt_chunk_size()
        base_dir_input = prompt_output_directory()

        # Step 2: Handle directory collision safely
        base_output_dir, overwrite = resolve_output_directory(input_file, base_dir_input)

        print("\nStarting chunking process...")
        print(f"  Source File : {input_file}")
        print(f"  File Size   : {format_bytes(input_file.stat().st_size)}")
        print(f"  Chunk Size  : {chunk_size_mb} MB ({chunk_size_mb * 1024 * 1024:,} bytes)")
        print(f"  Destination : {base_output_dir / input_file.stem}\n")

        # Step 3: Execute chunking
        metadata = split_file(
            input_file=input_file,
            chunk_size_mb=chunk_size_mb,
            base_output_dir=base_output_dir,
            overwrite=overwrite,
            progress_callback=print_progress,
        )

        # Step 4: Summary presentation
        print("\n" + "=" * 50)
        print("CHUNKING COMPLETED SUCCESSFULLY")
        print("=" * 50)
        print(f"Original File     : {metadata.original_filename}")
        print(f"Original Size     : {format_bytes(metadata.original_size)}")
        print(f"Chunk Size Config : {metadata.chunk_size:,} bytes ({chunk_size_mb} MB)")
        print(f"Total Chunks      : {metadata.total_chunks}")
        print(f"Output Directory  : {base_output_dir / input_file.stem}")
        print(f"Metadata File     : {base_output_dir / input_file.stem / 'chunk_metadata.json'}")

        if metadata.total_chunks > 0:
            print(f"\nGenerated Chunks List:")
            for chunk in metadata.chunks:
                print(
                    f"  - [{chunk.index:03d}] {chunk.filename:<18} "
                    f"Offset: {chunk.offset:>10,} bytes | "
                    f"Size: {chunk.size:>10,} bytes"
                )
        else:
            print("\nNote: Input file was empty (0 bytes). No binary chunks created per specification.")

    except (ValidationError, ChunkerError) as err:
        print(f"\n[Error] {err}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user. Exiting cleanly.")
        sys.exit(130)
    except Exception as err:
        print(f"\n[Unexpected Error] An unexpected error occurred: {err}")
        sys.exit(1)


if __name__ == "__main__":
    run()
