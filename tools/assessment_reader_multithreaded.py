import os
from pathlib import Path
from typing import Union, Optional, List
import utils
from models.FileData import FileData
from configuration import Configuration as Config
from concurrent.futures import ThreadPoolExecutor, as_completed
from loggers.assessment_reader_logger import assessment_reader_logger as logger


def _read_single_file(file_path: Path) -> Optional["FileData"]:
    if "PropertyEditorManager" in str(file_path):
        print('found')
    try:
        with open(file_path, "rb") as f:
            raw: bytes = f.read()
    except Exception as e:
        #logger.exception("Could not read %s: %s", file_path, e)
        print(logger.exception(f"Could not read file: {file_path} exception: {e}"))
        return None

    # Determine if the file is empty
    is_empty = (len(raw) == 0)

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