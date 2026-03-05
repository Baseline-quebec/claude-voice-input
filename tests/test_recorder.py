"""Tests for the audio recorder module."""

import io
from unittest.mock import patch

import numpy as np
from scipy.io import wavfile


class TestRecordAudio:
    """Tests for record_audio function."""

    def _make_audio_chunks(self, n_chunks, amplitude=0.5, blocksize=1024):
        """Generate fake audio chunks."""
        return [
            np.random.uniform(-amplitude, amplitude, (blocksize, 1)).astype(np.float32)
            for _ in range(n_chunks)
        ]

    def _make_silent_chunks(self, n_chunks, blocksize=1024):
        """Generate silent audio chunks."""
        return [np.zeros((blocksize, 1), dtype=np.float32) for _ in range(n_chunks)]

    @patch("claude_voice_input.recorder.sd")
    def test_returns_wav_bytes(self, mock_sd):
        """Recording should return valid WAV bytes."""
        from claude_voice_input.recorder import record_audio

        audio_chunks = self._make_audio_chunks(20) + self._make_silent_chunks(40)
        chunk_iter = iter(audio_chunks)

        class FakeStream:
            def __enter__(self_stream):
                return self_stream

            def __exit__(self_stream, *args):
                pass

        def fake_input_stream(**kwargs):
            callback = kwargs["callback"]
            stream = FakeStream()
            original_enter = stream.__enter__

            def patched_enter():
                result = original_enter()
                for chunk in chunk_iter:
                    callback(chunk, kwargs["blocksize"], None, None)
                return result

            stream.__enter__ = patched_enter
            return stream

        mock_sd.InputStream = fake_input_stream

        result = record_audio(sample_rate=16000, silence_duration=2.0, max_duration=10.0)

        assert isinstance(result, bytes)
        assert len(result) > 44  # WAV header is 44 bytes

        buf = io.BytesIO(result)
        rate, data = wavfile.read(buf)
        assert rate == 16000
        assert data.dtype == np.int16

    @patch("claude_voice_input.recorder.sd")
    def test_stops_on_max_duration(self, mock_sd):
        """Recording should stop when max_duration is reached."""
        from claude_voice_input.recorder import record_audio

        # All loud chunks — never silent, should hit max_duration
        audio_chunks = self._make_audio_chunks(200, amplitude=0.5)
        chunk_iter = iter(audio_chunks)

        class FakeStream:
            def __enter__(self_stream):
                return self_stream

            def __exit__(self_stream, *args):
                pass

        def fake_input_stream(**kwargs):
            callback = kwargs["callback"]
            stream = FakeStream()
            original_enter = stream.__enter__

            def patched_enter():
                result = original_enter()
                for chunk in chunk_iter:
                    callback(chunk, kwargs["blocksize"], None, None)
                return result

            stream.__enter__ = patched_enter
            return stream

        mock_sd.InputStream = fake_input_stream

        result = record_audio(sample_rate=16000, max_duration=5.0)
        assert isinstance(result, bytes)

    def test_wav_output_format(self):
        """WAV output should be mono int16 at expected sample rate."""
        sample_rate = 16000
        samples = np.sin(np.linspace(0, 1, sample_rate)).astype(np.float32)
        audio_int16 = (samples * 32767).astype(np.int16)

        buf = io.BytesIO()
        wavfile.write(buf, sample_rate, audio_int16)
        buf.seek(0)

        rate, data = wavfile.read(buf)
        assert rate == sample_rate
        assert data.dtype == np.int16
        assert len(data) == sample_rate
