"""VoiceStory Studio: privacy-first, offline-inference audiobook creator.

Model files are downloaded once from the open-source model host. The original
recording, script and generated speech are never intentionally sent to a TTS API.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

APP_NAME = "VoiceStory Studio"
DEFAULT_LIMIT = 220
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac"}
Progress = Callable[[str], None]


def split_narration(text: str, limit: int = DEFAULT_LIMIT) -> list[str]:
    """Chunk prose without losing words, preserving the narration's text order.

    Segment durations are intentionally short for stability on CPU-only devices.
    Whitespace is normalized, since it is not spoken by the TTS engine.
    """
    if limit < 40:
        raise ValueError("Segment limit must be at least 40 characters")
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    fragments: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        # A chapter heading must start a new segment for accurate M4B chapters.
        if chapter_name(line):
            fragments.append("\0CHAPTER_BOUNDARY\0")
        fragments.extend(re.split(r'(?<=[.!?])\s+(?=["\'“‘A-Z0-9])', line))

    chunks: list[str] = []
    current = ""

    def append(piece: str) -> None:
        nonlocal current
        if current and len(current) + 1 + len(piece) > limit:
            chunks.append(current)
            current = ""
        current = f"{current} {piece}" if current else piece

    for fragment in fragments:
        if fragment == "\0CHAPTER_BOUNDARY\0":
            if current:
                chunks.append(current)
                current = ""
            continue
        fragment = fragment.strip()
        if not fragment:
            continue
        if len(fragment) <= limit:
            append(fragment)
        else:
            for word in fragment.split():
                if len(word) <= limit:
                    append(word)
                else:
                    # Extremely long unbroken strings (URLs, unusual words).
                    for start in range(0, len(word), limit):
                        append(word[start:start + limit])
    if current:
        chunks.append(current)
    if any(len(c) > limit for c in chunks):
        raise AssertionError("Chunker generated an oversized segment")
    return chunks


def chapter_name(text: str) -> str | None:
    stripped = text.strip().rstrip(".")
    if re.match(r"^(?:chapter\s+\w+\s*[:—\-].+|epilogue\b.*|prologue\b.*)$", stripped, re.I):
        return stripped
    return None


def assign_chapters(text: str, segments: list[str]) -> list[dict]:
    """Find heading start segment indices for M4B chapter metadata.

    The script is split into voice segments separately. We avoid dangerous
    fuzzy matching: only headings at the beginning of a generated segment count.
    """
    chapter_candidates = [chapter_name(line) for line in text.splitlines()]
    candidates = [item for item in chapter_candidates if item]
    chapters = [{"title": "Opening", "segment": 1}]
    for title in candidates:
        for idx, seg in enumerate(segments, 1):
            if seg.lower().startswith(title.lower()) and idx != 1:
                if chapters[-1]["segment"] != idx:
                    chapters.append({"title": title, "segment": idx})
                break
    return sorted(chapters, key=lambda chapter: chapter["segment"])


def _run(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, check=True, cwd=cwd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required program is missing: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        details = exc.stderr.strip()[-1400:]
        raise RuntimeError(f"Command failed: {args[0]} ({details})") from exc


def _ffprobe_duration(path: Path) -> float:
    out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(path)]).stdout
    return float(out.strip())


def prepare_reference(source: str | Path, destination: Path, *, start: float = 0.0,
                      seconds: int = 14) -> Path:
    """Extract the chosen speaker only; no speaker-separation is attempted.

    Users must choose an interval in the recording with no second speaker.
    """
    source = Path(source).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Voice sample not found: {source}")
    if source.suffix.lower() not in AUDIO_EXTENSIONS:
        raise ValueError("Voice sample must be WAV, MP3, M4A, FLAC, OGG or AAC")
    if start < 0 or not 6 <= seconds <= 30:
        raise ValueError("Select a start time >= 0 and a reference length of 6–30 seconds")
    for program in ("ffmpeg", "ffprobe"):
        if not shutil.which(program):
            raise RuntimeError(f"{program} is required. Install ffmpeg first.")
    duration = _ffprobe_duration(source)
    if start + 6 > duration:
        raise ValueError("The selected reference contains fewer than 6 seconds of speech")
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_name(destination.stem + ".partial.wav")
    _run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
          "-ss", str(start), "-i", str(source), "-vn", "-t", str(seconds),
          "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(tmp)])
    if _ffprobe_duration(tmp) < 5.5:
        tmp.unlink(missing_ok=True)
        raise ValueError("Voice reference is too short. Select at least 6 seconds.")
    tmp.replace(destination)
    return destination


def _device() -> str:
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _load_model(variant: str, device: str):
    from chatterbox.tts_turbo import ChatterboxTurboTTS
    # Both the official Nano and Turbo models use ChatterboxTurboTTS.
    return ChatterboxTurboTTS.from_pretrained(device=device, nano=(variant == "nano"))


def _job_key(script: str, voice: Path, variant: str, chunk_limit: int,
             reference_start: float, reference_seconds: int) -> str:
    digest = hashlib.sha256()
    digest.update(script.encode("utf-8"))
    digest.update(voice.read_bytes())
    digest.update(json.dumps([variant, chunk_limit, reference_start, reference_seconds]).encode())
    return digest.hexdigest()[:20]


def _atomic_json(path: Path, data: object) -> None:
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def _make_ffmetadata(title: str, author: str, segments: list[Path],
                     chapters: list[dict], directory: Path, speed: float = 1.0) -> Path:
    """Write chapter timestamps, computed from actual synthesized clip lengths."""
    durations = [_ffprobe_duration(p) / speed for p in segments]
    starts_ms = [0]
    for dur in durations:
        starts_ms.append(starts_ms[-1] + round(dur * 1000))
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("=", "\\=").replace(";", "\\;").replace("#", "\\#").replace("\n", " ")
    lines = [";FFMETADATA1", f"title={esc(title)}", f"artist={esc(author)}", "comment=AI-generated voice narration"]
    for i, c in enumerate(chapters):
        index = c["segment"] - 1
        next_index = chapters[i + 1]["segment"] - 1 if i + 1 < len(chapters) else len(segments)
        if next_index <= index:
            continue
        lines += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={starts_ms[index]}",
                  f"END={starts_ms[next_index]}", f"title={esc(c['title'])}"]
    path = directory / "chapters.ffmetadata"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def generate_audiobook(
    text: str,
    voice_file: str | Path,
    output_dir: str | Path,
    *,
    variant: str = "nano",
    speed: float = 1.0,
    chunk_limit: int = DEFAULT_LIMIT,
    reference_start: float = 0.0,
    reference_seconds: int = 14,
    title: str = "My Audiobook",
    author: str = "",
    make_m4b: bool = True,
    on_progress: Progress | None = None,
    model_factory: Callable[[str, str], object] | None = None,
) -> dict[str, Path]:
    """Create a resumable, locally rendered MP3 and optionally chaptered M4B.

    The job hash isolates different voices, stories, models and crop settings.
    Segment saves are atomic; resume never accepts partial or undersized WAVs.
    """
    if variant not in {"nano", "turbo"}:
        raise ValueError("Model must be nano or turbo")
    if not 0.7 <= speed <= 1.3:
        raise ValueError("Playback speed must be 0.7–1.3")
    if not 40 <= chunk_limit <= 600:
        raise ValueError("Segment limit must be 40–600 characters")
    if not title.strip():
        title = "My Audiobook"
    voice = Path(voice_file).expanduser().resolve()
    if not voice.is_file():
        raise FileNotFoundError(f"Voice file not found: {voice}")
    segments = split_narration(text, chunk_limit)
    if not segments:
        raise ValueError("Enter a story or upload a plain-text script")
    if len(segments) > 10000:
        raise ValueError("Script is too long for one job; split it into volumes")
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    job = output / f"job_{_job_key(text, voice, variant, chunk_limit, reference_start, reference_seconds)}"
    job.mkdir(parents=True, exist_ok=True)
    progress = on_progress or (lambda _: None)
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("Install ffmpeg (including ffprobe) before generating audiobooks")

    reference = job / "voice_reference.wav"
    if not reference.exists():
        progress("Preparing your authorized voice sample locally…")
        prepare_reference(voice, reference, start=reference_start, seconds=reference_seconds)
    (job / "script.txt").write_text(text, encoding="utf-8")
    chapters = assign_chapters(text, segments)
    _atomic_json(job / "manifest.json", {
        "format": "VoiceStory Studio job v2", "voice_file_name": voice.name,
        "variant": variant, "reference_start": reference_start,
        "reference_seconds": reference_seconds, "segment_limit": chunk_limit,
        "segments": segments, "chapters": chapters,
        "note": "AI-generated audio. Private story/voice data: do not publish this folder."
    })

    def valid_audio(p: Path) -> bool:
        if not p.is_file() or p.stat().st_size < 3000:
            return False
        try:
            return _ffprobe_duration(p) > 0.09
        except Exception:
            return False

    wave_files = [job / f"segment_{i:05d}.wav" for i in range(1, len(segments) + 1)]
    pending = [(i, phrase, wave_files[i-1]) for i, phrase in enumerate(segments, 1)
               if not valid_audio(wave_files[i-1])]
    refreshed = bool(pending)
    if pending:
        device = _device() if model_factory is None else "cpu"
        progress(f"Loading {variant.upper()} on {device}. First use downloads open-source model weights…")
        model = (model_factory or _load_model)(variant, device)
        import numpy as np
        import soundfile as sf
        import torch
        for n, phrase, file in pending:
            progress(f"Narrating passage {n} of {len(segments)}")
            with torch.inference_mode():
                wav = model.generate(phrase, audio_prompt_path=str(reference))
            audio = wav.squeeze().detach().cpu().numpy() if hasattr(wav, "detach") else np.asarray(wav).squeeze()
            if audio.ndim != 1 or audio.size < 600 or not np.all(np.isfinite(audio)):
                raise RuntimeError(f"Voice model gave invalid audio for passage {n}. Rerun to resume.")
            sr = int(model.sr)
            gap = np.zeros(round(sr * (0.38 if phrase.endswith((".", "?", "!")) else 0.22)), dtype="float32")
            staging = file.with_suffix(".partial.wav")
            sf.write(str(staging), np.concatenate([audio.astype("float32"), gap]), sr, subtype="PCM_16")
            staging.replace(file)

    # Relative segment paths avoid ffconcat quoting bugs with apostrophes and spaces.
    playlist = job / "segments.ffconcat"
    playlist.write_text("ffconcat version 1.0\n" + "".join(f"file '{p.name}'\n" for p in wave_files), encoding="utf-8")
    speed_percent = round(speed * 100)
    tags_hash = hashlib.sha256(f"{title}\0{author}".encode()).hexdigest()[:8]
    suffix = f"_{speed_percent}pct_{tags_hash}"
    mp3 = job / f"audiobook{suffix}.mp3"
    m4b = job / f"audiobook{suffix}.m4b"
    mp3_tmp = job / f"audiobook{suffix}.partial.mp3"
    m4b_tmp = job / f"audiobook{suffix}.partial.m4b"
    speed_filter = ["-af", f"atempo={speed}"] if speed != 1 else []
    common = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
              "-f", "concat", "-safe", "1", "-i", str(playlist)]
    if refreshed or not valid_audio(mp3):
        progress("Combining passages and encoding MP3…")
        _run(common + speed_filter + ["-metadata", f"title={title}", "-metadata", f"artist={author}",
             "-metadata", "comment=AI-generated narration", "-c:a", "libmp3lame", "-b:a", "160k", str(mp3_tmp)])
        mp3_tmp.replace(mp3)
    outputs = {"mp3": mp3}
    if make_m4b:
        if refreshed or not valid_audio(m4b):
            progress("Creating chaptered M4B audiobook…")
            metadata = _make_ffmetadata(title, author, wave_files, chapters, job, speed=speed)
            _run(common + ["-i", str(metadata), "-map_metadata", "1", "-map_chapters", "1",
                          "-vn"] + speed_filter + ["-c:a", "aac", "-b:a", "128k", str(m4b_tmp)])
            m4b_tmp.replace(m4b)
        outputs["m4b"] = m4b
    progress("Completed: audio saved locally in " + str(job))
    return outputs


def diagnostics() -> dict:
    packages = ("gradio", "torch", "torchaudio", "chatterbox", "numpy", "soundfile")
    return {"python": sys.version.split()[0], "platform": platform.platform(),
            "ffmpeg": shutil.which("ffmpeg"), "ffprobe": shutil.which("ffprobe"),
            "packages": {name: importlib.util.find_spec(name) is not None for name in packages},
            "note": "A working Chatterbox runtime and model weights are also required; this check does not synthesize audio."}


def run_ui() -> None:
    import gradio as gr

    with gr.Blocks(title=APP_NAME) as app:
        gr.Markdown("# 🎧 VoiceStory Studio\n**Your story. Your authorized voice. Your computer.**")
        gr.Markdown("Free, local audiobook generation with Chatterbox Nano/Turbo. No hosted voice API or paid credits. "
                    "Your narration and voice reference stay on this machine; open-source model weights download once.")
        with gr.Row():
            voice = gr.Audio(label="Voice reference (your own voice; 10–20 clean seconds)",
                             type="filepath", sources=["upload", "microphone"])
            script_file = gr.File(label="Optional plain-text story (.txt)", type="filepath", file_types=[".txt"])
        script = gr.Textbox(label="Story (or upload .txt)", lines=12,
                            placeholder="There are some mysteries that science has yet to explain...")
        with gr.Row():
            title = gr.Textbox(value="My Audiobook", label="Book title")
            author = gr.Textbox(value="", label="Author / narrator credit")
        with gr.Accordion("Narration settings", open=False):
            with gr.Row():
                model = gr.Dropdown(["nano", "turbo"], value="nano", label="Model (Nano recommended for CPU)")
                speed = gr.Slider(minimum=0.7, maximum=1.3, step=0.05, value=1.0, label="Playback speed")
                start = gr.Number(value=0, minimum=0, label="Reference start (seconds)")
                length = gr.Slider(minimum=6, maximum=30, value=14, step=1, label="Voice reference length (seconds)")
        consent = gr.Checkbox(label="I am the speaker, or have their explicit permission to clone this voice.")
        create = gr.Button("Create private audiobook", variant="primary")
        status = gr.Textbox(label="Status", interactive=False)
        player = gr.Audio(label="Listen to audiobook", type="filepath")
        files = gr.File(label="Download MP3 and chaptered M4B", file_count="multiple")
        gr.Markdown("🔒 **Privacy:** This app only listens on `127.0.0.1`, never creates a public share link, "
                    "and does not include upload, analytics or narration APIs. Do not redistribute audio deceptively.")

        def work(sample, upload, text, book, writer, variant, pace, offset, seconds, authorized,
                 progress=gr.Progress()):
            if not authorized:
                raise gr.Error("Confirm that you have permission to use the speaker's voice.")
            if not sample:
                raise gr.Error("Record or upload your authorized voice sample first.")
            if upload:
                text = Path(upload).read_text(encoding="utf-8-sig")
            try:
                outputs = generate_audiobook(text, sample, Path.home() / "VoiceStoryStudio-output",
                    variant=variant, speed=float(pace), reference_start=float(offset),
                    reference_seconds=int(seconds), title=book, author=writer, make_m4b=True,
                    on_progress=lambda message: progress(0, desc=message))
            except Exception as exc:
                raise gr.Error(str(exc)) from exc
            return "Finished! Your files are saved locally.", str(outputs["mp3"]), [str(p) for p in outputs.values()]

        create.click(work, inputs=[voice, script_file, script, title, author, model, speed, start, length, consent],
                     outputs=[status, player, files], concurrency_limit=1)
    app.queue().launch(server_name="127.0.0.1", server_port=7860, share=False, inbrowser=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local open-source voice-cloned audiobook studio")
    parser.add_argument("--voice", help="Your authorized speaker WAV/M4A/MP3 recording")
    parser.add_argument("--story", help="UTF-8 text file to narrate")
    parser.add_argument("--output", default="output", help="Private output directory")
    parser.add_argument("--model", choices=["nano", "turbo"], default="nano")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--reference-start", type=float, default=0.0)
    parser.add_argument("--reference-seconds", type=int, default=14)
    parser.add_argument("--title", default="My Audiobook")
    parser.add_argument("--author", default="")
    parser.add_argument("--mp3-only", action="store_true")
    parser.add_argument("--ui", action="store_true", help="Open local browser interface")
    parser.add_argument("--diagnose", action="store_true", help="Check installation prerequisites")
    args = parser.parse_args()
    if args.diagnose:
        print(json.dumps(diagnostics(), indent=2))
        return
    if args.ui:
        run_ui()
        return
    if not args.voice or not args.story:
        parser.error("Supply --voice and --story, or use --ui")
    text = Path(args.story).read_text(encoding="utf-8-sig")
    outputs = generate_audiobook(text, args.voice, args.output, variant=args.model,
              speed=args.speed, reference_start=args.reference_start,
              reference_seconds=args.reference_seconds, title=args.title,
              author=args.author, make_m4b=not args.mp3_only, on_progress=print)
    for kind, path in outputs.items():
        print(f"{kind.upper()}: {path}")


if __name__ == "__main__":
    main()