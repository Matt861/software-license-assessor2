from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


def load_properties(path: Path, encoding: str = "utf-8") -> Dict[str, str]:
    """
    Minimal .properties reader:
      - ignores blank lines and lines starting with # or ;
      - supports key=value and key: value
      - strips surrounding whitespace
      - does not do escape-sequence processing (keeps backslashes as-is)
    """
    props: Dict[str, str] = {}

    with path.open("r", encoding=encoding) as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue

            # split on first '=' or ':' if present
            sep_idx = None
            for sep in ("=", ":"):
                i = line.find(sep)
                if i != -1:
                    sep_idx = i
                    break

            if sep_idx is None:
                continue  # or raise ValueError(f"Invalid line: {raw_line!r}")

            key = line[:sep_idx].strip()
            value = line[sep_idx + 1 :].strip()
            props[key] = value

    return props


def get_bool(props: Dict[str, str], key: str, default: bool = False) -> bool:
    v = props.get(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def get_int(props: Dict[str, str], key: str, default: int = 0) -> int:
    v = props.get(key)
    if v is None:
        return default
    return int(v.strip())


if __name__ == "__main__":
    config_path = Path("config.properties")
    props = load_properties(config_path)

