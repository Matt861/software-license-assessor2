import json
from typing import Dict
import requests  # or httpx
from pathlib import Path

p = Path(__file__).resolve()

def download_spdx_license_headers(output_dir_str, licenses_json_path: str) -> None:

    output_dir = Path(output_dir_str)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(licenses_json_path, "r", encoding="utf-8") as f:
        licenses_index = json.load(f)

    headers_by_id: Dict[str, str] = {}

    for lic in licenses_index.get("licenses", []):
        license_id = lic.get("licenseId")
        details_url = lic.get("detailsUrl")
        is_deprecated_license = lic.get("isDeprecatedLicenseId")

        if not license_id or not details_url:
            print(f"Skipping entry with missing licenseId or detailsUrl: {lic}")
            continue

        if is_deprecated_license:
            print(f"Skipping entry because license is deprecated: {lic}")
            continue

        try:
            resp = requests.get(details_url, timeout=10)

            # Handle bad HTTP responses (e.g., 404, 500)
            if not resp.ok:
                print(f"[WARN] {license_id}: bad HTTP status {resp.status_code} for {details_url}")
                continue

            try:
                details = resp.json()
            except ValueError as e:
                print(f"[WARN] {license_id}: invalid JSON from {details_url}: {e}")
                continue

            header = (
                    details.get("standardLicenseHeader")
                    or details.get("standardLicenseHeaderTemplate")
            )

            if header:
                headers_by_id[license_id] = header

                # Make a filesystem-safe filename (just in case)
                safe_name = license_id.replace("/", "_").replace("\\", "_")
                out_path = output_dir / f"{safe_name}.txt"

                try:
                    with out_path.open("w", encoding="utf-8") as out_f:
                        out_f.write(header)
                    print(f"[OK] Wrote header for {license_id} to {out_path}")
                except OSError as e:
                    print(f"[ERROR] {license_id}: failed to write {out_path}: {e}")
            else:
                print(f"[INFO] {license_id}: no standardLicenseHeader or template present")

        except requests.exceptions.Timeout:
            print(f"[ERROR] {license_id}: request to {details_url} timed out")
        except requests.exceptions.RequestException as e:
            # Catches ConnectionError, HTTPError (if raise_for_status used), etc.
            print(f"[ERROR] {license_id}: request failed for {details_url}: {e}")

    # headers_by_id still contains all successfully retrieved headers in memory if you need it

if __name__ == "__main__":
    download_spdx_license_headers("input/license_headers2", "input/licenses.json")