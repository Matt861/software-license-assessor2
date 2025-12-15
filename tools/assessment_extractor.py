import os
import shutil
from pathlib import Path
import zipfile
import tarfile
import gzip
import bz2
import lzma
from loggers.assessment_extractor_logger import assessment_extractor_logger as logger
from configuration import Configuration as Config



# Toggle this to turn noisy debug output on/off
DEBUG = True


def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs, flush=True)


# ---------- Classification helpers ----------

def _looks_like_hex_hash(name: str) -> bool:
    """
    Heuristic: filename looks like a hash (Docker/OCI layers often do this).
    """
    name = name.lower()
    if not (32 <= len(name) <= 128):
        return False
    return all(c in "0123456789abcdef" for c in name)


def _is_image_layer_candidate(path: Path) -> bool:
    """
    Return True iff this hex-looking, extension-less file is *likely* an image
    layer blob, not just some random hex-y filename like .build-id entries.

    We require that some ancestor directory is named 'sha256' (typical for
    Docker/OCI blobs: .../blobs/sha256/<hash> or .../sha256/<hash>).
    """
    if path.suffix != "" or not _looks_like_hex_hash(path.name):
        return False

    for parent in path.parents:
        if parent.name.lower() == "sha256":
            return True
    return False


def is_multi_archive(path: Path) -> bool:
    """
    True if this path should be treated as a multi-file archive.
    """
    name = path.name.lower()

    # Common multi-file archives by extension
    if name.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
        return True
    if path.suffix.lower() in {".zip", ".tar", ".jar"}:
        return True

    # Special rule for .gz:
    #   - name has another extension before .gz -> single-file compression
    #   - otherwise -> treat as multi-file archive (e.g., "compress1.gz")
    if path.suffix.lower() == ".gz" and "." not in path.stem:
        return True

    # Hash-named *image layer* files (no extension, hex name) under a 'sha256' directory
    if _is_image_layer_candidate(path):
        return True

    return False


def is_single_compressed(path: Path) -> bool:
    """
    True if this path is a single-file compressed file.
    """
    suffix = path.suffix.lower()

    if suffix in {".bz2", ".xz", ".lzma"}:
        return True

    if suffix == ".gz":
        # If there's another extension before .gz (e.g. ".txt.gz"), treat as single-file
        return "." in path.stem

    return False


def classify(path: Path) -> str:
    """
    Classify the file:
    - "multi"   -> multi-file archive
    - "single"  -> single-file compression
    - "none"    -> normal file
    """
    if is_multi_archive(path):
        kind = "multi"
    elif is_single_compressed(path):
        kind = "single"
    else:
        kind = "none"

    debug_print(f"[classify] {path} -> {kind}")
    return kind


# ---------- Extraction helpers ----------

def decompress_single(src_file: Path, dest_file: Path) -> None:
    """Decompress single-file compressed src_file to dest_file."""
    debug_print(f"[decompress_single] {src_file} -> {dest_file}")
    dest_file.parent.mkdir(parents=True, exist_ok=True)

    openers = {
        ".gz": gzip.open,
        ".bz2": bz2.open,
        ".xz": lzma.open,
        ".lzma": lzma.open,
    }

    opener = openers.get(src_file.suffix.lower())
    if opener is None:
        print(logger.error(f"Unsupported single-file compression: {src_file}"))
        raise ValueError(f"Unsupported single-file compression: {src_file}")

    with opener(src_file, "rb") as f_in, open(dest_file, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)


def strip_multi_suffix(rel_path: Path) -> Path:
    """
    For multi-file archives, strip the archive extension(s) to get the
    directory name.
    """
    s = str(rel_path)
    lower = s.lower()

    # Compound tar extensions
    for suf in (".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz"):
        if lower.endswith(suf):
            result = Path(s[:-len(suf)])
            debug_print(f"[strip_multi_suffix] {rel_path} -> {result}")
            return result

    # Fallback: remove just the last suffix
    result = rel_path.with_suffix("")
    debug_print(f"[strip_multi_suffix] {rel_path} -> {result}")
    return result


