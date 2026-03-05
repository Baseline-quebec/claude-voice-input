"""MCP server exposing voice transcription tools."""

import os
import tempfile

from mcp.server.fastmcp import FastMCP

from claude_voice_input.recorder import record_audio

mcp = FastMCP(
    "claude-voice-input",
    description="Local voice input for Claude using Whisper.",
)

# Lazy-loaded model
_model = None


def get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        model_size = os.environ.get("WHISPER_MODEL", "base")
        device = os.environ.get("WHISPER_DEVICE", "auto")
        compute_type = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
        _model = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _model


@mcp.tool()
def voice_listen(
    language: str = "fr",
    silence_duration: float = 2.0,
    max_duration: float = 120.0,
) -> str:
    """Record audio from the microphone and transcribe it locally with Whisper.

    Listens until silence is detected, then returns the transcription.

    Args:
        language: Language code (e.g. "fr", "en"). Default: "fr".
        silence_duration: Seconds of silence before stopping. Default: 2.0.
        max_duration: Maximum recording duration in seconds. Default: 120.
    """
    audio_bytes = record_audio(
        silence_duration=silence_duration,
        max_duration=max_duration,
    )

    # Write to temp file for faster-whisper
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        model = get_model()
        segments, _info = model.transcribe(tmp_path, language=language, beam_size=5)
        text = " ".join(segment.text.strip() for segment in segments)
    finally:
        os.unlink(tmp_path)

    if not text.strip():
        return "[Aucune parole détectée]"

    return text


@mcp.tool()
def voice_transcribe_file(
    file_path: str,
    language: str = "fr",
) -> str:
    """Transcribe an existing audio file locally with Whisper.

    Args:
        file_path: Path to the audio file (wav, mp3, m4a, etc.).
        language: Language code (e.g. "fr", "en"). Default: "fr".
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    model = get_model()
    segments, _info = model.transcribe(file_path, language=language, beam_size=5)
    text = " ".join(segment.text.strip() for segment in segments)

    if not text.strip():
        return "[Aucune parole détectée]"

    return text


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
