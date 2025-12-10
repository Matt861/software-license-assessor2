import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union, Optional
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import utils

WORD_RE = re.compile(r"\S+")


@dataclass
class FileIndex:
    source_obj: Any  # your model instance for stringA / FileData
    text: str
    tokens: List[Dict]
    trigram_positions: Dict[Tuple[str, str, str], List[int]]


@dataclass
class MatchResult:
    matched_substring: str
    match_percent: float
    start_index: int
    end_index: int
    expected_versions: Optional[List[str]] = None
    found_versions: Optional[List[str]] = None
    license_name: Optional[str] = None


def _ensure_text(value: Union[str, bytes]) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


def _tokenize_with_spans(text: str) -> List[Dict]:
    """
    Tokenize using WORD_RE and record spans. Optimized to minimize
    attribute lookups and repeated name resolution.
    """
    tokens: List[Dict] = []
    append = tokens.append
    finditer = WORD_RE.finditer
    lower = str.lower

    for m in finditer(text):
        word = m.group(0)
        append(
            {
                "word": word,
                "norm": lower(word),
                "start": m.start(),
                "end": m.end(),
            }
        )
    return tokens


def _build_trigram_positions(tokens: List[Dict], anchor_size: int) -> Dict[Tuple[str, str, str], List[int]]:
    """
    Build trigram (or anchor_size-gram) index: (norm1, norm2, norm3) -> [positions].
    Uses pre-extracted norm tokens to reduce per-iteration overhead.
    """
    trigram_positions: Dict[Tuple[str, str, str], List[int]] = defaultdict(list)
    if anchor_size <= 0 or len(tokens) < anchor_size:
        return trigram_positions

    # Pre-extract normalized token strings once
    norms = [t["norm"] for t in tokens]
    n = len(norms)

    if anchor_size == 3:
        # Fast path for the common case of trigrams
        for i in range(n - 2):
            anchor = (norms[i], norms[i + 1], norms[i + 2])
            trigram_positions[anchor].append(i)
    else:
        # Generic n-gram
        for i in range(n - anchor_size + 1):
            anchor = tuple(norms[i : i + anchor_size])
            trigram_positions[anchor].append(i)

    return trigram_positions


def _build_single_file_index(obj: Any, anchor_size: int) -> FileIndex:
    """
    Build a FileIndex for a single object. This is separated so we can
    run it in a ThreadPoolExecutor.
    """

    # If you already have pre-normalized text on the object, reuse it:
    # e.g., obj.normalized_text or obj.indexed_text.
    text = getattr(obj, "file_content_normalized", None)
    if text is not None:
        text = _ensure_text(text)
    else:
        # Fallback: normalize here (this is expensive, so it's worth
        # centralizing if you can).
        raw = _ensure_text(obj.file_content)
        text = utils.remove_punctuation_and_normalize_text(raw)

    tokens = _tokenize_with_spans(text)
    trigram_positions = _build_trigram_positions(tokens, anchor_size)

    return FileIndex(
        source_obj=obj,
        text=text,
        tokens=tokens,
        trigram_positions=trigram_positions,
    )


def build_file_indexes(
    model_objects,          # e.g. Iterable[FileData]
    anchor_size: int = 3,
    max_workers: Optional[int] = None,
) -> List[FileIndex]:
    """
    Build FileIndex objects for all model_objects.

    Performance improvements:
      - Removes per-file print() noise.
      - Reuses pre-normalized text if available (obj.normalized_text).
      - Minimizes overhead in tokenization and trigram-building loops.
      - Uses a ThreadPoolExecutor to parallelize indexing across files.
    """

    objs = list(model_objects)
    if not objs:
        return []

    # Reasonable default for CPU-heavy-ish work (regex, lowercase, etc.)
    if max_workers is None:
        import os
        cpu_count = os.cpu_count() or 4
        max_workers = min(32, cpu_count * 2)

    file_indexes: List[FileIndex] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_build_single_file_index, obj, anchor_size): obj for obj in objs}

        for future in as_completed(futures):
            idx = future.result()
            file_indexes.append(idx)

    return file_indexes
