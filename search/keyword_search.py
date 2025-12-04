from typing import Dict, List, Union

import utils
from configuration import Configuration as Config
from input.keyword_strings import copyright_matches, license_matches, prohibitive_matches, general_matches, \
    export_matches, custom_search_matches, license_name_matches, license_abbreviation_matches, license_url_matches

ALL_MATCH_LISTS: Dict[str, List[str]] = {
    #"copyright": copyright_matches,
    "license": license_matches,
    #"prohibitive": prohibitive_matches,
    "general": general_matches,
    #"export": export_matches,
    "custom": custom_search_matches,
    "license_name": license_name_matches,
    "license_abbreviation": license_abbreviation_matches,
    "license_urls": license_url_matches,
}


def _find_matches_in_content(content: Union[str, bytes]) -> Dict[str, List[str]]:
    """
    Given a file's content, return a dict of:
        { category_name: [matched_strings_from_that_category] }

    Matching is:
    - Case-insensitive
    - Based on full strings from the lists (e.g. we look specifically
      for 'Eclipse Public License', not just 'Eclipse').
    - The matched string must not be embedded inside a larger
      alphanumeric token. For example, 'mpl' should NOT match 'fdsmplew'.
    """
    # text = utils.to_text(content)
    # text_lower = text.lower()
    text = utils.remove_punctuation_and_normalize_text(content)

    def _contains_standalone(haystack: str, needle: str) -> bool:
        """
        Return True if `needle` appears in `haystack` such that the
        characters immediately before and after it (if any) are NOT
        alphanumeric. This prevents matching inside larger words.
        """
        if not needle:
            return False

        start = 0
        n = len(needle)
        L = len(haystack)

        while True:
            idx = haystack.find(needle, start)
            if idx == -1:
                return False

            # Check character before the match
            before_ok = (idx == 0) or (not haystack[idx - 1].isalnum())
            # Check character after the match
            after_idx = idx + n
            after_ok = (after_idx == L) or (not haystack[after_idx].isalnum())

            if before_ok and after_ok:
                return True

            # Continue searching after this position
            start = idx + 1

    matches: Dict[str, List[str]] = {}

    for category, terms in ALL_MATCH_LISTS.items():
        found_terms: List[str] = []
        for term in terms:
            term = utils.remove_punctuation_and_normalize_text(term)
            if _contains_standalone(text, term):
                found_terms.append(term)

        if found_terms:
            matches[category] = found_terms

    return matches


def search_all_assessment_files_for_keyword_matches():
    for file_data in Config.file_data_manager.get_all_file_data():
        file_matches = _find_matches_in_content(file_data.file_content)
        if file_matches:
            file_data.keyword_matches = file_matches


if __name__ == "__main__":
    search_all_assessment_files_for_keyword_matches()