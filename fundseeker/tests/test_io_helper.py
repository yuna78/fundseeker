import tempfile
import unittest
from pathlib import Path

from src.utils.io_helper import build_output_path, ensure_daily_dir


class IoHelperTests(unittest.TestCase):
    def test_ensure_daily_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            day_dir = ensure_daily_dir(base, "2099-01-01")
            self.assertTrue(day_dir.exists())
            self.assertTrue(day_dir.name, "2099-01-01")

    def test_build_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            path = build_output_path(base, "demo", ".txt")
            self.assertTrue(path.parent.exists())
            self.assertTrue(path.name.startswith("demo_"))
            self.assertTrue(path.name.endswith(".txt"))


if __name__ == "__main__":
    unittest.main()
