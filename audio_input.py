import threading
import time
from pathlib import Path

import numpy as np

try:
    import sounddevice as sd
    import soundfile as sf
except ImportError:
    sd = None
    sf = None


DEFAULT_AUDIO_CANDIDATES = ("intro.wav", "audio.wav")


def select_audio_source(explicit_path: str | None = None) -> Path:
    """Return the audio file path to process for the current batch turn."""
    if explicit_path:
        candidate = Path(explicit_path)
        if not candidate.exists():
            raise FileNotFoundError(f"Audio file not found: {candidate}")
        if candidate.suffix.lower() != ".wav":
            raise ValueError("Only .wav files are supported in this MVP.")
        return candidate

    for file_name in DEFAULT_AUDIO_CANDIDATES:
        candidate = Path(file_name)
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "No default audio source found. Expected one of: "
        + ", ".join(DEFAULT_AUDIO_CANDIDATES)
    )


def record_microphone_until_enter(
    output_path: str = "audio.wav",
    sample_rate: int = 16000,
    channels: int = 1,
    max_seconds: int = 25,
) -> Path:
    """Record from default microphone after Enter, stop on Enter or max_seconds."""
    if sd is None or sf is None:
        raise RuntimeError(
            "Live recording requires sounddevice and soundfile. "
            "Install them in your virtual environment."
        )

    destination = Path(output_path)
    print("[audio] Are you ready to talk? Press ENTER to start recording.")
    input()
    print(f"[audio] Recording now. Press ENTER to stop (max {max_seconds}s).")

    frames: list[np.ndarray] = []
    stop_event = threading.Event()

    def _wait_for_enter() -> None:
        input()
        stop_event.set()

    def _callback(indata, frame_count, time_info, status) -> None:
        if status:
            print(f"[audio] Stream status: {status}")
        frames.append(indata.copy())

    stopper = threading.Thread(target=_wait_for_enter, daemon=True)
    stopper.start()

    start = time.monotonic()
    with sd.InputStream(
        samplerate=sample_rate,
        channels=channels,
        dtype="int16",
        callback=_callback,
    ):
        while not stop_event.is_set():
            elapsed = time.monotonic() - start
            if elapsed >= max_seconds:
                print(f"[audio] Max recording time reached ({max_seconds}s).")
                stop_event.set()
                break
            sd.sleep(100)

    if not frames:
        raise RuntimeError("No audio was captured from microphone.")

    audio = np.concatenate(frames, axis=0)
    sf.write(destination, audio, sample_rate, subtype="PCM_16")
    print(f"[audio] Saved recording to: {destination}")
    return destination
