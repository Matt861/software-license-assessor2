import os
from jproperties import Properties
from dotenv import load_dotenv
from pathlib import Path

import utils
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
    spdx_licenses_dir = Path(root_dir, configs.get("SPDX_LICENSES_DIR").data)
    manual_licenses_dir = Path(root_dir, configs.get("MANUAL_LICENSES_DIR").data)
    all_licenses_dir = [spdx_licenses_dir, manual_licenses_dir]
    spdx_license_headers_dir = Path(root_dir, configs.get("SPDX_LICENSE_HEADERS_DIR").data)
    manual_license_headers_dir = Path(root_dir, configs.get("MANUAL_LICENSE_HEADERS_DIR").data)
    all_license_headers_dir = [spdx_license_headers_dir, manual_license_headers_dir]
    file_hash_algorithm = configs.get("FILE_HASH_ALGORITHM").data
    output_dir = Path(configs.get("OUTPUT_DIR").data).resolve()
    data_dir = Path(configs.get("DATA_DIR").data).resolve()
    # source_dir = Path(configs.get("SOURCE_DIR").data)
    #source_dir = open('//networkdrive/license_assessments/source')
    source_dir = configs.get("SOURCE_DIR").data
    dest_dir = configs.get("DEST_DIR").data
    source_project_name = configs.get("SOURCE_PROJECT_NAME").data
    assessment_name = configs.get("ASSESSMENT_NAME").data
    #source_project_dir = Path(source_dir, source_project_name)
    #source_project_dir = source_dir / source_project_name
    source_dir_is_network = configs.get("SOURCE_DIR_IS_NETWORK").data
    dest_dir_is_network = configs.get("DEST_DIR_IS_NETWORK").data
    source_project_dir = utils.get_source_project_dir(source_dir, source_project_name, source_dir_is_network)
    #dest_assessment_dir = Path(dest_dir, assessment_name)
    dest_assessment_dir = utils.get_dest_assessment_dir(dest_dir, assessment_name, dest_dir_is_network)

    # USE THIS ON NETWORKS WHERE DOTENV AND JPROPERTIES ARE NOT APPROVED FOR USE
    # root_dir = get_project_root()
    # ignore_dirs_str = "src/test, src\\test"
    # ignore_dirs = [part.strip() for part in ignore_dirs_str.split(",")]
    # source_dir = "C:/license_assessments/source"
    # dest_dir = "C:/license_assessments/extracted"
    # spdx_licenses_dir = Path(root_dir, "input/spdx_licenses")
    # manual_licenses_dir = Path(root_dir, "input/manual_licenses")
    # all_licenses_dir = [spdx_licenses_dir, manual_licenses_dir]
    # spdx_license_headers_dir = Path(root_dir, "input/spdx_license_headers")
    # manual_license_headers_dir = Path(root_dir, "input/manual_license_headers")
    # all_license_headers_dir = [spdx_license_headers_dir, manual_license_headers_dir]
    # source_project_name = "my-ubi8-java8.tar"
    # assessment_name = "ubi8-java8-assessment"
    # file_hash_algorithm = "sha256"
    # output_dir = Path(root_dir, "output")
    # data_dir = Path(root_dir, "data")
    # source_project_dir = Path(source_dir, source_project_name)
    # dest_assessment_dir = Path(dest_dir, assessment_name)



    # Global instance of file data manager
    file_data_manager = None
    # Indexed assessment file content
    file_indexes = None
    # Indexed license content
    license_indexes = None
    # Indexed license header content
    license_header_indexes = None

