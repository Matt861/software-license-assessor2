import utils
from configuration import Configuration as Config
from tools import file_content_indexer


def search_assessment_files_for_full_licenses(licenses_normalized):
    for file_data in Config.file_data_manager.get_all_file_data():
        if file_data.file_content:
            file_content = utils.remove_punctuation_and_normalize_text(file_data.file_content)
            license_matches = []
            for license_path, license_content in licenses_normalized.items():
                if license_content and license_content in file_content:
                    license_name = utils.get_file_name_from_path_without_extension(license_path)
                    license_match = {"License_name": license_name, "License_text": license_content}
                    license_matches.append(license_match)
            if license_matches:
                file_data.license_match_strength = "EXACT"
                for license_item in license_matches:
                    file_data.license_matches.append(license_item)
                    file_data.license_names.append(license_item.get("License_name"))
                    file_data.has_full_license = True




if __name__ == "__main__":
    license_headers_normalized = utils.read_and_normalize_licenses(Config.all_license_headers_dir)
    Config.license_header_indexes = file_content_indexer.build_pattern_indexes_from_dict(license_headers_normalized, anchor_size=4)
    search_assessment_files_for_full_licenses(Config.license_header_indexes)