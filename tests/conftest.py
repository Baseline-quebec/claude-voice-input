"""Shared test fixtures."""

import io
from dataclasses import dataclass
from unittest.mock import MagicMock

import numpy as np
import pytest
from scipy.io import wavfile


@dataclass
class FakeSegment:
    text: str


@pytest.fixture()
def mock_whisper_model(monkeypatch):
    """Mock WhisperModel that returns predictable transcription."""
    model = MagicMock()
    segments = [FakeSegment(text="Bonjour le monde")]
    info = MagicMock()
    model.transcribe.return_value = (iter(segments), info)

    def fake_get_model():
        return model

    monkeypatch.setattr("claude_voice_input.server._model", model)
    monkeypatch.setattr("claude_voice_input.server.get_model", fake_get_model)
    return model


@pytest.fixture()
def mock_whisper_model_empty(monkeypatch):
    """Mock WhisperModel that returns no speech."""
    model = MagicMock()
    model.transcribe.return_value = (iter([]), MagicMock())

    monkeypatch.setattr("claude_voice_input.server._model", model)
    monkeypatch.setattr("claude_voice_input.server.get_model", lambda: model)
    return model


@pytest.fixture()
def sample_wav_bytes():
    """Generate a short WAV file with a sine wave."""
    sample_rate = 16000
    duration = 0.5
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    buf = io.BytesIO()
    wavfile.write(buf, sample_rate, audio)
    return buf.getvalue()


@pytest.fixture()
def sample_wav_file(tmp_path, sample_wav_bytes):
    """Write a sample WAV to a temp file and return its path."""
    path = tmp_path / "test.wav"
    path.write_bytes(sample_wav_bytes)
    return str(path)
