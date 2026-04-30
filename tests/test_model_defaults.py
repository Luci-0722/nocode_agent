from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from nocode_agent.app import backend_stdio
from nocode_agent.config import load_global_config, save_global_default_model, parse_model_name


class ModelDefaultConfigTest(unittest.TestCase):
    def test_parse_model_name_splits_correctly(self) -> None:
        provider, model_id = parse_model_name("glm/glm-5.1")
        self.assertEqual(provider, "glm")
        self.assertEqual(model_id, "glm-5.1")

    def test_parse_model_name_rejects_invalid_format(self) -> None:
        with self.assertRaises(ValueError):
            parse_model_name("invalid-no-slash")

    def test_parse_model_name_rejects_empty_parts(self) -> None:
        with self.assertRaises(ValueError):
            parse_model_name("/model-id")
        with self.assertRaises(ValueError):
            parse_model_name("provider/")

    def test_global_default_model_is_loaded_from_home_config(self) -> None:
        config = {
            "default_model": "qwen/glm-5",
            "providers": {
                "qwen": {"base_url": "http://127.0.0.1:11434/v1"},
                "claude": {"base_url": "https://api.anthropic.com"},
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"HOME": temp_dir}, clear=False):
                save_global_default_model("claude/claude-sonnet-4")
                self.assertEqual(load_global_config().get("default_model"), "claude/claude-sonnet-4")
                self.assertEqual(backend_stdio._resolve_initial_model_name(config), "claude/claude-sonnet-4")

    def test_explicit_model_override_beats_home_default(self) -> None:
        config = {
            "default_model": "qwen/glm-5",
            "providers": {
                "qwen": {"base_url": "http://127.0.0.1:11434/v1"},
                "claude": {"base_url": "https://api.anthropic.com"},
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(
                os.environ,
                {"HOME": temp_dir, "NOCODE_MODEL_NAME": "qwen/glm-5"},
                clear=False,
            ):
                save_global_default_model("claude/claude-sonnet-4")
                self.assertEqual(backend_stdio._resolve_initial_model_name(config), "qwen/glm-5")

    def test_resolve_initial_falls_back_to_first_provider(self) -> None:
        config = {
            "providers": {
                "glm": {"base_url": "https://open.bigmodel.cn/api/paas/v4"},
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.dict(os.environ, {"HOME": temp_dir}, clear=False):
                result = backend_stdio._resolve_initial_model_name(config)
                self.assertEqual(result, "glm/unknown")
