import hashlib
import os
from pathlib import Path
from typing import Iterable, Optional

def sha256_of_directory(
    root_dir: str | Path,
    exclude: Optional[Iterable[str | Path]] = None,
) -> str:
    root_dir = Path(root_dir).resolve()
    exclude_paths = set()

    # Normalize exclude paths to absolute Paths under root_dir
    if exclude:
        for p in exclude:
            p = Path(p)
            # If relative, treat as inside root_dir
            if not p.is_absolute():
                p = root_dir / p
            exclude_paths.add(p.resolve())

    def is_excluded(path: Path) -> bool:
        # Exclude if the file/dir *is* an excluded path or is inside one
        return any(path == ex or ex in path.parents for ex in exclude_paths)

    hasher = hashlib.sha256()

    # Collect all files we will include, with stable ordering by relative path
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirpath = Path(dirpath)

        # Optionally trim excluded dirs from traversal early for speed
        dirnames[:] = [
            d for d in dirnames
            if not is_excluded((dirpath / d).resolve())
        ]

        for fname in filenames:
            fpath = (dirpath / fname).resolve()
            if is_excluded(fpath):
                continue
            files.append(fpath)

    files.sort(key=lambda p: str(p.relative_to(root_dir)).replace(os.sep, "/"))

    # Feed each file's relative path and contents into the hasher
    for fpath in files:
        rel = str(fpath.relative_to(root_dir)).replace(os.sep, "/")
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\0")  # delimiter between path and content

        with fpath.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)

    return hasher.hexdigest()


# Hash of folder A as-is
hash_with_all = sha256_of_directory("Folder_A")

# Hash of folder A *as if C did not exist inside it*
exclusive_hash = sha256_of_directory("Folder_A", exclude=["Folder_C"])

print("With:     ", hash_with_all)
print("Without:  ", exclusive_hash)
