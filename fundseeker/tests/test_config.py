import os
import unittest
from pathlib import Path

from src.utils.config import AppConfig, load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_defaults(self) -> None:
        cfg = load_config()
        self.assertIsInstance(cfg, AppConfig)
        self.assertTrue(cfg.paths.output_dir.is_absolute())
        self.assertTrue(cfg.paths.logs_dir.is_absolute())
        self.assertTrue(cfg.paths.data_dir.is_absolute())
        self.assertTrue(str(cfg.paths.default_fund_list).endswith("data/fund_list.csv"))
        self.assertGreater(cfg.settings.batch_size, 0)

    def test_env_override(self) -> None:
        custom_dir = Path.cwd() / "tmp-output"
        os.environ["FUNDSEEKER_OUTPUT_DIR"] = str(custom_dir)
        cfg = load_config()
        self.assertEqual(cfg.paths.output_dir, custom_dir.resolve())
        del os.environ["FUNDSEEKER_OUTPUT_DIR"]


if __name__ == "__main__":
    unittest.main()
