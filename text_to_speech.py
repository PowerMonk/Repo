import subprocess
import sys
from collections.abc import Callable
from pathlib import Path


class TextToSpeech:
    def __init__(
        self,
        model_path: str = "models/es_ES-sharvard-medium.onnx",
        sample_rate: int = 22050,
    ) -> None:
        self.model_path = Path(model_path)
        self.sample_rate = sample_rate

    def speak(self, text: str, on_audio_start: Callable[[], None] | None = None) -> None:
        if not self.model_path.exists():
            raise FileNotFoundError(f"TTS model not found: {self.model_path}")

        normalized_text = " ".join(text.split())
        if not normalized_text:
            return

        piper_cmd = [
            sys.executable,
            "-m",
            "piper",
            "--model",
            str(self.model_path),
            "--output-raw",
        ]
        ffplay_cmd = [
            "ffplay",
            "-loglevel",
            "error",
            "-ar",
            str(self.sample_rate),
            "-f",
            "s16le",
            "-i",
            "-",
            "-nodisp",
            "-autoexit",
        ]

        piper_proc = subprocess.Popen(
            piper_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        ffplay_proc = None

        try:
            ffplay_proc = subprocess.Popen(
                ffplay_cmd,
                stdin=piper_proc.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )

            if piper_proc.stdout is not None:
                piper_proc.stdout.close()

            if piper_proc.stdin is None:
                raise RuntimeError("Piper stdin is unavailable")

            piper_proc.stdin.write((normalized_text + "\n").encode("utf-8"))
            piper_proc.stdin.close()

            if on_audio_start is not None:
                on_audio_start()

            ffplay_stderr = ffplay_proc.communicate()[1]
            piper_proc.wait()
            piper_stderr = b""
            if piper_proc.stderr is not None:
                piper_stderr = piper_proc.stderr.read()

            if piper_proc.returncode != 0:
                raise RuntimeError((piper_stderr or b"").decode("utf-8", errors="replace") or "Piper synthesis failed")

            if ffplay_proc.returncode != 0:
                raise RuntimeError((ffplay_stderr or b"").decode("utf-8", errors="replace") or "ffplay playback failed")
        finally:
            if piper_proc.poll() is None:
                piper_proc.kill()
            if ffplay_proc is not None and ffplay_proc.poll() is None:
                ffplay_proc.kill()
