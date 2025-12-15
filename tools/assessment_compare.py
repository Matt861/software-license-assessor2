from configuration import Configuration as Config
from loggers.assessment_compare_logger import assessment_compare_logger as logger
from typing import Iterable, List, Set, Optional
from models.FileData import FileData


# def compare_assessment_file_hashes(old_data: Iterable[FileData], new_data: Iterable[FileData],) -> List[FileData]:
#     """
#     Returns FileData items from list_b whose file_hash does NOT appear anywhere in list_a.
#     Comparison is based ONLY on file_hash (file_path is ignored).
#
#     Notes:
#       - None hashes are ignored in both lists (i.e., they won't be considered "missing"
#         and won't be used to match). Change if you want different behavior.
#     """
#     old_file_data_hashes: Set[str] = {fd.file_hash for fd in old_data if fd.file_hash}
#
#     return [
#         fd
#         for fd in new_data
#         if fd.file_hash and fd.file_hash not in old_file_data_hashes
#     ]


def compare_assessment_file_hashes(old_data: Iterable[FileData], new_data: Iterable[FileData],) -> List[FileData]:
    """
    Returns FileData items from list_b whose file_hash does NOT appear anywhere in list_a.
    Comparison is based ONLY on file_hash (file_path is ignored).

    Notes:
      - None/empty hashes are ignored in both lists.
    """
    old_file_data_hashes: Set[str] = set()

    for fd in old_data:
        file_hash = fd.file_hash
        # if "003cd0a16a54e9ff1e852cb08b8d5b0b3df17ac8f8cc382537097d82e35251b2" in file_hash:
        #     print('')
        if file_hash:
            old_file_data_hashes.add(file_hash)

    results: List[FileData] = []

    for fd in new_data:
        file_hash = fd.file_hash
        #
        # if "003cd0a16a54e9ff1e852cb08b8d5b0b3df17ac8f8cc382537298d82g35221b2" in file_hash:
        #     print('')

        # Skip None/empty hashes
        if not file_hash:
            #continue
            results.append(fd)

        if file_hash not in old_file_data_hashes:
            results.append(fd)

    return results


if __name__ == "__main__":
    old_file_data = Config.loaded_file_data_manager.get_all_file_data()
    new_file_data = Config.file_data_manager.get_all_file_data()
    compare_assessment_file_hashes(old_file_data, new_file_data)