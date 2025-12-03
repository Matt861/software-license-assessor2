import os
from jproperties import Properties
from dotenv import load_dotenv
from pathlib import Path
from root import get_project_root

p = Path(__file__).resolve()


class Configuration:
    load_dotenv()
    configs = Properties()
    # properties_file = Path('app-config.properties').resolve()
    properties_file = os.path.join(p.parent, 'app-config.properties')
    with open(properties_file, 'rb') as config_file:
        configs.load(config_file)

    root_dir = get_project_root()
    ignore_dirs_str = configs.get('IGNORE_DIRS').data
    ignore_dirs = [part.strip() for part in ignore_dirs_str.split(",")]
    review_file_dir = configs.get('REVIEW_FILE_DIR').data
    source_dir = Path(configs.get("SOURCE_DIR").data).resolve()
    dest_dir = Path(configs.get("DEST_DIR").data).resolve()
    spdx_licenses_dir = Path(root_dir, configs.get("SPDX_LICENSES_DIR").data)
    manual_licenses_dir = Path(root_dir, configs.get("MANUAL_LICENSES_DIR").data)
    all_licenses_dir = [spdx_licenses_dir, manual_licenses_dir]
    spdx_license_headers_dir = Path(root_dir, configs.get("SPDX_LICENSE_HEADERS_DIR").data)
    manual_license_headers_dir = Path(configs.get("MANUAL_LICENSE_HEADERS_DIR").data).resolve()
    all_license_headers_dir = [spdx_license_headers_dir, manual_license_headers_dir]
    project_name = configs.get("PROJECT_NAME").data
    #assessments_dir = Path(configs.get("ASSESSMENTS_DIR").data)
    assessment_name = Path(configs.get("ASSESSMENT_NAME").data)
    assessment_name_str = configs.get("ASSESSMENT_NAME").data
    file_hash_algorithm = configs.get("FILE_HASH_ALGORITHM").data
    output_dir = Path(configs.get("OUTPUT_DIR").data).resolve()
    data_dir = Path(configs.get("DATA_DIR").data).resolve()

    # Global instance of file data manager
    file_data_manager = None
    # Indexed assessment file content
    file_indexes = None
    # Indexed license content
    license_indexes = None
    # Indexed license header content
    license_header_indexes = None

