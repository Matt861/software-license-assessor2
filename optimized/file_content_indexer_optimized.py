import os
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
    source_obj: Any  # your FileData or similar
    text: str
    tokens: List[Dict]
    # Now stores 4-token anchors instead of 3-token trigrams
    trigram_positions: Dict[Tuple[str, str, str, str], List[int]]


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
    Tokenize using WORD_RE and record spans.
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


def _build_anchor_positions(
    tokens: List[Dict],
    anchor_size: int,
) -> Dict[Tuple[str, ...], List[int]]:
    """
    Build anchor_size-gram index: (norm1, ..., normN) -> [positions].

    With anchor_size=4, this becomes a 4-token anchor index.
    """
    positions: Dict[Tuple[str, ...], List[int]] = defaultdict(list)
    if anchor_size <= 0 or len(tokens) < anchor_size:
        return positions

    norms = [t["norm"] for t in tokens]
    n = len(norms)

    if anchor_size == 4:
        # Fast path for 4-token anchors
        for i in range(n - 3):
            anchor = (norms[i], norms[i + 1], norms[i + 2], norms[i + 3])
            positions[anchor].append(i)
    else:
        # Generic N-gram fallback
        for i in range(n - anchor_size + 1):
            anchor = tuple(norms[i : i + anchor_size])
            positions[anchor].append(i)

    return positions


def _build_single_file_index(obj: Any, anchor_size: int) -> FileIndex:
    """
    Build a FileIndex for a single object.
    This is used as the worker for multithreading.
    """

    # If you have pre-normalized text, reuse it:
    # e.g. obj.normalized_text
    text = getattr(obj, "normalized_text", None)
    if text is not None:
        text = _ensure_text(text)
    else:
        raw = _ensure_text(obj.file_content)
        text = utils.remove_punctuation_and_normalize_text(raw)

    tokens = _tokenize_with_spans(text)
    anchor_positions = _build_anchor_positions(tokens, anchor_size)

    # Note: we keep the attribute name trigram_positions for compatibility,
    # even though they are now 4-token anchors.
    return FileIndex(
        source_obj=obj,
        text=text,
        tokens=tokens,
        trigram_positions=anchor_positions,  # 4-gram anchors
    )


def build_file_indexes(
    model_objects,          # e.g. Iterable[FileData]
    anchor_size: int = 4,   # 4-token anchors by default
    max_workers: Optional[int] = None,
) -> List[FileIndex]:
    """
    Build FileIndex objects for all model_objects.

    Performance features:
      - Reuses pre-normalized text if available (obj.normalized_text).
      - Minimizes overhead in tokenization/anchor-building.
      - Uses ThreadPoolExecutor to parallelize indexing across files.
    """
    objs = list(model_objects)
    if not objs:
        return []

    # Reasonable default for CPU-bound-ish work
    if max_workers is None:
        cpu_count = os.cpu_count() or 4
        max_workers = min(32, cpu_count * 2)

    file_indexes: List[FileIndex] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_build_single_file_index, obj, anchor_size): obj
            for obj in objs
        }

        for future in as_completed(futures):
            idx = future.result()
            file_indexes.append(idx)

    return file_indexes
