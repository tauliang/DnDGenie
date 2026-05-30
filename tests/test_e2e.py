from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import CHAT_MODEL
from support import EMBEDDING_MODEL
from support import MockLMStudioServer


ROOT = Path(__file__).resolve().parents[1]


def script_env(server: MockLMStudioServer, data_dir: str | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "LMSTUDIO_BASE_URL": server.base_url,
            "LMSTUDIO_CHAT_MODEL": CHAT_MODEL,
            "LMSTUDIO_EMBEDDING_MODEL": EMBEDDING_MODEL,
            "LMSTUDIO_API_KEY": "test-key",
        }
    )
    if data_dir:
        env["DNDGENIE_DATA_DIRS"] = data_dir
    return env


class EndToEndTests(unittest.TestCase):
    def test_check_lmstudio_passes_against_openai_compatible_mock(self):
        with MockLMStudioServer() as server:
            result = subprocess.run(
                [sys.executable, "scripts/dnd-beyond-basic", "--check-lmstudio"],
                cwd=ROOT,
                env=script_env(server),
                text=True,
                capture_output=True,
                timeout=20,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Models visible to the local server", result.stdout)
        self.assertIn("LM Studio chat and embedding models are ready", result.stdout)

    def test_repl_answers_sample_dnd_prompt_with_mock_lmstudio(self):
        response = "Encounter table: 1. Goblin scouts. 2. Lost traveler."
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            (data_dir / "woods").write_text(
                "<html><body><h1>Woods</h1><p>Goblins hide in forest trails.</p></body></html>",
                encoding="utf-8",
            )
            with MockLMStudioServer(chat_response=response) as server:
                result = subprocess.run(
                    [sys.executable, "scripts/dnd-beyond-basic"],
                    cwd=ROOT,
                    env=script_env(server, str(data_dir)),
                    input=(
                        "provide a brief random encounter table for 3 first-level "
                        "characters. They are in the woods.\nquit\n"
                    ),
                    text=True,
                    capture_output=True,
                    timeout=30,
                )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Loading", result.stdout)
        self.assertIn("Thinking...", result.stdout)
        self.assertIn("Goblin scouts", result.stdout)

    def test_repl_reports_empty_chat_response(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            (data_dir / "woods").write_text(
                "<html><body><h1>Woods</h1><p>Forest encounter notes.</p></body></html>",
                encoding="utf-8",
            )
            with MockLMStudioServer(chat_response="") as server:
                result = subprocess.run(
                    [sys.executable, "scripts/dnd-beyond-basic"],
                    cwd=ROOT,
                    env=script_env(server, str(data_dir)),
                    input="what happens in the woods?\nquit\n",
                    text=True,
                    capture_output=True,
                    timeout=30,
                )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("empty answer", result.stdout)
        self.assertIn("--check-lmstudio", result.stdout)

    def test_repl_load_url_command_adds_documents(self):
        response = "Loaded shrine notes and answered from the extra source."
        html_pages = {
            "/extra-rules": (
                "<html><body><h1>Forest Shrine</h1>"
                "<p>A mossy shrine grants a small blessing.</p></body></html>"
            )
        }
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            (data_dir / "woods").write_text(
                "<html><body><h1>Woods</h1><p>Forest encounter notes.</p></body></html>",
                encoding="utf-8",
            )
            with MockLMStudioServer(chat_response=response, html_pages=html_pages) as server:
                result = subprocess.run(
                    [sys.executable, "scripts/dnd-beyond-basic"],
                    cwd=ROOT,
                    env=script_env(server, str(data_dir)),
                    input=(
                        f"load({server.base_url}/extra-rules)\n"
                        "what happens at the shrine?\nquit\n"
                    ),
                    text=True,
                    capture_output=True,
                    timeout=30,
                )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("/extra-rules", server.requested_paths)
        self.assertIn("Loaded shrine notes", result.stdout)


if __name__ == "__main__":
    unittest.main()
