import utils
from configuration import Configuration as Config
from loggers.full_license_search_logger import full_license_search_logger as logger
from tools import file_content_indexer
from pathlib import Path
from typing import Dict, List, Tuple

from tools.file_content_indexer import FileIndex


# licenses_normalized: Dict[Path, str] is already normalized text per license
def build_license_metadata(licenses_normalized: Dict[Path, str]) -> List[Tuple[str, str]]:
    """
    Convert {path -> normalized_text} into a list of (license_name, license_content),
    skipping empty contents.
    """
    result: List[Tuple[str, str]] = []
    for license_path, license_content in licenses_normalized.items():
        if not license_content:
            continue
        license_name = utils.get_file_name_from_path_without_extension(license_path)
        result.append((license_name, license_content))
    return result


def search_assessment_files_for_full_licenses(license_metadata: List[Tuple[str, str]], file_indexes: List[FileIndex],):
    """
    Faster version:
      - Uses pre-indexed, normalized file text from FileIndex.text
      - Avoids re-normalizing file content in the hot loop
      - Reuses precomputed license_metadata [(license_name, license_content)]
    """

    # Optional: map file_data id -> FileIndex for quick lookup if needed elsewhere
    # file_index_by_obj_id = {id(idx.source_obj): idx for idx in file_indexes}

    for idx in file_indexes:
        file_data = idx.source_obj  # your FileData object
        # FileIndex.text should already be normalized with remove_punctuation_and_normalize_text
        file_content = idx.text

        if not file_content:
            continue

        # Simple length check can skip obviously impossible matches
        content_len = len(file_content)

        license_matches = []
        for license_name, license_content in license_metadata:
            # Skip if license longer than file content
            if len(license_content) > content_len:
                continue

            if license_content in file_content:
                license_matches.append(
                    {"License_name": license_name, "License_text": license_content}
                )

        if license_matches:
            file_data.license_match_strength = "EXACT"
            file_data.has_full_license = True
            # Extend once instead of appending in a loop
            file_data.license_matches.extend(license_matches)
            # Append just the names
            file_data.license_names.extend(
                match["License_name"] for match in license_matches
            )


if __name__ == "__main__":
    licenses_normalized = utils.read_and_normalize_licenses(Config.all_licenses_dir)
    license_metadata = build_license_metadata(licenses_normalized)
    search_assessment_files_for_full_licenses(license_metadata, Config.file_indexes)