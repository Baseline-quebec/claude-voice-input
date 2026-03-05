"""Tests for the MCP server tools."""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestGetModel:
    """Tests for the lazy model loader."""

    def test_reads_env_vars(self, monkeypatch):
        """get_model should respect environment variables."""
        import claude_voice_input.server as server_mod

        server_mod._model = None
        monkeypatch.setenv("WHISPER_MODEL", "tiny")
        monkeypatch.setenv("WHISPER_DEVICE", "cpu")
        monkeypatch.setenv("WHISPER_COMPUTE_TYPE", "float32")

        with patch("claude_voice_input.server.WhisperModel", create=True):
            # Patch the import inside get_model
            fake_whisper = MagicMock()
            mock_model_instance = MagicMock()
            fake_whisper.WhisperModel.return_value = mock_model_instance

            with patch.dict("sys.modules", {"faster_whisper": fake_whisper}):
                server_mod._model = None
                result = server_mod.get_model()

            fake_whisper.WhisperModel.assert_called_once_with(
                "tiny", device="cpu", compute_type="float32"
            )
            assert result is mock_model_instance

        server_mod._model = None

    def test_returns_cached_model(self, monkeypatch):
        """get_model should return cached model on second call."""
        import claude_voice_input.server as server_mod

        sentinel = MagicMock()
        server_mod._model = sentinel
        assert server_mod.get_model() is sentinel
        server_mod._model = None


class TestVoiceTranscribeFile:
    """Tests for voice_transcribe_file tool."""

    def test_transcribes_file(self, mock_whisper_model, sample_wav_file):
        """Should return transcription text for a valid file."""
        from claude_voice_input.server import voice_transcribe_file

        result = voice_transcribe_file(file_path=sample_wav_file, language="fr")
        assert result == "Bonjour le monde"
        mock_whisper_model.transcribe.assert_called_once_with(
            sample_wav_file, language="fr", beam_size=5
        )

    def test_file_not_found(self, mock_whisper_model):
        """Should raise FileNotFoundError for missing files."""
        from claude_voice_input.server import voice_transcribe_file

        with pytest.raises(FileNotFoundError, match="not_a_real_file"):
            voice_transcribe_file(file_path="/tmp/not_a_real_file.wav")

    def test_no_speech_detected(self, mock_whisper_model_empty, sample_wav_file):
        """Should return placeholder when no speech is detected."""
        from claude_voice_input.server import voice_transcribe_file

        result = voice_transcribe_file(file_path=sample_wav_file)
        assert result == "[Aucune parole détectée]"

    def test_multiple_segments(self, monkeypatch, sample_wav_file):
        """Should join multiple segments with spaces."""
        from dataclasses import dataclass

        @dataclass
        class Seg:
            text: str

        model = MagicMock()
        segments = [Seg(text="Premiere phrase."), Seg(text="Deuxieme phrase.")]
        model.transcribe.return_value = (iter(segments), MagicMock())
        monkeypatch.setattr("claude_voice_input.server._model", model)
        monkeypatch.setattr("claude_voice_input.server.get_model", lambda: model)

        from claude_voice_input.server import voice_transcribe_file

        result = voice_transcribe_file(file_path=sample_wav_file)
        assert result == "Premiere phrase. Deuxieme phrase."


class TestVoiceListen:
    """Tests for voice_listen tool."""

    def test_records_and_transcribes(self, mock_whisper_model, monkeypatch, sample_wav_bytes):
        """Should record audio and return transcription."""
        monkeypatch.setattr(
            "claude_voice_input.server.record_audio", lambda **kwargs: sample_wav_bytes
        )

        from claude_voice_input.server import voice_listen

        result = voice_listen(language="fr", silence_duration=1.0, max_duration=10.0)
        assert result == "Bonjour le monde"

    def test_passes_params_to_recorder(self, mock_whisper_model, monkeypatch, sample_wav_bytes):
        """Should forward silence_duration and max_duration to recorder."""
        captured = {}

        def fake_record(**kwargs):
            captured.update(kwargs)
            return sample_wav_bytes

        monkeypatch.setattr("claude_voice_input.server.record_audio", fake_record)

        from claude_voice_input.server import voice_listen

        voice_listen(silence_duration=3.0, max_duration=60.0)
        assert captured["silence_duration"] == 3.0
        assert captured["max_duration"] == 60.0

    def test_no_speech_returns_placeholder(
        self, mock_whisper_model_empty, monkeypatch, sample_wav_bytes
    ):
        """Should return placeholder when no speech detected."""
        monkeypatch.setattr(
            "claude_voice_input.server.record_audio", lambda **kwargs: sample_wav_bytes
        )

        from claude_voice_input.server import voice_listen

        result = voice_listen()
        assert result == "[Aucune parole détectée]"

    def test_cleans_up_temp_file(self, mock_whisper_model, monkeypatch, sample_wav_bytes):
        """Should delete the temporary WAV file after transcription."""
        monkeypatch.setattr(
            "claude_voice_input.server.record_audio", lambda **kwargs: sample_wav_bytes
        )

        import glob
        import tempfile

        before = set(glob.glob(os.path.join(tempfile.gettempdir(), "*.wav")))

        from claude_voice_input.server import voice_listen

        voice_listen()

        after = set(glob.glob(os.path.join(tempfile.gettempdir(), "*.wav")))
        new_files = after - before
        assert len(new_files) == 0, f"Temp file not cleaned up: {new_files}"
