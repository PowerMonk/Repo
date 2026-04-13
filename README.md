# Repo Voice Pipeline

Local-first conversational voice pipeline for Repo (robot assistant).

Current mode: batch + optional live microphone capture.

## What it does

1. Captures user audio from a file or microphone.
2. Transcribes speech to text with Whisper.
3. Optionally checks wake word.
4. Sends transcript to local LLM (Ollama/Gemma).
5. Cleans output text for speech safety.
6. Speaks the response with Piper + ffplay.
7. Leaves room for future robot motor commands (ESP32).

## Project flow

Execution flow in the current codebase:

1. Audio input stage: [audio_input.py](audio_input.py)
2. Speech-to-text stage: [speech_to_text.py](speech_to_text.py)
3. Text processing + prompt + sanitization: [text_processing.py](text_processing.py)
4. Text-to-speech playback: [text_to_speech.py](text_to_speech.py)
5. Orchestration of full loop: [main.py](main.py)
6. Future motor control integration point: [robot_controller.py](robot_controller.py)

## Quick start

Prerequisites:

- Python virtual environment in this repo
- Ollama installed and model available (default: gemma4:e4b)
- ffplay available on PATH
- Piper model file at models/es_ES-sharvard-medium.onnx
- faster-whisper installed

Run from file input:

```powershell
c:/Users/aroml/Repo/.venv/Scripts/python.exe .\main.py --audio-file .\intro.wav
```

Run in live microphone mode:

```powershell
c:/Users/aroml/Repo/.venv/Scripts/python.exe .\main.py --live
```

Live mode behavior:

1. Program asks: are you ready to talk
2. Press Enter to start recording
3. Speak normally
4. Press Enter again to stop (or wait for max seconds)
5. STT + LLM + TTS pipeline runs

Run without speech output:

```powershell
c:/Users/aroml/Repo/.venv/Scripts/python.exe .\main.py --audio-file .\intro.wav --no-tts
```

## Useful options

- --wake-word repo: require wake word at transcript start
- --no-wake-word: disable wake-word filtering
- --llm-model gemma4:e4b: choose Ollama model
- --live: record from microphone
- --recording-file audio.wav: output file for live recording
- --max-record-seconds 25: safety cap for live recording length

## Notes

- Test scripts are intentionally kept in repo root while the modular pipeline stabilizes:
  - [test_whisper.py](test_whisper.py)
  - [test_llm.py](test_llm.py)
  - [test_tts.py](test_tts.py)
- If LLM output is empty or unusable after sanitization, the program fails clearly instead of returning hardcoded text.
- ESP32 motor protocol is pending and will be integrated in robot_controller once defined.
