from pathlib import Path
from typing import List

import print_utils
import utils
from models.FileData import FileDataManager
from loggers.main_logger import main_logger as logger
from search import fuzzy_license_search, keyword_search, full_license_search, keyword_search_optimized
from timer import Timer
from configuration import Configuration as Config
from tools import assessment_extractor, assessment_reader, file_release_assessor, file_hash_assessor, \
    file_content_indexer, fuzzy_matches_evaluator, assessment_data_generator
from tools.file_content_indexer import PatternIndex

p = Path(__file__).resolve()

main_timer = Timer()
main_timer.start("starting main timer")

# Global instance of file data manager
Config.file_data_manager = FileDataManager()

def main() -> None:

    #assessment_extractor.create_assessment_from_source(Config.source_project_dir, Config.dest_assessment_dir)

    # CREATES A FILE DATA OBJECT FOR EACH FILE IN THE ASSESSMENT
    assessment_reader_timer = Timer()
    assessment_reader_timer.start("starting assessment reader timer")
    assessment_reader.read_all_assessment_files(Config.dest_assessment_dir)
    assessment_reader_timer.stop("stopping assessment reader timer")
    print(logger.info(assessment_reader_timer.elapsed("Elapsed time for assessment reader: ")))

    # DETERMINE IF A FILE IS PART OF THE RELEASE
    file_release_assessor.set_file_release_status()

    # GET/SET SHA256 HASH VALUE FOR EACH FILE
    file_hash_assessor.compute_file_hashes_for_assessment()

    # READ/LOAD/NORMALIZE CONTENT OF LICENSES
    license_header_reader_timer = Timer()
    license_header_reader_timer.start("starting license header reader timer")
    license_headers_normalized = utils.read_and_normalize_licenses(Config.all_license_headers_dir)
    license_header_reader_timer.stop("stopping license header reader timer")
    print(logger.info(license_header_reader_timer.elapsed("Elapsed time for license header reader: ")))

    license_reader_timer = Timer()
    license_reader_timer.start("starting license reader timer")
    licenses_normalized = utils.read_and_normalize_licenses(Config.all_licenses_dir)
    license_reader_timer.stop("stopping license reader timer")
    print(logger.info(license_reader_timer.elapsed("Elapsed time for license reader: ")))


    # BREAK LICENSE AND FILE STRING INDEXING OUT INTO THEIR OWN MODULES
    file_indexing_timer = Timer()
    file_indexing_timer.start("starting file indexing timer")
    Config.file_indexes = file_content_indexer.build_file_indexes(Config.file_data_manager.get_all_file_data(), anchor_size=4)
    file_indexing_timer.stop("stopping file indexing timer")
    print(logger.info(file_indexing_timer.elapsed("Elapsed time for file indexing: ")))

    license_indexing_timer = Timer()
    license_indexing_timer.start("starting license indexing timer")
    Config.license_header_indexes = file_content_indexer.build_pattern_indexes_from_dict(license_headers_normalized, anchor_size=4)
    license_indexing_timer.stop("stopping license indexing timer")
    print(logger.info(license_indexing_timer.elapsed("Elapsed time for license indexing: ")))
    #Config.license_indexes = file_content_indexer.build_pattern_indexes_from_dict(licenses_normalized, anchor_size=4)
    #print("Combining license indexes")
    #combined_license_indexes: List[PatternIndex] = Config.license_indexes + Config.license_header_indexes

    # SCAN ALL ASSESSMENT FILES FOR FULL LICENSE MATCHES
    print("Begin full license search")
    full_license_search_timer = Timer()
    full_license_search_timer.start("starting full license search timer")
    full_license_search.search_assessment_files_for_full_licenses(licenses_normalized)
    full_license_search_timer.stop("stopping full license search timer")
    print(logger.info(full_license_search_timer.elapsed("Elapsed time for full license search: ")))

    # SCAN ALL ASSESSMENT FILES FOR FUZZY MATCHES OF LICENSE HEADERS
    print("Begin fuzzy license search")
    fuzzy_license_search_timer = Timer()
    fuzzy_license_search_timer.start("starting fuzzy license search timer")
    fuzzy_license_search.fuzzy_match_licenses_in_assessment_files(Config.license_header_indexes)
    fuzzy_license_search_timer.stop("stopping fuzzy license search timer")
    print(logger.info(fuzzy_license_search_timer.elapsed("Elapsed time for fuzzy license search: ")))

    # FILTER FUZZY MATCHES
    print("Begin fuzzy license evaluator")
    fuzzy_evaluator_timer = Timer()
    fuzzy_evaluator_timer.start("starting fuzzy evaluator timer")
    fuzzy_matches_evaluator.determine_best_fuzzy_matches_from_file_data()
    fuzzy_evaluator_timer.stop("stopping fuzzy evaluator timer")
    print(logger.info(fuzzy_evaluator_timer.elapsed("Elapsed time for fuzzy evaluator: ")))

    # SCAN ALL ASSESSMENT FILES FOR KEYWORDS
    print("Begin keyword search")
    keyword_search_timer = Timer()
    keyword_search_timer.start("starting keyword search timer")
    keyword_search.search_all_assessment_files_for_keyword_matches()
    #keyword_search_optimized.search_all_assessment_files_for_keyword_matches()
    keyword_search_timer.stop("stopping keyword search timer")
    print(logger.info(keyword_search_timer.elapsed("Elapsed time for keyword search: ")))

    # GENERATE CSV OF ASSESSMENT DATA
    print("Begin csv gen")
    csv_gen_timer = Timer()
    csv_gen_timer.start("starting csv gen timer")
    assessment_data_generator.write_license_data_to_csv("".join([Config.assessment_name, "_data3", ".csv"]))
    csv_gen_timer.stop("stopping csv gen timer")
    print(logger.info(csv_gen_timer.elapsed("Elapsed time for csv gen: ")))

    # SAVE FILE DATA TO JSON
    print("Begin save file data to json")
    file_data_to_json_timer = Timer()
    file_data_to_json_timer.start("starting file data to json timer")
    Config.file_data_manager.save_to_json()
    file_data_to_json_timer.stop("stopping file data to json timer")
    print(logger.info(file_data_to_json_timer.elapsed("Elapsed time for file data to json: ")))



if __name__ == "__main__":
    main()

    # print_utils.print_files_with_full_license_match()
    print_utils.print_files_with_fuzzy_license_matches()
    print('Done')
    main_timer.stop("stopping main timer")
    print(logger.info(main_timer.elapsed("Elapsed time for main: ")))

