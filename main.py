from pathlib import Path

import print_utils
import utils
from models.FileData import FileDataManager
from search import fuzzy_license_search, keyword_search
from timer import Timer
from configuration import Configuration as Config
from tools import assessment_extractor, assessment_reader, file_release_assessor, file_hash_assessor, \
    file_content_indexer, fuzzy_matches_evaluator, assessment_data_generator

p = Path(__file__).resolve()

timer = Timer()
timer.start()

# Global instance of file data manager
Config.file_data_manager = FileDataManager()

def main() -> None:

    assessment_extractor.create_assessment_from_source(Config.source_project_dir, Config.dest_assessment_dir)

    # CREATES A FILE DATA OBJECT FOR EACH FILE IN THE ASSESSMENT
    assessment_reader.read_all_assessment_files(Config.dest_assessment_dir)
    # DETERMINE IF A FILE IS PART OF THE RELEASE
    file_release_assessor.set_file_release_status()
    # GET/SET SHA256 HASH VALUE FOR EACH FILE
    file_hash_assessor.compute_file_hashes_for_assessment()
    # READ/LOAD/NORMALIZE CONTENT OF LICENSES
    license_headers_normalized = utils.read_and_normalize_licenses([Config.spdx_license_headers_dir, Config.manual_license_headers_dir])
    # BREAK LICENSE AND FILE STRING INDEXING OUT INTO THEIR OWN MODULES
    Config.file_indexes = file_content_indexer.build_file_indexes(Config.file_data_manager.get_all_file_data(), anchor_size=4)
    Config.license_header_indexes = file_content_indexer.build_pattern_indexes_from_dict(license_headers_normalized, anchor_size=4)
    # SCAN ALL ASSESSMENT FILES FOR FUZZY MATCHES OF LICENSE HEADERS
    fuzzy_license_search.fuzzy_match_licenses_in_assessment_files(Config.license_header_indexes)
    # FILTER FUZZY MATCHES
    fuzzy_matches_evaluator.determine_best_fuzzy_matches_from_file_data()
    # SCAN ALL ASSESSMENT FILES FOR KEYWORDS
    keyword_search.search_all_assessment_files_for_keyword_matches()
    # GENERATE CSV OF ASSESSMENT DATA
    assessment_data_generator.write_license_data_to_csv("".join([Config.assessment_name, "_data", ".csv"]))



if __name__ == "__main__":
    main()

    # print_utils.print_files_with_full_license_match()
    print_utils.print_files_with_fuzzy_license_matches()
    print('Done')
    timer.stop()
    print(timer.elapsed())

