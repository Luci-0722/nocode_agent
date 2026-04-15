from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from nocode_agent.app import backend_stdio
from nocode_agent.config import list_available_models, load_global_config, save_global_default_model


class ModelDefaultConfigTest(unittest.TestCase):
    def test_list_available_models_marks_only_exact_default(self) -> None:
        config = {
            "default_model": "qwen/glm-4-flash",
            "models": {
                "qwen": {
                    "model": "glm-5",
                    "variants": ["glm-4-flash", "glm-4-air"],
                },
                "claude": {
                    "model": "claude-sonnet-4",
                },
            },
        }

        models = {item["name"]: item["is_default"] for item in list_available_models(config)}

        self.assertEqual(models["qwen"], "false")
        self.assertEqual(models["qwen/glm-4-flash"], "true")
        self.assertEqual(models["qwen/glm-4-air"], "false")
        self.assertEqual(models["claude"], "false")

    def test_global_default_model_is_loaded_from_home_config(self) -> None:
        config = {
            "default_model": "qwen",
            "models": {
                "qwen": {"model": "glm-5"},
                "claude": {"model": "claude-sonnet-4"},
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"HOME": temp_dir}, clear=False):
                save_global_default_model("claude")
                self.assertEqual(load_global_config().get("default_model"), "claude")
                self.assertEqual(backend_stdio._resolve_initial_model_name(config), "claude")

    def test_explicit_model_override_beats_home_default(self) -> None:
        config = {
            "default_model": "qwen",
            "models": {
                "qwen": {"model": "glm-5"},
                "claude": {"model": "claude-sonnet-4"},
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(
                os.environ,
                {"HOME": temp_dir, "NOCODE_MODEL_NAME": "qwen"},
                clear=False,
            ):
                save_global_default_model("claude")
                self.assertEqual(backend_stdio._resolve_initial_model_name(config), "qwen")
