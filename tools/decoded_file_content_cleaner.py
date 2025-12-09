import re
from configuration import Configuration as Config


# One or more control chars (except \n, \r, \t) → single space
_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]+')

# Optional: literal "\xNN" escape sequences → single space
_HEX_ESCAPE_RE = re.compile(r'(?:\\x[0-9A-Fa-f]{2})+')


def clean_decoded_binary_text(text: str) -> str:
    """
    Replace runs of binary-like/control characters in text with a single space.

    This targets:
      - Actual control characters (NUL, BEL, etc.) in the decoded string.
      - Literal '\\xNN' escape sequences, if they appear as text.

    Newlines and tabs are preserved.
    """
    # Remove actual control characters (not visible but still in the string)
    text = _CONTROL_CHARS_RE.sub(' ', text)

    # If your decoding ever produces literal backslash-x sequences like "\x00"
    # as real characters, this cleans those too.
    text = _HEX_ESCAPE_RE.sub(' ', text)

    return text


def clean_decoded_assessment_files_content():
    for file_data in Config.file_data_manager.get_all_file_data():
        if file_data and file_data.file_content:
            print(f"Cleaning content for file: {file_data.file_path}")
            cleaned_file_content = clean_decoded_binary_text(file_data.file_content)
            file_data.file_content = cleaned_file_content


if __name__ == "__main__":
    clean_decoded_assessment_files_content()