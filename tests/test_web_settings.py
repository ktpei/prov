import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from provenance.web.__main__ import load_env
from provenance.web.settings import CONFIG_PATH, SETTINGS, load_settings


class SettingsTests(unittest.TestCase):
    def test_local_credentials_override_stale_inherited_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("OPENROUTER_API_KEY=current-test-key\nEXA_API_KEY=current-exa\n")
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": "stale-test-key"}):
                load_env(path)
                self.assertEqual(os.environ["OPENROUTER_API_KEY"], "current-test-key")
                self.assertEqual(os.environ["EXA_API_KEY"], "current-exa")

    def test_config_overrides_stale_settings_but_preserves_credentials(self):
        with patch.dict(
            os.environ, {"OPENROUTER_API_KEY": "test-secret", "WEB_MAX_TURN_USD": "99"}
        ):
            config = load_settings()
            self.assertEqual(os.environ["OPENROUTER_API_KEY"], "test-secret")
            self.assertEqual(os.environ["WEB_MAX_TURN_USD"], str(config["max_turn_usd"]))
            self.assertEqual(os.environ["OPENROUTER_MODEL"], config["model"])

    def test_invalid_config_does_not_partially_change_environment(self):
        original = json.loads(CONFIG_PATH.read_text())
        for key, value in [
            ("model", ""),
            ("max_turn_usd", -1),
            ("total_spend_usd", "nan"),
            ("OPENROUTER_API_KEY", "must-not-be-here"),
        ]:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                config = {**original, key: value}
                path = Path(directory) / "config.json"
                path.write_text(json.dumps(config))
                with patch.dict(os.environ, {name: "unchanged" for name in SETTINGS.values()}):
                    with self.assertRaises(ValueError):
                        load_settings(path)
                    self.assertTrue(
                        all(os.environ[name] == "unchanged" for name in SETTINGS.values())
                    )
