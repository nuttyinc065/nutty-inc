# Security & privacy

This application is **designed for local personal use**, not for internet hosting without additional authentication and security hardening.

- Keep the Gradio server at `127.0.0.1`; do not set `share=True` or expose port 7860 to the internet.
- The app never intentionally uploads the voice sample, script, or generated recordings to a narration API. Installing Python packages and initial model weights requires internet.
- Local caches, temporary UI uploads, voice-reference WAVs, scripts, and exported audio can contain sensitive personal information. Keep the output folder private and delete when no longer needed.
- The source code repository must **not** include a recording of a real person's voice, private stories, or generated personal audiobooks. `.gitignore` helps but is not a security boundary.
- Voice cloning must be explicitly authorized by the speaker. Do not deploy for anonymous public access without abuse safeguards, authentication and privacy controls.
- Audio outputs should be labeled **AI-generated narration** to prevent confusion.
- Do not accept untrusted executable content or scripts as model downloads. Fetch dependencies from original maintainers.
- Chatterbox's upstream repository is retired research and receives no official security maintenance. Review dependencies regularly before use.
- If you find a vulnerability, contact the maintainer privately. Do not post private audio or exploit proofs in public issues.