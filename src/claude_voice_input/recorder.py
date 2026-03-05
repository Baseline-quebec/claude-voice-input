"""Audio recording with silence detection."""

import io
import queue
import numpy as np
import sounddevice as sd
from scipy.io import wavfile


def record_audio(
    sample_rate: int = 16000,
    silence_threshold: float = 0.01,
    silence_duration: float = 2.0,
    max_duration: float = 120.0,
) -> bytes:
    """Record audio from the default microphone until silence is detected.

    Returns WAV file content as bytes.
    """
    audio_queue: queue.Queue[np.ndarray] = queue.Queue()
    recording = True

    def callback(indata, frames, time, status):
        if recording:
            audio_queue.put(indata.copy())

    chunks: list[np.ndarray] = []
    silent_chunks = 0
    chunks_per_second = int(sample_rate / 1024)
    silent_chunks_threshold = int(silence_duration * chunks_per_second)
    max_chunks = int(max_duration * chunks_per_second)

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        blocksize=1024,
        callback=callback,
    ):
        while len(chunks) < max_chunks:
            chunk = audio_queue.get()
            chunks.append(chunk)

            rms = np.sqrt(np.mean(chunk**2))
            if rms < silence_threshold:
                silent_chunks += 1
            else:
                silent_chunks = 0

            # Only stop on silence after we've captured at least some audio
            if silent_chunks >= silent_chunks_threshold and len(chunks) > chunks_per_second:
                break

    recording = False

    if not chunks:
        raise RuntimeError("No audio captured.")

    audio_data = np.concatenate(chunks, axis=0)
    # Convert float32 [-1, 1] to int16
    audio_int16 = (audio_data * 32767).astype(np.int16)

    buffer = io.BytesIO()
    wavfile.write(buffer, sample_rate, audio_int16)
    return buffer.getvalue()
