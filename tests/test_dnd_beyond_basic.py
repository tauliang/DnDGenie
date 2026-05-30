from __future__ import annotations

import builtins
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_dnd_module():
    loader = SourceFileLoader(
        "dnd_beyond_basic",
        str(ROOT / "scripts/dnd-beyond-basic"),
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class DnDBeyondBasicTests(unittest.TestCase):
    def setUp(self):
        self.module = load_dnd_module()

    def test_get_data_directories_can_be_overridden_for_tests(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            configured = os.pathsep.join([first, second])
            with patch.dict(os.environ, {"DNDGENIE_DATA_DIRS": configured}):
                self.assertEqual(
                    self.module.get_data_directories(),
                    [Path(first).resolve(), Path(second).resolve()],
                )

    def test_load_data_files_skips_spells_and_records_source_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "woods").write_text(
                "<html><body><h1>Woods</h1><p>Goblins lurk here.</p></body></html>",
                encoding="utf-8",
            )
            (root / "spells").write_text(
                "<html><body><h1>Spells</h1><p>Skip this.</p></body></html>",
                encoding="utf-8",
            )

            with contextlib.redirect_stdout(io.StringIO()):
                splits = self.module.load_data_files(root)

        self.assertGreater(len(splits), 0)
        self.assertTrue(all("woods" in split.metadata["source"] for split in splits))
        self.assertFalse(any("spells" in split.page_content.lower() for split in splits))

    def test_empty_model_answer_returns_actionable_message(self):
        class EmptyChain:
            def invoke(self, question):
                return ""

        genie = object.__new__(self.module.DnDGenie)
        genie.chain = EmptyChain()

        self.assertIn("empty answer", genie.answer("hello"))
        self.assertIn("--check-lmstudio", genie.answer("hello"))

    def test_blank_repl_input_reprompts_until_exit_command(self):
        class DummyGenie:
            def __init__(self, splits, settings):
                pass

            def add_source(self, source):
                raise AssertionError("blank input should not load a source")

            def answer(self, question):
                raise AssertionError("blank input should not ask a question")

        inputs = iter(["", "quit"])
        prompts = []

        def fake_input(prompt):
            prompts.append(prompt)
            return next(inputs)

        with patch.object(self.module, "require_lmstudio_ready", return_value=object()):
            with patch.object(self.module, "load_corpus", return_value=[]):
                with patch.object(self.module, "DnDGenie", DummyGenie):
                    with patch.object(builtins, "input", fake_input):
                        with patch.object(sys, "argv", ["dnd-beyond-basic"]):
                            self.module.main()

        self.assertEqual(prompts, ["input> ", "input> "])


if __name__ == "__main__":
    unittest.main()