def safe_extract_tar(tar_obj: tarfile.TarFile, path: Path) -> None:
    """
    Safely extract a tarfile to 'path', handling:
    - path traversal protection
    - Windows-invalid filename characters
    - skipping special files (symlinks, devices, FIFOs)
    """
    path = path.resolve()
    invalid_chars = '<>:"|?*' if os.name == "nt" else ""

    debug_print(f"[safe_extract_tar] Extracting to {path}")

    for member in tar_obj.getmembers():
        name = member.name
        if not name:
            continue

        # On Windows, skip names with invalid characters (like ":" in man pages)
        if os.name == "nt" and any(ch in name for ch in invalid_chars):
            logger.info(f"[safe_extract_tar] Skipping invalid Windows name: {name}")
            debug_print(f"[safe_extract_tar] Skipping invalid Windows name: {name}")
            continue

        # Path traversal protection
        member_path = (path / name).resolve()
        if not str(member_path).startswith(str(path)):
            logger.exception(f"Unsafe path in tar archive (path traversal attempt) for path: {path}")
            raise Exception("Unsafe path in tar archive (path traversal attempt)")

        try:
            if member.isdir():
                debug_print(f"[safe_extract_tar] Dir: {member_path}")
                member_path.mkdir(parents=True, exist_ok=True)

            elif member.isreg():
                debug_print(f"[safe_extract_tar] File: {member_path}")
                member_path.parent.mkdir(parents=True, exist_ok=True)
                src_f = tar_obj.extractfile(member)
                if src_f is None:
                    debug_print(f"[safe_extract_tar]   No fileobj for {name}, skipping")
                    continue

                try:
                    with src_f:
                        with open(member_path, "wb") as dst_f:
                            shutil.copyfileobj(src_f, dst_f)
                except (OSError, ValueError) as e:
                    logger.error(f"[safe_extract_tar]   Failed writing {member_path}: {e}")
                    debug_print(f"[safe_extract_tar]   Failed writing {member_path}: {e}")
                    continue

                # Apply basic permissions; ignore failures
                try:
                    os.chmod(member_path, member.mode & 0o777)
                except PermissionError:
                    logger.error(f"[safe_extract_tar]   chmod failed for {member_path}")
                    debug_print(f"[safe_extract_tar]   chmod failed for {member_path}")
                    pass

            else:
                # Skip symlinks, devices, fifos, etc.
                logger.info(f"[safe_extract_tar] Skipping special member: {name}")
                debug_print(f"[safe_extract_tar] Skipping special member: {name}")
                continue

        except (PermissionError, OSError, ValueError) as e:
            logger.error(f"[safe_extract_tar]   Error for {name}: {e}")
            debug_print(f"[safe_extract_tar]   Error for {name}: {e}")
            continue


