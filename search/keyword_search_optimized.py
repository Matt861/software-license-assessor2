import collections
import re
from collections import defaultdict
from typing import Dict, List, Union, Set, Tuple
import utils
from configuration import Configuration as Config
from input.keyword_strings import copyright_matches, license_matches, prohibitive_matches, general_matches, \
    export_matches, custom_search_matches, license_name_matches, license_abbreviation_matches, license_url_matches


ALL_MATCH_LISTS: Dict[str, List[str]] = {
    "license": license_matches,
    "general": general_matches,
    "custom": custom_search_matches,
    "license_name": license_name_matches,
    "license_abbreviation": license_abbreviation_matches,
    "license_urls": license_url_matches,
}


def _normalize_term_string(term: str) -> str:
    # Must match the normalization you use for file content
    return utils.remove_punctuation_and_normalize_text(term)


# --- Precomputed indexes ---

# Category -> list of normalized terms in original order (deduped per category)
NORMALIZED_TERMS_BY_CATEGORY: Dict[str, List[str]] = {}

# token -> list of (category, term) for single-word terms
SINGLE_WORD_INDEX: Dict[str, List[Tuple[str, str]]] = collections.defaultdict(list)

# first_token -> list of (category, term, term_tokens) for multi-word terms
MULTI_WORD_INDEX: Dict[str, List[Tuple[str, str, List[str]]]] = collections.defaultdict(list)

for category, terms in ALL_MATCH_LISTS.items():
    seen = set()
    normalized_terms: List[str] = []

    for term in terms:
        if not term:
            continue

        norm = _normalize_term_string(term)
        if not norm:
            continue

        # Deduplicate within this category
        if norm in seen:
            continue
        seen.add(norm)
        normalized_terms.append(norm)

        tokens = norm.split()
        if not tokens:
            continue

        if len(tokens) == 1:
            # single-word term
            SINGLE_WORD_INDEX[tokens[0]].append((category, norm))
        else:
            # multi-word term, index by first token
            MULTI_WORD_INDEX[tokens[0]].append((category, norm, tokens))

    NORMALIZED_TERMS_BY_CATEGORY[category] = normalized_terms


def _find_matches_in_content(content: Union[str, bytes]) -> Dict[str, List[str]]:
    """
    Given a file's content, return a dict of:
        { category_name: [matched_strings_from_that_category] }

    Matching is:
    - Case-insensitive via utils.remove_punctuation_and_normalize_text
    - Based on full normalized strings from the lists.
    - Terms are matched as whole tokens or sequences of tokens
      (no matching inside larger alphanumeric tokens).
    """
    text = utils.remove_punctuation_and_normalize_text(content)
    if not text:
        return {}

    tokens = text.split()
    if not tokens:
        return {}

    # category -> set of normalized terms found
    found_by_category: Dict[str, Set[str]] = defaultdict(set)

    # --- Single-word matches: use the set of unique tokens ---
    unique_tokens = set(tokens)
    for tok in unique_tokens:
        entries = SINGLE_WORD_INDEX.get(tok)
        if not entries:
            continue
        for category, term in entries:
            found_by_category[category].add(term)

    # --- Multi-word matches: single pass over tokens ---
    n = len(tokens)
    for i, tok in enumerate(tokens):
        candidates = MULTI_WORD_INDEX.get(tok)
        if not candidates:
            continue

        remaining = n - i
        for category, term, term_tokens in candidates:
            L = len(term_tokens)
            if L > remaining:
                continue
            # Compare the slice of tokens to the term tokens
            if tokens[i:i + L] == term_tokens:
                found_by_category[category].add(term)

    # --- Build output preserving original term order per category ---
    matches: Dict[str, List[str]] = {}
    for category, terms_in_order in NORMALIZED_TERMS_BY_CATEGORY.items():
        found_set = found_by_category.get(category)
        if not found_set:
            continue

        ordered = [t for t in terms_in_order if t in found_set]
        if ordered:
            matches[category] = ordered

    return matches


def search_all_assessment_files_for_keyword_matches():
    file_data_list = Config.file_data_manager.get_all_file_data()
    for file_data in file_data_list:
        file_matches = _find_matches_in_content(file_data.file_content)
        if file_matches:
            file_data.keyword_matches = file_matches


if __name__ == "__main__":
    search_all_assessment_files_for_keyword_matches()