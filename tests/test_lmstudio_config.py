from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lmstudio_config import CHAT_READINESS_PROMPT
from lmstudio_config import get_lmstudio_settings
from lmstudio_config import normalize_base_url
from lmstudio_config import require_lmstudio_ready
from lmstudio_config import response_to_text
from support import CHAT_MODEL
from support import EMBEDDING_MODEL
from support import MockLMStudioServer


class LMStudioConfigTests(unittest.TestCase):
    def test_normalize_base_url_accepts_bare_server_url(self):
        self.assertEqual(
            normalize_base_url("http://127.0.0.1:1234"),
            "http://127.0.0.1:1234/v1",
        )
        self.assertEqual(
            normalize_base_url("http://127.0.0.1:1234/"),
            "http://127.0.0.1:1234/v1",
        )
        self.assertEqual(
            normalize_base_url("http://127.0.0.1:1234/v1"),
            "http://127.0.0.1:1234/v1",
        )

    def test_get_settings_reads_lmstudio_environment(self):
        env = {
            "LMSTUDIO_BASE_URL": "http://127.0.0.1:1234",
            "LMSTUDIO_API_KEY": "test-key",
            "LMSTUDIO_CHAT_MODEL": CHAT_MODEL,
            "LMSTUDIO_EMBEDDING_MODEL": EMBEDDING_MODEL,
            "LMSTUDIO_MAX_TOKENS": "256",
            "LMSTUDIO_TEMPERATURE": "0.2",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = get_lmstudio_settings()

        self.assertEqual(settings.base_url, "http://127.0.0.1:1234/v1")
        self.assertEqual(settings.api_key, "test-key")
        self.assertEqual(settings.chat_model, CHAT_MODEL)
        self.assertEqual(settings.embedding_model, EMBEDDING_MODEL)
        self.assertEqual(settings.max_tokens, 256)
        self.assertEqual(settings.temperature, 0.2)

    def test_get_settings_requires_model_names(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "LMSTUDIO_CHAT_MODEL"):
                get_lmstudio_settings()

    def test_response_to_text_handles_common_langchain_shapes(self):
        class Response:
            content = [{"text": "hello"}, {"text": "world"}]

        self.assertEqual(response_to_text("  hello  "), "hello")
        self.assertEqual(response_to_text(Response()), "hello\nworld")
        self.assertEqual(response_to_text(None), "")

    def test_require_lmstudio_ready_checks_embeddings_and_chat(self):
        with MockLMStudioServer() as server:
            env = {
                "LMSTUDIO_BASE_URL": server.base_url,
                "LMSTUDIO_CHAT_MODEL": CHAT_MODEL,
                "LMSTUDIO_EMBEDDING_MODEL": EMBEDDING_MODEL,
            }
            with patch.dict(os.environ, env, clear=True):
                settings = require_lmstudio_ready()

        self.assertEqual(settings.chat_model, CHAT_MODEL)
        self.assertEqual(settings.embedding_model, EMBEDDING_MODEL)

    def test_require_lmstudio_ready_rejects_empty_chat_response(self):
        with MockLMStudioServer(readiness_response="") as server:
            env = {
                "LMSTUDIO_BASE_URL": server.base_url,
                "LMSTUDIO_CHAT_MODEL": CHAT_MODEL,
                "LMSTUDIO_EMBEDDING_MODEL": EMBEDDING_MODEL,
            }
            with patch.dict(os.environ, env, clear=True):
                with self.assertRaisesRegex(RuntimeError, "empty response"):
                    require_lmstudio_ready()

    def test_readiness_prompt_is_specific(self):
        self.assertIn("OK", CHAT_READINESS_PROMPT)


if __name__ == "__main__":
    unittest.main()
