"""All tests run with synthetic voices; nobody's voice or private story is bundled."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf

import studio


class SegmentationTests(unittest.TestCase):
    def test_plain_prose_lossless_words(self):
        source = "Hello world. Here's a mysterious story!\n\nNext paragraph, another clue?"
        chunks = studio.split_narration(source, 43)
        self.assertTrue(all(len(c) <= 43 for c in chunks))
        self.assertEqual(" ".join(chunks), " ".join(source.split()))

    def test_very_long_sentence(self):
        text = " ".join(["mystery", "connection", "beautiful"] * 30)
        chunks = studio.split_narration(text, 60)
        self.assertEqual(" ".join(chunks), text)
        self.assertTrue(all(len(c) <= 60 for c in chunks))

    def test_very_long_word(self):
        text = "a" * 142
        chunks = studio.split_narration(text, 40)
        self.assertEqual("".join(chunks), text)
        self.assertTrue(all(len(c) <= 40 for c in chunks))

    def test_empty_and_invalid(self):
        self.assertEqual(studio.split_narration(""), [])
        with self.assertRaises(ValueError):
            studio.split_narration("Hello", 8)

    def test_chapter_detection(self):
        text = "Opening text.\n\nChapter One: The Clue\n\nThe secret lies below.\n\nEpilogue\n\nAll is well."
        parts = studio.split_narration(text, 45)
        self.assertTrue(parts)
        self.assertTrue(studio.chapter_name("Chapter One: The Clue"))
        self.assertTrue(studio.chapter_name("Epilogue"))
        self.assertEqual([c["title"] for c in studio.assign_chapters(text, parts)],
                         ["Opening", "Chapter One: The Clue", "Epilogue"])
        self.assertIsNone(studio.chapter_name("Not a chapter"))

    def test_diagnostics_safe_and_local(self):
        d = studio.diagnostics()
        self.assertTrue("ffmpeg" in d and "packages" in d)
        source = Path(studio.__file__).read_text()
        self.assertIn('server_name="127.0.0.1"', source)
        self.assertIn("share=False", source)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires ffmpeg")
class AudioWorkflowTests(unittest.TestCase):
    class FakeModel:
        sr = 24000
        def __init__(self):
            self.calls = []
        def generate(self, text, audio_prompt_path):
            assert Path(audio_prompt_path).exists()
            self.calls.append(text)
            t = np.arange(6000, dtype=np.float32) / self.sr
            return np.sin(t * 2 * np.pi * 190).astype(np.float32) * 0.2

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.reference = root / "voice fake.wav"
        self.output = root / "private_out"
        t = np.arange(24000 * 17, dtype=np.float32) / 24000
        sf.write(self.reference, np.sin(t * 2 * np.pi * 150) * .1, 24000)

    def test_produces_mp3_chaptered_m4b_and_resumes(self):
        text = "A secret begins.\n\nChapter One: A Clue\n\nTwo minds share a special bond.\n\nEpilogue\n\nThe end."
        model = self.FakeModel()
        options = dict(variant="nano", title="Test story", author="Test author", chunk_limit=65,
                       model_factory=lambda *_: model)
        r = studio.generate_audiobook(text, self.reference, self.output, **options)
        self.assertIn("mp3", r)
        self.assertIn("m4b", r)
        self.assertGreater(r["mp3"].stat().st_size, 1000)
        self.assertGreater(r["m4b"].stat().st_size, 1000)
        original_calls = len(model.calls)
        self.assertGreater(original_calls, 0)
        again = studio.generate_audiobook(text, self.reference, self.output, **options)
        self.assertEqual(r, again)
        self.assertEqual(original_calls, len(model.calls), "resume must not regenerate existing clips")
        manifest = json.loads((r["mp3"].parent / "manifest.json").read_text())
        self.assertEqual(manifest["variant"], "nano")
        self.assertTrue(manifest["segments"])
        self.assertIn("script.txt", [p.name for p in r["mp3"].parent.iterdir()])
        import subprocess
        chapters = subprocess.run(["ffprobe", "-v", "error", "-show_chapters", "-of", "json",
                                   str(r["m4b"])], capture_output=True, text=True, check=True)
        titles = [ch["tags"]["title"] for ch in json.loads(chapters.stdout)["chapters"]]
        self.assertEqual(titles, ["Opening", "Chapter One: A Clue", "Epilogue"])

    def test_changes_in_reference_start_create_separate_job(self):
        text = "A little story."
        kwargs = dict(variant="nano", make_m4b=False, model_factory=lambda *_: self.FakeModel())
        a = studio.generate_audiobook(text, self.reference, self.output, reference_start=0, **kwargs)
        b = studio.generate_audiobook(text, self.reference, self.output, reference_start=1, **kwargs)
        self.assertNotEqual(a["mp3"].parent, b["mp3"].parent)

    def test_validation(self):
        with self.assertRaises(FileNotFoundError):
            studio.generate_audiobook("hello", self.output / "missing.wav", self.output)
        with self.assertRaises(ValueError):
            studio.generate_audiobook("", self.reference, self.output)
        with self.assertRaises(ValueError):
            studio.prepare_reference(self.reference, self.output / "bad.wav", start=12, seconds=14)


if __name__ == "__main__":
    unittest.main()