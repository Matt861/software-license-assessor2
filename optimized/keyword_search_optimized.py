from configuration import Configuration as Config
import utils
from input.keyword_strings import license_matches, general_matches, \
    custom_search_matches, license_name_matches, license_abbreviation_matches, license_url_matches
from tools.file_content_indexer import FileIndex
import collections
from dataclasses import dataclass
from typing import Dict, List, Set


ALL_MATCH_LISTS: Dict[str, List[str]] = {
    "license": license_matches,
    "general": general_matches,
    "custom": custom_search_matches,
    "license_name": license_name_matches,
    "license_abbreviation": license_abbreviation_matches,
    "license_urls": license_url_matches,
}

def _normalize_term_string(term: str) -> str:
    # Must match how FileIndex.text / tokens were normalized
    return utils.remove_punctuation_and_normalize_text(term)


@dataclass(frozen=True)
class TermInfo:
    category: str
    norm: str         # normalized full string
    tokens: List[str] # normalized token list


# Global list of all terms, plus mapping from category -> [norms in original order]
ALL_TERMS: List[TermInfo] = []
TERMS_BY_CATEGORY: Dict[str, List[str]] = collections.defaultdict(list)

def _build_term_index():
    seen_per_category: Dict[str, set] = collections.defaultdict(set)

    for category, terms in ALL_MATCH_LISTS.items():
        for term in terms:
            if not term:
                continue

            norm = _normalize_term_string(term)
            if not norm:
                continue

            if norm in seen_per_category[category]:
                continue
            seen_per_category[category].add(norm)

            tokens = norm.split()
            if not tokens:
                continue

            ti = TermInfo(
                category=category,
                norm=norm,
                tokens=tokens,
            )
            ALL_TERMS.append(ti)
            TERMS_BY_CATEGORY[category].append(norm)


# Call once at import/init
_build_term_index()


def _get_token_texts(index: FileIndex) -> List[str]:
    """
    Extract the normalized token text from FileIndex.tokens.

    Adjust "norm" to whatever your token dict key is
    (e.g., 'text', 'normalized', etc.).
    """
    return [t["norm"] for t in index.tokens]  # <-- change key if needed


def _find_matches_in_index(index: FileIndex) -> Dict[str, List[str]]:
    """
    Given a FileIndex, return:
        { category_name: [matched_normalized_terms_in_that_category] }

    Matching:
    - Single-word terms: token-set membership.
    - Multi-word terms: sliding-window token sequence comparison.
    - No trigrams used.
    """
    if not index.tokens:
        return {}

    tokens = _get_token_texts(index)
    token_count = len(tokens)
    token_set: Set[str] = set(tokens)

    found_by_category: Dict[str, Set[str]] = collections.defaultdict(set)

    for term in ALL_TERMS:
        L = len(term.tokens)

        # --- Single-word term ---
        if L == 1:
            if term.tokens[0] in token_set:
                found_by_category[term.category].add(term.norm)
            continue

        # --- Multi-word term (length >= 2): sliding-window search ---
        first_tok = term.tokens[0]

        # Quick skip: if the first token never appears, no match
        if first_tok not in token_set:
            continue

        # Scan tokens and compare slices
        for i in range(token_count - L + 1):
            if tokens[i] != first_tok:
                continue
            if tokens[i:i + L] == term.tokens:
                found_by_category[term.category].add(term.norm)
                break  # no need to keep checking this term in this file

    # Build output preserving original per-category term order
    matches: Dict[str, List[str]] = {}
    for category, ordered_terms in TERMS_BY_CATEGORY.items():
        found_set = found_by_category.get(category)
        if not found_set:
            continue

        ordered = [t for t in ordered_terms if t in found_set]
        if ordered:
            matches[category] = ordered

    return matches


# def search_all_assessment_files_for_keyword_matches():
#     file_data_list = Config.file_data_manager.get_all_file_data()
#     for file_data in file_data_list:
#         file_matches = _find_matches_in_content(file_data.file_content)
#         if file_matches:
#             file_data.keyword_matches = file_matches

def search_all_assessment_files_for_keyword_matches():
    for idx in Config.file_indexes:
        print(f"Finding keyword matches for file: {idx.source_obj.file_path}")
        matches = _find_matches_in_index(idx)
        if matches:
            # assuming source_obj is your FileData instance
            idx.source_obj.keyword_matches = matches


if __name__ == "__main__":
    search_all_assessment_files_for_keyword_matches()