def safe_extract_zip(zf: zipfile.ZipFile, path: Path) -> None:
    """
    Safe zip extraction with path traversal protection.
    """
    path = path.resolve()
    debug_print(f"[safe_extract_zip] Extracting to {path}")

    for info in zf.infolist():
        if info.is_dir():
            d = (path / info.filename).resolve()
            debug_print(f"[safe_extract_zip] Dir: {d}")
            d.mkdir(parents=True, exist_ok=True)
            continue

        dest = (path / info.filename).resolve()
        if not str(dest).startswith(str(path)):
            logger.exception(f"Unsafe path in zip archive (path traversal attempt) for path: {dest}")
            raise Exception("Unsafe path in zip archive (path traversal attempt)")

        debug_print(f"[safe_extract_zip] File: {dest}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info, "r") as src, open(dest, "wb") as dst:
            shutil.copyfileobj(src, dst)


def _finalize_extract_dir(extract_dir: Path, final_dir: Path) -> None:
    """
    Finalize an extraction directory:

    - If extract_dir == final_dir: nothing extra to do.
    - Otherwise:
        * remove any existing file/dir at final_dir
        * rename/move extract_dir to final_dir

    After this, there should be NO lingering '*_extracted' dirs.
    """
    if extract_dir == final_dir:
        debug_print(f"[finalize] extract_dir == final_dir == {final_dir}, nothing to do")
        return

    debug_print(f"[finalize] Moving {extract_dir} -> {final_dir}")
    if final_dir.exists():
        if final_dir.is_file():
            debug_print(f"[finalize] Removing file {final_dir}")
            final_dir.unlink()
        elif final_dir.is_dir():
            debug_print(f"[finalize] Removing dir {final_dir}")
            shutil.rmtree(final_dir)

    # Now move/rename the extracted directory into place
    extract_dir.rename(final_dir)


def extract_multi(src_file: Path, dest_root: Path, rel_path: Path) -> None:
    """
    Extract a multi-file archive.

    - Normal archives: .zip, .tar, .tar.gz, etc.
    - Hash-named image layers (no extension, hex name under sha256): treated
      as tar streams via tarfile.open(..., "r:*") directly.
    """
    debug_print(f"[extract_multi] {src_file} (rel={rel_path})")
    default_dir_rel = strip_multi_suffix(rel_path)
    base_name = default_dir_rel.name

    archive_src = src_file  # works for normal archives and layer blobs

    # ZIP?
    if zipfile.is_zipfile(archive_src):
        debug_print(f"[extract_multi] ZIP archive detected: {archive_src}")
        with zipfile.ZipFile(archive_src, "r") as zf:
            names = [i.filename for i in zf.infolist() if i.filename]
            top_levels = set(
                n.split("/", 1)[0].rstrip("/")
                for n in names
                if n and not n.startswith("__MACOSX")
            )

            target_dir_rel = default_dir_rel
            if len(top_levels) == 1:
                only = next(iter(top_levels))
                if only == base_name:
                    debug_print("[extract_multi] Flattening ZIP top-level dir")
                    target_dir_rel = default_dir_rel.parent

            target_dir_candidate = dest_root / target_dir_rel

            # In-place case: file path == dir path
            if src_file.resolve() == target_dir_candidate.resolve():
                extract_dir = target_dir_candidate.with_name(
                    target_dir_candidate.name + "_extracted"
                )
                final_dir = target_dir_candidate
            else:
                extract_dir = target_dir_candidate
                final_dir = target_dir_candidate

            extract_dir.mkdir(parents=True, exist_ok=True)
            safe_extract_zip(zf, extract_dir)
        _finalize_extract_dir(extract_dir, final_dir)
        return

    # TAR (covers .tar, .tar.gz, and hash layer blobs)
    try:
        debug_print(f"[extract_multi] Trying TAR: {archive_src}")
        with tarfile.open(archive_src, mode="r:*") as tf:
            names = [m.name for m in tf.getmembers() if m.name]
            top_levels = set(
                n.split("/", 1)[0].rstrip("/")
                for n in names
                if n and n not in (".", "/")
            )

            target_dir_rel = default_dir_rel
            if len(top_levels) == 1:
                only = next(iter(top_levels))
                if only == base_name:
                    debug_print("[extract_multi] Flattening TAR top-level dir")
                    target_dir_rel = default_dir_rel.parent

            target_dir_candidate = dest_root / target_dir_rel

            if src_file.resolve() == target_dir_candidate.resolve():
                # Hash-layer in-place: extract to temp dir, then replace the file.
                extract_dir = target_dir_candidate.with_name(
                    target_dir_candidate.name + "_extracted"
                )
                final_dir = target_dir_candidate
            else:
                extract_dir = target_dir_candidate
                final_dir = target_dir_candidate

            extract_dir.mkdir(parents=True, exist_ok=True)
            safe_extract_tar(tf, extract_dir)
        _finalize_extract_dir(extract_dir, final_dir)
        return

    except (tarfile.ReadError, OSError, FileNotFoundError) as e:
        logger.error(f"[extract_multi] Not a TAR or error reading {archive_src}: {e}")
        debug_print(f"[extract_multi] Not a TAR or error reading {archive_src}: {e}")

    # Fallback: treat as plain file
    dest_file = dest_root / rel_path
    if dest_file != src_file:
        debug_print(f"[extract_multi] Fallback copy {src_file} -> {dest_file}")
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest_file)


# ---------- Copy / nested extraction pipeline ----------

def copy_or_extract_file(src_file: Path, dest_root: Path, rel_path: Path) -> None:
    """
    Handle a single file during the initial copy phase.
    """
    if not src_file.is_file():
        return

    kind = classify(src_file)

    if kind == "none":
        dest_file = dest_root / rel_path
        debug_print(f"[copy_or_extract] Copy (none): {src_file} -> {dest_file}")
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest_file)

    elif kind == "single":
        dest_rel = rel_path.with_suffix("")  # drop only final extension
        dest_file = dest_root / dest_rel
        debug_print(f"[copy_or_extract] Decompress (single): {src_file} -> {dest_file}")
        decompress_single(src_file, dest_file)

    else:  # "multi"
        debug_print(f"[copy_or_extract] Extract (multi): {src_file}")
        extract_multi(src_file, dest_root, rel_path)


def copy_tree_with_extraction(src: Path, dest_root: Path) -> None:
    """
    Copy a directory from src to dest_root, extracting archives/compressed files
    encountered in src.
    """
    if not src.is_dir():
        logger.error(f"Source {src} is not a directory")
        raise ValueError(f"Source {src} is not a directory")

    debug_print(f"[copy_tree_with_extraction] Walking {src}")
    for dirpath, dirnames, filenames in os.walk(src):
        dirpath = Path(dirpath)
        rel_dir = dirpath.relative_to(src)
        debug_print(f"[copy_tree_with_extraction] Dir: {dirpath}, rel={rel_dir}")

        for filename in filenames:
            src_file = dirpath / filename

            if rel_dir == Path("."):
                rel_path = Path(filename)
            else:
                rel_path = rel_dir / filename

            debug_print(f"[copy_tree_with_extraction] File: {src_file}, rel={rel_path}")
            copy_or_extract_file(src_file, dest_root, rel_path)


