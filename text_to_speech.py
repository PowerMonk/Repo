import subprocess
import sys
from pathlib import Path


class TextToSpeech:
    def __init__(
        self,
        model_path: str = "models/es_ES-sharvard-medium.onnx",
        sample_rate: int = 22050,
    ) -> None:
        self.model_path = Path(model_path)
        self.sample_rate = sample_rate

    def speak(self, text: str) -> None:
        if not self.model_path.exists():
            raise FileNotFoundError(f"TTS model not found: {self.model_path}")

        normalized_text = " ".join(text.split())
        if not normalized_text:
            return

        command = (
            f'"{sys.executable}" -m piper '
            f'--model "{self.model_path}" '
            '--output-raw | '
            f'ffplay -loglevel error -ar {self.sample_rate} -f s16le -i - -nodisp -autoexit'
        )

        result = subprocess.run(
            command,
            input=normalized_text,
            text=True,
            shell=True,
            capture_output=True,
            encoding="utf-8",
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "TTS playback failed")
