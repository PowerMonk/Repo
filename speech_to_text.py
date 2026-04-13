import os
import sys
from pathlib import Path

from faster_whisper import WhisperModel


def configure_cuda_dll_paths() -> None:
    """Register known CUDA DLL paths on Windows when available."""
    if not hasattr(os, "add_dll_directory"):
        return

    candidate_paths = [
        os.environ.get("CUBLAS_DLL_PATH"),
        os.path.join(sys.base_prefix, "Lib", "site-packages", "nvidia", "cublas", "bin"),
        os.path.join(sys.base_prefix, "Lib", "site-packages", "nvidia", "cudnn", "bin"),
    ]

    for raw_path in candidate_paths:
        if not raw_path:
            continue
        if os.path.isdir(raw_path):
            os.add_dll_directory(raw_path)


class SpeechToText:
    def __init__(self, model_size: str = "small", language: str = "es") -> None:
        self.language = language
        configure_cuda_dll_paths()
        self.model = self._load_model(model_size)

    def _load_model(self, model_size: str) -> WhisperModel:
        try:
            print("[stt] Loading Whisper model on CUDA...")
            return WhisperModel(model_size, device="cuda", compute_type="float16")
        except Exception as error:
            print(f"[stt] CUDA unavailable, falling back to CPU int8: {error}")
            return WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe_file(self, audio_path: str | Path) -> str:
        source = str(audio_path)
        segments, _ = self.model.transcribe(source, language=self.language)
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        return text.strip()
