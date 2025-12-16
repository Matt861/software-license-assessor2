from configuration import Configuration as Config
from models.FileData import FileData
from typing import Iterable, List, Set


def find_new_or_changed_files(old_data: Iterable[FileData], new_data: Iterable[FileData],) -> List[FileData]:
    """
    Returns FileData items from new_data whose file_hash does NOT appear anywhere in old_data.
    Comparison is based ONLY on file_hash (file_path is ignored).

    Notes:
      - None/empty hashes are ignored in both lists.
    """
    old_file_data_hashes: Set[str] = set()

    for fd in old_data:
        file_hash = fd.file_hash
        if file_hash:
            old_file_data_hashes.add(file_hash)

    results: List[FileData] = []

    for fd in new_data:
        file_hash = fd.file_hash

        # Skip None/empty hashes
        if not file_hash:
            #continue
            results.append(fd)

        if file_hash not in old_file_data_hashes:
            results.append(fd)

    return results


def find_removed_files(old_data: Iterable[FileData], new_data: Iterable[FileData],) -> List[FileData]:
    """
    Returns FileData items from new_data whose file_hash does NOT appear anywhere in old_data.
    Comparison is based ONLY on file_hash (file_path is ignored).

    Notes:
      - None/empty hashes are ignored in both lists.
    """
    new_file_data_hashes: Set[str] = set()

    for fd in new_data:
        file_hash = fd.file_hash
        if file_hash:
            new_file_data_hashes.add(file_hash)

    results: List[FileData] = []

    for fd in old_data:
        file_hash = fd.file_hash

        # Skip None/empty hashes
        if not file_hash:
            #continue
            results.append(fd)

        if file_hash not in new_file_data_hashes:
            results.append(fd)

    return results


if __name__ == "__main__":
    old_file_data = Config.loaded_file_data_manager.get_all_file_data()
    new_file_data = Config.file_data_manager.get_all_file_data()
    new_or_changed_hashes = find_new_or_changed_files(old_file_data, new_file_data)
    removed_files = find_removed_files(old_file_data, new_file_data)