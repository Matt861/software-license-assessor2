from timer import Timer
import os
import json
import re
from typing import Union
import requests
import unicodedata

def normalize_for_compare(value: Union[str, bytes, None]) -> str:
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


# Raw JSON of licenses.json in the SPDX repo
LICENSES_JSON_URL = (
    "https://raw.githubusercontent.com/spdx/license-list-data/main/json/licenses.json"
)

def download_all_spdx_licenses(output_dir: str, licenses_json_path: str) -> None:
    """
    Download all SPDX license texts by following each license's detailsUrl
    and using the 'licenseText' field from the JSON.

    If licenses_json_path is provided, read licenses.json from disk.
    Otherwise, fetch it from GitHub.
    """
    os.makedirs(output_dir, exist_ok=True)

    total_count = 0
    downloaded_count = 0
    no_license_text_count = 0
    error_fetching_count = 0
    error_writing_count = 0
    failed_to_download_license_list = []

    # Load licenses.json (from disk or from the web)
    if licenses_json_path is None:
        resp = requests.get(LICENSES_JSON_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    else:
        with open(licenses_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    licenses = data.get("licenses", [])

    for lic in licenses:
        total_count += 1
        license_id = lic.get("licenseId")
        details_url = lic.get("detailsUrl")
        is_deprecated_license = lic.get("isDeprecatedLicenseId")

        if not license_id or not details_url:
            continue

        if is_deprecated_license:
            print(f"Skipping entry because license is deprecated: {lic}")
            continue

        try:
            # Fetch the details JSON for this license
            r = requests.get(details_url, timeout=30)
            r.raise_for_status()
            details = r.json()
        except Exception as e:
            error_fetching_count += 1
            failed_to_download_license_list.append(license_id)
            print(f"Error fetching details for {license_id} at {details_url}: {e}")
            continue

        license_text = details.get("licenseText")
        license_text = normalize_for_compare(license_text)
        if not license_text:
            no_license_text_count += 1
            failed_to_download_license_list.append(license_id)
            print(f"No licenseText found for {license_id} at {details_url}")
            continue

        out_path = os.path.join(output_dir, f"{license_id}.txt")

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(license_text)
            downloaded_count += 1
            print(f"Saved {license_id} -> {out_path}")
        except Exception as e:
            error_writing_count += 1
            failed_to_download_license_list.append(license_id)
            print(f"Error writing {out_path}: {e}")

    print(f"{"Total license count: "}{total_count}")
    print(f"{"Downloaded count: "}{downloaded_count}")
    print(f"{"No license text count: "}{no_license_text_count}")
    print(f"{"Error fetching count: "}{error_fetching_count}")
    print(f"{"Error writing count: "}{error_writing_count}")
    print("License(s) that failed to download: ")
    for failed_license in failed_to_download_license_list:
        print(failed_license)


if __name__ == "__main__":
    # If you already have licenses.json locally, pass its path:
    # download_all_spdx_licenses(
    #     output_dir="spdx_licenses_from_details",
    #     licenses_json_path="licenses.json",
    # )
    timer = Timer()
    timer.start("Starting SPDX license downloader timer")
    download_all_spdx_licenses("input/licenses2", "input/licenses.json")
    timer.stop("Stopping SPDX license downloader timer")
    print(timer.elapsed())
