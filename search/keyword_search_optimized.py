import re
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

def _normalize_term(term: str) -> str:
    # Assumes this returns lowercase / punctuation-stripped text in the same
    # shape you use for content normalization.
    return utils.remove_punctuation_and_normalize_text(term)


# Normalize and deduplicate all terms once
NORMALIZED_MATCH_LISTS: Dict[str, List[str]] = {
    category: list(dict.fromkeys(
        _normalize_term(term)
        for term in terms
        if term  # skip empty strings / None
    ))
    for category, terms in ALL_MATCH_LISTS.items()
}

# Build a compiled regex per category, enforcing “standalone token” boundaries.
# We mimic your "not embedded in larger alphanumeric token" logic:
# before char is not [0-9A-Za-z] (or start of string)
# after char is not [0-9A-Za-z] (or end of string)
_BOUNDARY_BEFORE = r'(?<![0-9A-Za-z])'
_BOUNDARY_AFTER = r'(?![0-9A-Za-z])'

NORMALIZED_PATTERNS: Dict[str, re.Pattern] = {}

for category, terms in NORMALIZED_MATCH_LISTS.items():
    if not terms:
        continue

    # Escape each term to avoid regex meta-char issues
    # and join into a single alternation.
    alternation = "|".join(re.escape(t) for t in terms if t)
    pattern = re.compile(_BOUNDARY_BEFORE + "(" + alternation + ")" + _BOUNDARY_AFTER)
    NORMALIZED_PATTERNS[category] = pattern


def _find_matches_in_content(content: Union[str, bytes]) -> Dict[str, List[str]]:
    """
    Given a file's content, return a dict of:
        { category_name: [matched_strings_from_that_category] }

    Matching is:
    - Case-insensitive / normalized via utils.remove_punctuation_and_normalize_text
    - Based on full strings from the lists (post-normalization).
    - The matched string must not be embedded inside a larger
      alphanumeric token (enforced by regex boundaries).
    """
    # Normalize file content once
    text = utils.remove_punctuation_and_normalize_text(content)

    matches: Dict[str, List[str]] = {}

    for category, pattern in NORMALIZED_PATTERNS.items():
        # Find *all* occurrences of any term in this category
        found = pattern.findall(text)
        if not found:
            continue

        # Current behavior is "term appears or not", not per occurrence;
        # so dedupe while preserving order:
        unique_terms = list(dict.fromkeys(found))
        if unique_terms:
            matches[category] = unique_terms

    return matches


def search_all_assessment_files_for_keyword_matches():
    file_data_list = Config.file_data_manager.get_all_file_data()
    for file_data in file_data_list:
        file_matches = _find_matches_in_content(file_data.file_content)
        if file_matches:
            file_data.keyword_matches = file_matches


if __name__ == "__main__":
    search_all_assessment_files_for_keyword_matches()