import hashlib
import os
import re
from pathlib import Path
from typing import Union, Optional, List
import utils
from models.FileData import FileData
from configuration import Configuration as Config
from concurrent.futures import ThreadPoolExecutor, as_completed
from loggers.assessment_reader_logger import assessment_reader_logger as logger


# One or more control chars (except \n, \r, \t) → single space
_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]+')

# Optional: literal "\xNN" escape sequences → single space
_HEX_ESCAPE_RE = re.compile(r'(?:\\x[0-9A-Fa-f]{2})+')


def is_ignored_dir(src_dir: Path) -> bool:
    src_dir_str = str(src_dir)
    for ignore_dir in Config.ignore_dirs:
        if ignore_dir in str(src_dir_str):
            return True
    return False


def clean_decoded_binary_text(text: str) -> str:
    """
    Replace runs of binary-like/control characters in text with a single space.

    This targets:
      - Actual control characters (NUL, BEL, etc.) in the decoded string.
      - Literal '\\xNN' escape sequences, if they appear as text.

    Newlines and tabs are preserved.
    """
    # Remove actual control characters (not visible but still in the string)
    text = _CONTROL_CHARS_RE.sub(' ', text)

    # If your decoding ever produces literal backslash-x sequences like "\x00"
    # as real characters, this cleans those too.
    text = _HEX_ESCAPE_RE.sub(' ', text)

    return text


def _read_single_file(file_path: Path) -> Optional["FileData"]:
    try:
        with open(file_path, "rb") as f:
            raw: bytes = f.read()
    except Exception as e:
        #logger.exception("Could not read %s: %s", file_path, e)
        print(logger.exception(f"Could not read file: {file_path} exception: {e}"))
        return None

    # Determine if the file is empty
    is_empty = (len(raw) == 0)

    # compute hash directly from raw bytes (only disk read)
    algo = Config.file_hash_algorithm  # e.g., "sha256"
    h = hashlib.new(algo)
    h.update(raw)
    file_hash = h.hexdigest()


    if is_empty:
        # You can choose "" or b""; "" keeps things simple for text handling
        content: Union[str, bytes] = ""
        print(logger.info(f"File empty: {file_path}"))
    else:
        try:
            # First attempt: strict UTF-8 decode
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback: decode with errors ignored, then clean
            # This is where your \x00-style junk shows up.
            decoded = raw.decode("utf-8", errors="ignore")

        # At this point `decoded` is always a str from bytes,
        content = decoded

    file_data = FileData(file_path, content)
    file_data.file_extension = utils.get_file_extension(file_path)
    file_data.file_is_empty = is_empty
    #file_data.file_hash = file_hash
    #cleaned_file_content = clean_decoded_binary_text(content)
    #file_data.file_content_normalized = utils.remove_punctuation_and_normalize_text(cleaned_file_content)
    return file_data


def read_all_assessment_files(root_dir, max_workers: Optional[int] = None):
    """
    Multithreaded version:
      - Walks the directory tree once to collect file paths.
      - Uses a ThreadPoolExecutor to read files in parallel.
    """

    root_dir = Path(root_dir)

    # 1. Collect all file paths first (cheap)
    file_paths: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirpath_path = Path(dirpath)
        for filename in filenames:
            if not is_ignored_dir(dirpath_path / filename):
                file_paths.append(dirpath_path / filename)

    #logger.info("Found %d files to read under %s", len(file_paths), root_dir)
    print(logger.info(f"Found files to read under: {len(file_paths)} {root_dir}"))

    add_file_data = Config.file_data_manager.add_file_data

    # 2. Read in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {
            executor.submit(_read_single_file, p): p for p in file_paths
        }

        for future in as_completed(future_to_path):
            file_data = future.result()
            if file_data is not None:
                add_file_data(file_data)


if __name__ == "__main__":
    read_all_assessment_files(Path(Config.dest_dir, Config.assessment_name))