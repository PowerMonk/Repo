# Repo Voice Pipeline

Local-first conversational voice pipeline for Repo (robot assistant).

Current mode: batch + optional live microphone capture.

## What it does

1. Captures user audio from a file or microphone.
2. Transcribes speech to text with Whisper.
3. Sends real-time robot state updates over HTTP.
4. Optionally checks wake word.
5. Sends transcript to local LLM (Ollama/Gemma).
6. Cleans output text for speech safety.
7. Speaks the response with Piper + ffplay.
8. Leaves room for future robot motor command execution.

## Project flow

Execution flow in the current codebase:

1. Audio input stage: [audio_input.py](audio_input.py)
2. Speech-to-text stage: [speech_to_text.py](speech_to_text.py)
3. Robot state publisher (HTTP): [robot_controller.py](robot_controller.py)
4. Text processing + prompt + sanitization: [text_processing.py](text_processing.py)
5. Text-to-speech playback: [text_to_speech.py](text_to_speech.py)
6. Orchestration of full loop: [main.py](main.py)

## Robot states and behavior

The robot receives one of four global states in real time:

- LISTENING: intended for arm motion only
- THINKING: intended for eye motion only
- SPEAKING: intended for mouth + arm motion
- IDLE: no motion

State endpoint contract (current implementation):

- POST /state
- JSON payload example:

```json
{
  "state": "THINKING",
  "components": {
    "arms": false,
    "eyes": true,
    "mouth": false
  },
  "timestamp_ms": 1760000000000
}
```

Speaking sync helpers (for mouth animation timing):

- POST /speaking-plan: sends word count, estimated duration, mouth states, and a GO bit
- POST /signal: sends `{ "go": 1 }`

Speaking-plan payload example:

```json
{
  "word_count": 24,
  "estimated_duration_ms": 8600,
  "mouth_states": ["CLOSED", "HALF_OPEN", "OPEN"],
  "recommended_tick_ms": 180,
  "go": 1,
  "timestamp_ms": 1760000001000
}
```

These values are intentionally simple so you can tune servo angles/speeds manually on hardware.

## Ollama API path

The LLM call in [text_processing.py](text_processing.py) uses Ollama local HTTP API first:

- URL: `http://127.0.0.1:11434/api/generate`
- Method: POST
- JSON body:

```json
{
  "model": "gemma4:e4b",
  "prompt": "...",
  "stream": false
}
```

Why this path is used:

- Non-stream output is cleaner for deterministic sanitization
- Avoids terminal formatting/noise from CLI streaming output
- Faster integration for robot timing metadata

If the HTTP call fails, code falls back to `ollama run` CLI.

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
- --robot-ip 192.168.4.1: target ESP32 IP (placeholder)
- --robot-timeout-ms 120: request timeout for real-time state updates
- --no-robot: disable robot HTTP calls
- --robot-strict: fail program if robot HTTP requests fail

## Notes

- Test scripts are intentionally kept in repo root while the modular pipeline stabilizes:
  - [test_whisper.py](test_whisper.py)
  - [test_llm.py](test_llm.py)
  - [test_tts.py](test_tts.py)
- If LLM output is empty or unusable after sanitization, the program fails clearly instead of returning hardcoded text.
- ESP32 motor protocol is pending and will be integrated in robot_controller once defined.
