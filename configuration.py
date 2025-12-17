from property_reader import load_properties
from root import get_project_root
import utils
from pathlib import Path


p = Path(__file__).resolve()

class Configuration:
    root_dir = get_project_root()
    config_path = Path(root_dir, "config.properties")
    props = load_properties(config_path)
    ignore_dirs = [part.strip() for part in props["IGNORE_DIRS"].split(",")]
    spdx_licenses_dir = Path(root_dir, props["SPDX_LICENSES_DIR"])
    manual_licenses_dir = Path(root_dir, props["MANUAL_LICENSES_DIR"])
    all_licenses_dir = [spdx_licenses_dir, manual_licenses_dir]
    spdx_license_headers_dir = Path(root_dir, props["SPDX_LICENSE_HEADERS_DIR"])
    manual_license_headers_dir = Path(root_dir, props["MANUAL_LICENSE_HEADERS_DIR"])
    all_license_headers_dir = [spdx_license_headers_dir, manual_license_headers_dir]
    file_hash_algorithm = props["FILE_HASH_ALGORITHM"]
    output_dir = Path(root_dir, props["OUTPUT_DIR"])
    data_dir = Path(root_dir, props["DATA_DIR"])
    source_dir = props["SOURCE_DIR"]
    dest_dir = props["DEST_DIR"]
    source_project_name = props["SOURCE_PROJECT_NAME"]
    assessment_name = props["ASSESSMENT_NAME"]
    source_dir_is_network = props["SOURCE_DIR_IS_NETWORK"]
    dest_dir_is_network = props["DEST_DIR_IS_NETWORK"]
    source_project_dir = utils.get_source_project_dir(source_dir, source_project_name, source_dir_is_network)
    dest_assessment_dir = utils.get_dest_assessment_dir(dest_dir, assessment_name, dest_dir_is_network)

    # Global instance of file data manager
    file_data_manager = None
    # Global instance of loaded file data manager
    loaded_file_data_manager = None
    # Indexed assessment file content
    file_indexes = None
    # Indexed license content
    license_indexes = None
    # Indexed license header content
    license_header_indexes = None
    # Total assessment file count
    assessment_file_count = 0
    # Total released file couht
    released_file_count = 0