import tomllib
import unittest
from pathlib import Path


class ConfigTemplatesTest(unittest.TestCase):
    def test_public_templates_use_current_route_folders(self):
        root = Path(__file__).resolve().parents[1]
        expected = [
            "AI学习",
            "考研资料汇总",
            "炒股与量化学习",
            "研后/英语学习",
            "工作",
            "Life",
            "Inbox/Learning Inbox",
        ]

        for name in ["config.example.toml", "config.docker.toml"]:
            with self.subTest(name=name):
                data = tomllib.loads((root / name).read_text(encoding="utf-8"))
                folders = data["routing"]["allowed_folders"]

                self.assertEqual(folders, expected)
                self.assertNotIn("英语学习", folders)
                self.assertNotIn("毕业前的30件事", folders)
                self.assertEqual(data["outputs"]["formats"], ["markdown"])
                self.assertIn("html_dir", data["outputs"])
                self.assertIn("csv_path", data["outputs"])
                self.assertIn("notion_database_id", data["outputs"])


if __name__ == "__main__":
    unittest.main()
