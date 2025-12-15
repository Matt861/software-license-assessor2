import unittest
from typing import Union
import utils
from configuration import Configuration as Config
from models.FileData import FileDataManager
from pathlib import Path

p = Path(__file__).resolve()

class TestTemplate(unittest.TestCase):


    def test_test(self):
        Config.file_data_manager = FileDataManager()
        dir_path = Path(Config.root_dir, Config.spdx_license_headers_dir, "GPL-2.0-only.txt").resolve()
        if dir_path.is_file():
            try:
                # Try reading as text
                with open(dir_path, "r", encoding="utf-8") as f:
                    content: Union[str, bytes] = f.read()
            except UnicodeDecodeError:
                # Fallback to binary
                with open(dir_path, "rb") as f:
                    content = f.read()
            except Exception as e:
                print(f"Could not read {dir_path}: {e}")

            if content:
                print(f"File: {dir_path}")
                content = utils.remove_punctuation_and_normalize_text(content)
                print(content)



if __name__ == "__main__":
    unittest.main()