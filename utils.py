import os
import re
import string
from pathlib import Path
from typing import Optional, List, Dict, Union

import unicodedata


def get_file_extension(path_or_filename):
    base = os.path.basename(path_or_filename)
    if base.startswith('.') and base.count('.') == 1:
        return base.lower()
    ext = os.path.splitext(base)[1]
    return ext.lower() if ext else base.lower()


def to_text(content: Union[str, bytes]) -> str:
    """
    Ensure we are working with a text string.
    If content is bytes, decode as UTF-8 (ignoring errors).
    """
    if isinstance(content, str):
        return content
    return content.decode("utf-8", errors="ignore")


def get_file_name_from_path_without_extension(path: Path) -> str:
    """
    Strip everything before the last path separator and remove the file extension.
    Works with both '\\' and '/' as separators.
    """
    # Get the last part after any slash or backslash
    filename = re.split(r"[\\/]", str(path))[-1]

    # Strip the extension
    name_without_ext, _ = os.path.splitext(filename)

    # Strip _v1, _v2, etc
    name_without_ext = name_without_ext.split("_", 1)[0]

    return name_without_ext


def extract_versions_from_name(name: str) -> Optional[List[str]]:
    """
    Extract all numbers (like 2, 2.0, 2.1) from a file name.

    Examples:
        "ECL-2.0.txt"                 -> ["2.0"]
        "ECL-2.1.txt"                 -> ["2.1"]
        "ECL-2.txt"                   -> ["2"]
        "LGPL-2.0-or-later.txt"       -> ["2.0"]
        "APL-2.0-GPL-3.0.txt"         -> ["2.0", "3.0"]
    """
    # Ensure we're only working with the file name (no directories)
    name = Path(name).name

    # Find all sequences of digits, optionally followed by .digits
    versions = re.findall(r'\d+(?:\.\d+)?', name)
    return versions


def normalize_number_strings(values: Optional[List[str]]) -> list[str] | None:
    """
    Take a numeric string like "2", "2.1", "10", "-3", etc.

    - If it's an int (e.g. "2", "3", "10", "-3"), return it as "<int>.0"
      e.g. "2" -> "2.0", "-3" -> "-3.0"
    - Otherwise, return the original string unchanged
      e.g. "2.1" -> "2.1", "2.0" -> "2.0"
    - If value is None, return None
    """
    if values is None:
        return None

    normalized_strings = []

    for value in values:

        s = value.strip()

        # Match an optional sign followed by digits only (no decimal point)
        if re.fullmatch(r'[+-]?\d+', s):
            normalized_strings.append(f"{int(s)}.0")
            #return f"{int(s)}.0"
        else:
            normalized_strings.append(s)
            #return s
    return normalized_strings


def remove_punctuation_keep_decimal_dots(text: str) -> str:
    """
    Remove all punctuation from `text`, except for '.' characters that are part
    of numbers or version-like tokens (i.e., a '.' with digits on both sides,
    such as in '1.0' or '1.0.0').

    Also handles LaTeX-style escaped sequences like '\\&.' so that
    '2\\&.0\\&.' becomes '2.0'.
    """
    # Normalize '\&.' sequences to a plain dot
    # "v\\&. 2\\&.0\\&." -> "v. 2.0."
    text = re.sub(r'\\&\.', '.', text)

    punctuation = set(string.punctuation)
    result_chars = []
    n = len(text)

    for i, ch in enumerate(text):
        # Not punctuation? Always keep it.
        if ch not in punctuation:
            result_chars.append(ch)
            continue

        # Special handling for dots
        if ch == '.':
            prev_ch = text[i - 1] if i > 0 else ''
            next_ch = text[i + 1] if i + 1 < n else ''

            # Keep '.' only if it's between digits (e.g., 1.0, 1.0.0)
            if prev_ch.isdigit() and next_ch.isdigit():
                result_chars.append(ch)
            # else: skip this dot
            continue

        # Any other punctuation: remove it (skip)
        continue

    return ''.join(result_chars)


def remove_punctuation_and_normalize_text(value: Union[str, bytes, None]) -> str:
    """
    Normalize a string for comparison:
      - Handles None and bytes
      - Unicode normalizes (NFKC)
      - Strips accents/diacritics
      - Case-insensitive (casefold)
      - Collapses whitespace to single spaces
    Returns a normalized string.
    """
    if value is None:
        return ""

    # Decode bytes if needed
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")

    # Ensure it's a string
    value = str(value)

    value = remove_punctuation_keep_decimal_dots(value)

    # Normalize Unicode (compatibility decomposition + recomposition)
    value = unicodedata.normalize("NFKC", value)

    # Remove diacritics (accents)
    # e.g., "café" → "cafe"
    value = "".join(
        ch for ch in value
        if not unicodedata.category(ch).startswith("M")
    )

    # Case-insensitive
    value = value.casefold()

    # Collapse any whitespace (spaces, tabs, newlines) into a single space
    value = re.sub(r"\s+", " ", value)

    # Strip leading/trailing spaces
    return value.strip()


def load_file_contents_from_directory(license_dirs: List[Path]) -> Dict[Path, str]:
    licenses: Dict[Path, str] = {}

    for base_dir in license_dirs:
        if not os.path.isdir(base_dir):
            print(f"Warning: pattern directory does not exist or is not a directory: {base_dir}")
            continue

        for dirpath, dirnames, filenames in os.walk(base_dir):
            for filename in filenames:
                if not filename.lower().endswith(".txt"):
                    continue

                license_path = Path(dirpath, filename).resolve()

                print(f"Reading license: {license_path}")

                try:
                    with open(license_path, "r", encoding="utf-8") as f:
                        raw_text = f.read()
                except Exception as e:
                    print(f"Could not read pattern file {license_path}: {e}")
                    continue

                license_text = raw_text.strip()  # ignore extra whitespace before/after

                if not license_text:
                    # Skip completely empty patterns
                    continue

                licenses[license_path] = license_text

    return licenses


def read_and_normalize_licenses(license_dirs: List[Path]):
    licenses = load_file_contents_from_directory(license_dirs)

    # Pre-normalize all patterns once
    licenses_normalized: Dict[Path, str] = {
        path: remove_punctuation_and_normalize_text(text)
        for path, text in licenses.items()
    }

    return licenses_normalized


def get_source_project_dir(source_dir, source_project_name, source_dir_is_network):
    if source_dir_is_network == "True":
        source_dir = source_dir.replace("/", "\\")
        source_project_dir = source_dir + "\\" + source_project_name
    else:
        source_project_dir = source_dir + "/" + source_project_name

    return Path(source_project_dir)


def get_dest_assessment_dir(dest_dir, assessment_name, dest_dir_is_network):
    if dest_dir_is_network == "True":
        source_dir = dest_dir.replace("/", "\\")
        dest_assessment_dir = source_dir + "\\" + assessment_name
    else:
        dest_assessment_dir = dest_dir + "/" + assessment_name

    return Path(dest_assessment_dir)

