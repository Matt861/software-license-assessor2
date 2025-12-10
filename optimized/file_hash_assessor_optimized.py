import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from configuration import Configuration as Config
from models.FileData import FileData
from loggers.file_hash_assessor_logger import file_hash_assessor_logger as logger

# Larger chunk size = fewer read syscalls & loop iterations
CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB


def hash_file(file_path: Path, algo: str) -> str:
    """
    Compute the hash of a single file using the given algorithm.
    Optimized for fewer Python-level operations.
    """
    h = hashlib.new(algo)

    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)

    return h.hexdigest()


def hash_folder(folder_path: Path, algo: str) -> str:
    """
    Compute a deterministic hash of all files in a folder (recursively).
    (Kept for completeness; likely not your hot path.)
    """
    h = hashlib.new(algo)
    folder_path = folder_path.resolve()

    for root, dirs, files in os.walk(folder_path):
        dirs.sort()
        files.sort()

        for name in files:
            file_path = Path(root) / name
            rel_path = file_path.relative_to(folder_path).as_posix()

            h.update(rel_path.encode("utf-8"))
            h.update(b"\0")

            with file_path.open("rb") as f:
                for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
                    h.update(chunk)

    return h.hexdigest()


def _hash_single_filedata(file_data: "FileData", algo: str) -> None:
    """
    Worker: compute hash for a single FileData if needed.
    """
    path = file_data.file_path
    #print(f"Generating hash for file: {path}")

    # Skip if already hashed
    if getattr(file_data, "file_hash", None):
        return

    # If some file_data objects might reference directories, skip or handle as needed
    if not path.is_file():
        # If you want folder hashing, call hash_folder here instead.
        # For now, just skip non-files.
        return

    try:
        digest = hash_file(path, algo)
        file_data.file_hash = digest
    except Exception as e:
        # Prefer logger over print in real code
        print(logger.exception(f"Error hashing {path}: {e}"))


def compute_file_hashes_for_assessment(max_workers: int | None = None) -> None:
    """
    Compute SHA-256 (or configured) hashes for all FileData objects.

    Improvements:
      - Avoid path.exists()/is_dir checks per file where unnecessary.
      - Skip already-hashed files.
      - Use a ThreadPoolExecutor to hash files in parallel.
      - Larger CHUNK_SIZE for fewer syscalls.
    """
    algo = Config.file_hash_algorithm
    file_data_list = Config.file_data_manager.get_all_file_data()

    # Optional: filter only file-backed entries upfront
    file_data_list = [fd for fd in file_data_list if isinstance(fd.file_path, Path)]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_hash_single_filedata, fd, algo)
            for fd in file_data_list
        ]

        # Force completion and surface exceptions
        for future in as_completed(futures):
            exc = future.exception()
            if exc is not None:
                print(logger.info(f"Hash worker raised: {exc}"))


if __name__ == "__main__":
    compute_file_hashes_for_assessment()