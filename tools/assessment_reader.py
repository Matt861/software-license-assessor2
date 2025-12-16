from configuration import Configuration as Config
from loggers.assessment_reader_logger import assessment_reader_logger as logger
from models.FileData import FileData
import utils
import os
from pathlib import Path
from typing import Union


# def read_all_assessment_files(root_dir):
#     """
#     Iterates through all files in root_dir (including subdirectories),
#     reads their content, and creates FileData instances for each file.
#     """
#
#     # # Optional: start with a clean registry for each run
#     # FileData.clear_registry()
#
#     for dirpath, dirnames, filenames in os.walk(root_dir):
#         for filename in filenames:
#             file_path = Path(dirpath, filename).resolve()
#             print(f"Reading: {file_path}")
#
#             try:
#                 # Try reading as text
#                 with open(file_path, "r", encoding="utf-8") as f:
#                     content: Union[str, bytes] = f.read()
#             except UnicodeDecodeError:
#                 # Fallback to binary
#                 with open(file_path, "rb") as f:
#                     content = f.read()
#             except Exception as e:
#                 print(logger.exception(f"Could not read {file_path}: {e}"))
#                 continue
#
#             file_data = FileData(file_path, content)
#             file_extension = utils.get_file_extension(file_path)
#             file_data.file_extension = file_extension
#             Config.file_data_manager.add_file_data(file_data)

def read_all_assessment_files(root_dir):
    """
    Iterates through all files in root_dir (including subdirectories),
    reads their content, and creates FileData instances for each file.
    Optimized to:
      - Read each file only once (binary).
      - Attempt UTF-8 decode in memory.
      - Avoid expensive Path.resolve calls.
    """

    root_dir = Path(root_dir)

    add_file_data = Config.file_data_manager.add_file_data
    get_file_extension = utils.get_file_extension

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirpath_path = Path(dirpath)

        for filename in filenames:
            file_path = dirpath_path / filename
            print(f"Reading: {file_path}")

            try:
                # Read once in binary
                with open(file_path, "rb") as f:
                    raw: bytes = f.read()
            except Exception as e:
                print(logger.exception(f"Could not read {file_path}: {e}"))
                continue

            # Try to decode as UTF-8, fall back to bytes
            try:
                content: Union[str, bytes] = raw.decode("utf-8")
            except UnicodeDecodeError:
                content = raw

            file_data = FileData(file_path, content)
            file_data.file_extension = get_file_extension(file_path)
            add_file_data(file_data)


if __name__ == "__main__":
    read_all_assessment_files(Path(Config.dest_dir, Config.assessment_name))