def extract_nested_archives(dest_root: Path) -> None:
    """
    Repeatedly scan dest_root for archive/compressed files and extract them
    in-place until no more remain.

    Each physical file path is processed at most once.
    """
    processed = set()  # resolved absolute paths we've already processed
    pass_num = 0

    while True:
        pass_num += 1
        debug_print(f"[extract_nested_archives] Pass {pass_num} starting")
        changed = False

        for dirpath, dirnames, filenames in os.walk(dest_root):
            dirpath = Path(dirpath)

            for filename in filenames:
                abs_path = dirpath / filename

                # Resolve to a canonical key; skip if we can't resolve
                try:
                    key = str(abs_path.resolve())
                except FileNotFoundError:
                    logger.error(f"Failed to resolve path to a canonical key for path: {abs_path}")
                    continue

                # Don't process same file path more than once across passes
                if key in processed:
                    continue

                processed.add(key)

                if not abs_path.is_file():
                    continue

                kind = classify(abs_path)
                if kind == "none":
                    continue

                rel_path = abs_path.relative_to(dest_root)
                debug_print(f"[extract_nested_archives] {kind} -> {abs_path}")

                if kind == "single":
                    dest_rel = rel_path.with_suffix("")
                    dest_file = dest_root / dest_rel
                    decompress_single(abs_path, dest_file)
                    if abs_path.exists() and abs_path.is_file():
                        try:
                            debug_print(f"[extract_nested_archives] unlink {abs_path}")
                            abs_path.unlink()
                        except PermissionError as e:
                            logger.error(f"[extract_nested_archives] unlink failed: {e}")
                            debug_print(f"[extract_nested_archives] unlink failed: {e}")
                    changed = True

                else:  # "multi"
                    extract_multi(abs_path, dest_root, rel_path)
                    if abs_path.exists() and abs_path.is_file():
                        try:
                            debug_print(f"[extract_nested_archives] unlink {abs_path}")
                            abs_path.unlink()
                        except PermissionError as e:
                            logger.error(f"[extract_nested_archives] unlink failed: {e}")
                            debug_print(f"[extract_nested_archives] unlink failed: {e}")
                    changed = True

        debug_print(f"[extract_nested_archives] Pass {pass_num} changed={changed}")
        if not changed:
            break


# ---------- CLI ----------
def create_assessment_from_source(source_project_dir, dest_assessment_dir) -> None:

    logger.info(
        "Path check | path=%s exists=%s is_dir=%s is_file=%s",
        source_project_dir,
        source_project_dir.exists(),
        source_project_dir.is_dir(),
        source_project_dir.is_file(),
    )

    if source_project_dir.is_dir():
        # Normal directory: copy + first-level extraction, then nested extraction
        copy_tree_with_extraction(source_project_dir, dest_assessment_dir)
        #rel_path = Path(source_dir.name)
        #target_dir_rel = strip_multi_suffix(rel_path)
        #target_dir = dest_dir / target_dir_rel
        # Second phase: extract all nested archives/compressed files in-place
        extract_nested_archives(dest_assessment_dir)

    elif source_project_dir.is_file():
        # Top-level is a single file (could be archive/compressed/normal):
        # Treat it as if it were a file inside a virtual root and process it,
        # then run nested extraction on whatever it produced.
        rel_path = Path(source_project_dir.name)
        copy_or_extract_file(source_project_dir, dest_assessment_dir, rel_path)
        #target_dir_rel = strip_multi_suffix(rel_path)
        #target_dir = dest_assessment_dir / target_dir_rel
        # Second phase: extract all nested archives/compressed files in-place
        extract_nested_archives(dest_assessment_dir)

    else:
        logger.error(f"Source path {source_project_dir} is neither a file nor a directory")
        raise ValueError(f"Source path {source_project_dir} is neither a file nor a directory")

    # Second phase: extract all nested archives/compressed files in-place
    # extract_nested_archives(dest_dir)


if __name__ == "__main__":
    Config.dest_dir.mkdir(parents=True, exist_ok=True)
    create_assessment_from_source(Config.source_dir, Config.dest_dir)
