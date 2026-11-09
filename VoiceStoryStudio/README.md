# VoiceStory Studio 🎧

**Turn any story into a locally narrated MP3 or chaptered M4B audiobook using a voice you own or have explicit permission to clone.**

VoiceStory Studio is a free, open-source Python application with a friendly browser interface. It uses Resemble AI's **Chatterbox Nano (110M)** on CPU, or **Chatterbox Turbo (350M)** on capable hardware. The app itself runs on your computer: no HeyGen, ElevenLabs, paid text-to-speech API or account needed.

> **Release status:** tested local audiobook packaging and resumption; voice-model inference must be verified on an end-user machine with downloaded model weights. This is a community project, not a hosted commercial service. Chatterbox research is no longer actively maintained by its original developers (as of 2026). It may require maintenance as Python libraries evolve.

## Features

| Feature | Details |
|---|---|
| Private voice reference | Record or upload WAV, MP3, M4A, FLAC, OGG, AAC. Select a **single-speaker** 6–30-second excerpt. |
| Offline synthesis | All narration happens on your device, after the first one-time **download of public model files**. |
| Long stories | Automatically splits into passages and creates each in sequence. |
| Resume interrupted jobs | Re-running a job safely skips valid completed passages. |
| Audiobook formats | Encodes a downloadable **MP3**, plus an **M4B with navigable chapters** when headings are present. |
| Quality options | CPU-friendly Nano or larger Turbo; configurable playback speed. |
| No secret account | No API keys, cloud voice-storage, in-app payments, public links or telemetry in this code. |

## Install

**Requires:** A personal Windows, macOS or Linux computer with at least **8 GB RAM** (more is preferable), several gigabytes of free storage, **Python 3.11**, **Git**, and **ffmpeg + ffprobe** on `PATH`. A desktop is more practical than an iPhone for local model inference. CPU generation can take a while; a compatible GPU may help.

1. Download/extract this repository.
2. Install [Python 3.11](https://www.python.org/downloads/), [Git](https://git-scm.com/downloads) and [FFmpeg](https://ffmpeg.org/download.html). On macOS with Homebrew: `brew install ffmpeg`. On Ubuntu: `sudo apt install ffmpeg`.
3. From the project directory, open Terminal / PowerShell and run:

```bash
python3.11 -m venv .venv
# macOS / Linux
source .venv/bin/activate
# On Windows, use instead: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python studio.py --diagnose
python studio.py --ui
```

Then visit **http://127.0.0.1:7860** (usually opens automatically). Upload or record **only your own voice**, paste your story (or choose a `.txt` file), check the consent box, and choose **Create private audiobook**. Finished files are saved within `~/VoiceStoryStudio-output/`.

*The first run downloads model weights from Hugging Face. These files are large. Your voice recording and story are **not** uploaded to Hugging Face by this application.*

### One-click helpers

- On Windows, run `start_windows.bat` after installing Python and FFmpeg.
- On macOS/Linux, run `bash start_mac_linux.sh` after installing Python and FFmpeg.
- The first run installs the open-source dependencies. Antivirus software and Python security prompts depend on your device.

## Command line

```bash
python studio.py --voice "my_voice.m4a" --story "my_story.txt" --output "my_private_book" \
  --model nano --title "My Family Adventure" --author "Parent Narration"
```

For recordings containing several speakers, crop to a segment containing **only the consenting speaker**:

```bash
python studio.py --voice "conversation.m4a" --reference-start 3 \
  --reference-seconds 14 --story "story.txt" --output "my_private_book"
```

The output is in `my_private_book/job_*/audiobook_*.mp3` and `.m4b`. Your original reference, script, audio clips and progress manifest are saved in this private job directory, so do not share it accidentally. To resume, run the **identical command** again. Change `--speed 0.9` to create a different-speed export without redoing successful voice segments.

### How to add chapters

Add headings on their own lines:

```text
Chapter One: The Beginning

That evening, something changed.

Chapter Two: The Mystery

The old computer began to glow.

Epilogue: The Discovery

They finally understood.
```

The M4B contains clickable timestamps for each detected chapter. MP3 is a single continuous recording, usable in almost any audio player.

## Quality tips

Voice cloning quality varies: use a **clean, quiet recording of one person**, without overlapping speakers, background music or large pauses. Record 10–20 seconds of natural, expressive speech for a first attempt. Pronunciation may need adjustment in the input text, particularly for names. Each TTS segment may sound slightly different; listen and edit the text as necessary. AI narration will not sound *identical* to the speaker in every sentence.

### What's local—and what isn't?

- ✅ **Local:** the web interface, reference editing, model inference, saved audio, scripts and resumable jobs.
- 🌐 **Once, at setup:** pip installs third-party open-source libraries, and first model use downloads weights from Hugging Face.
- ❌ **Not included:** a public voice-cloning website, browser-only inference, remote hosting, voice marketplace or cloud storage.

Hosting the source publicly on GitHub is different from publicly uploading people's voices. **Never commit voice samples, family stories, `.wav` segments or completed audiobooks.** By default the UI binds to loopback only (`127.0.0.1`, `share=False`).

## Consent & responsible use

**Only clone your own voice or someone who has explicitly authorized cloning and generation.** Do not create deceptive impersonations, unauthorized endorsements, scams or misleading calls. When sharing the final audio, label it as AI-narrated. The project is not intended for use without the recorded person's consent.

For security guidance, see [SECURITY.md](SECURITY.md).

## Testing and development

```bash
python -m unittest discover -s tests -v
```

Tests exercise segmentation, chapter detection, synthetic local generation, MP3 and M4B encoding, input validation and interruption resumption without downloading voice models or using a real person's voice. They do **not** validate a real voice's similarity or successfully synthesize with the actual model in this build environment.

## Credits and licensing

- Wrapper/application code: **MIT License**, [LICENSE](LICENSE).
- Open-source TTS library and checkpoints: [Resemble AI Chatterbox](https://github.com/resemble-ai/chatterbox) and [Chatterbox Nano](https://huggingface.co/ResembleAI/chatterbox-nano). Refer to their licenses and documentation; their research repository was retired in 2026.
- Encoders: FFmpeg; consult FFmpeg's licensing for your own distribution plans.

This project is independently maintained and **not endorsed by Resemble AI**.

### Version note (November 2026)

The app installs Chatterbox from a **pinned GitHub source commit** rather than the published March 2026 PyPI wheel, because the later Nano model interface is present in the pinned source. Git is required, including for the upstream `resemble-perth` dependency. If your network prohibits GitHub, install on a network that can fetch the source and model files. This release has **not yet been validated end to end with downloaded model weights**; synthetic test voices only verify the file-processing pipeline.