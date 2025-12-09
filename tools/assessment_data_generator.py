import csv
import os.path
from pathlib import Path
from configuration import Configuration as Config


def write_license_data_to_csv(csv_name):
    """
    Create a CSV file with headers 'File Name' and 'License' and
    write one row per object in the given list.

    Each object is expected to have either:
      - attributes: file_name, license
      - or dictionary keys: 'file_name', 'license'
    """
    csv_path = Path(Config.output_dir, csv_name).resolve()
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header row, ADD STATUS TO THIS (PERMISSIBLE/IMPERMISSIBLE
        writer.writerow(["File Name", "License", "Match %", "Fuzzy Licenses", "Full License",
                         "Is Released", "Is Empty", "Keywords", "Hash"])

        # Write data rows
        for file_data in Config.file_data_manager.get_all_file_data():
            if file_data.file_path:
                p = Path(file_data.file_path)

                # Excel likes file:// URLs; convert Windows backslashes to forward slashes
                url = "file:///" + str(p).replace("\\", "/")

                # What the cell visibly shows (just the file name portion)
                display_text = p.name

                # Excel hyperlink formula
                file_cell = f'=HYPERLINK("{url}", "{display_text}")'
            else:
                file_cell = ""

            if file_data.fuzzy_license_match:
                fuzzy_license_match = file_data.fuzzy_license_match
                writer.writerow([file_cell, file_data.license_names,
                                 fuzzy_license_match.match_percent, fuzzy_license_match.license_name,
                                 file_data.has_full_license, file_data.is_released, file_data.file_is_empty,
                                 file_data.keyword_matches, file_data.file_hash])
            else:
                writer.writerow([file_cell, file_data.license_names, "", "",
                                 file_data.has_full_license, file_data.is_released, file_data.file_is_empty,
                                 file_data.keyword_matches, file_data.file_hash])
