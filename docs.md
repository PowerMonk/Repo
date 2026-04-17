# Repo Robot Technical Manual

## 1. Document purpose

This document is the technical reference for the Repo robot voice system. It is designed to be:

- readable by humans (engineering manual style)
- parseable by LLMs (clear sections, explicit contracts, deterministic schemas)

This manual covers the full codebase currently implemented in this repository, including:

- Python conversational pipeline (STT -> LLM -> TTS)
- ESP32 firmware state machine and motor control server
- HTTP contract between Python and ESP32
- operational flows, timing model, and troubleshooting guidance

---

## 2. System architecture

At runtime, the system is split into two cooperating runtimes:

1. Host runtime (PC, Python):

- captures/loads audio
- transcribes speech
- generates response text
- sanitizes text for speech
- synthesizes and plays speech audio
- sends robot state and speaking timing metadata to ESP32

2. Device runtime (ESP32, Arduino):

- exposes HTTP endpoints
- runs servo state machine
- animates mouth/arms/eyes based on state and speaking plan

High-level flow:

1. Audio in (file or microphone)
2. STT (Whisper)
3. Optional wake-word gate
4. LLM inference (Ollama)
5. Text sanitization
6. Robot state -> SPEAKING and speaking plan sent
7. TTS synthesis + playback (Piper + ffplay)
8. GO signal sent at audio start callback
9. Robot transitions back to IDLE at turn end

---

## 3. Repository map

### 3.1 Core runtime files

- `main.py`: orchestration entrypoint and CLI
- `audio_input.py`: file selection + live microphone recording
- `speech_to_text.py`: faster-whisper wrapper with CUDA fallback logic
- `text_processing.py`: prompting, wake-word parsing, sanitization
- `text_to_speech.py`: piper synthesis and ffplay playback bridge
- `robot_controller.py`: outbound HTTP client for ESP32 state updates
- `repo.ino`: ESP32 AP + HTTP server + servo control state machine

### 3.2 Auxiliary files

- `README.md`: quick-start style summary
- `docs.md`: this full technical manual
- `run.ps1`: legacy helper for CUDA DLL path setup
- `repo.py`: legacy monolithic prototype script

### 3.3 Test scripts

- `tests/test_whisper.py`: isolated STT test
- `tests/test_llm.py`: isolated LLM call test
- `tests/test_tts.py`: isolated TTS output test
- `range_test.ino`: manual movement-range hardware probing sketch

---

## 4. Python pipeline internals

## 4.1 Orchestrator (`main.py`)

`run_once(...)` implements one full turn.

Execution sequence:

1. `robot.set_state("LISTENING")`
2. Acquire audio source:

- `--live`: microphone record until Enter or max seconds
- else: explicit `--audio-file` or default candidate

3. STT transcription (`SpeechToText.transcribe_file`)
4. Optional wake-word enforcement
5. `robot.set_state("THINKING")`
6. LLM generation (`ask_llm`)
7. Text cleanup (`sanitize_for_speech`)
8. One retry with stricter instruction if first sanitized output is empty
9. If no usable text: fail clearly for this turn
10. If `--no-tts`: stop after printing response
11. `robot.set_state("SPEAKING")`
12. Send speaking plan with `go=0`
13. Start TTS playback; on playback start callback -> send GO signal
14. `finally`: `robot.set_state("IDLE")` always executes

CLI options:

- `--audio-file`
- `--live`
- `--recording-file`
- `--max-record-seconds`
- `--model-size`
- `--language`
- `--llm-model`
- `--wake-word`
- `--no-wake-word`
- `--no-tts`
- `--robot-ip`
- `--robot-timeout-ms`
- `--no-robot`
- `--robot-strict`

---

## 4.2 Audio ingestion (`audio_input.py`)

### File mode

`select_audio_source(explicit_path=None)`:

- validates provided path exists and is `.wav`
- otherwise tries defaults in order:
  1. `intro.wav`
  2. `audio.wav`
- raises clear exception if nothing available

### Live mode

`record_microphone_until_enter(...)`:

- prompts Enter to start
- records from default input using `sounddevice.InputStream`
- stops on second Enter or hard timeout (`max_seconds`)
- writes PCM 16-bit WAV via `soundfile`

Recording defaults:

- sample rate: 16000 Hz
- channels: 1 (mono)
- dtype: int16

---

## 4.3 Speech-to-text (`speech_to_text.py`)

`SpeechToText` wraps `faster_whisper.WhisperModel`.

Initialization behavior:

1. attempts CUDA DLL path registration on Windows
2. tries GPU model load:

- device: `cuda`
- compute type: `float16`

3. on failure, falls back to CPU:

- device: `cpu`
- compute type: `int8`

Transcription behavior:

- language parameter defaults to `es`
- output text is segment-joined and whitespace-normalized

---

## 4.4 LLM and sanitization (`text_processing.py`)

### Prompting

- system prompt enforces concise plain-text Spanish output
- forbids markdown, chain-of-thought style output, and formatting artifacts

### LLM transport strategy

Primary path:

- Ollama HTTP API
- endpoint: `http://127.0.0.1:11434/api/generate`
- request uses `stream=false` for deterministic output capture

Fallback path:

- CLI call: `ollama run <model>`

### Wake-word gate

`detect_and_strip_wake_word(text, wake_word)`:

- checks prefix match (case-insensitive)
- strips wake-word token and punctuation from leading position

### Output cleanup pipeline

`sanitize_for_speech(...)` performs:

1. reasoning scaffold stripping (`thinking`, `<think>`, etc.)
2. markdown and list-marker removal
3. control/ANSI code removal
4. quote/asterisk/symbol cleanup
5. emoji removal
6. accent removal and punctuation normalization for speech
7. max-char truncation with word-boundary preference

Design intent:

- prefer predictable speech-safe text over stylistic richness
- fail safely by returning empty string when output is unusable

---

## 4.5 TTS path (`text_to_speech.py`)

`TextToSpeech.speak(text, on_audio_start=None)`:

1. validates model file exists
2. starts Piper process:

- `python -m piper --model <onnx> --output-raw`

3. starts ffplay process consuming Piper raw stdout:

- format: `s16le`
- sample rate: configurable (default 22050)

4. writes normalized text to Piper stdin
5. executes `on_audio_start()` callback right after playback pipeline starts
6. waits for both processes and raises on failure

Key synchronization feature:

- GO signal can be emitted by callback close to real playback start, reducing visual/audio desync versus sending GO immediately after LLM output.

---

## 4.6 Robot HTTP client (`robot_controller.py`)

`RobotController` is a thin non-async POST client.

Methods:

- `set_state(state, extra=None)` -> POST `/state`
- `send_speaking_plan(text, words_per_second=2.8, start_immediately=False)` -> POST `/speaking-plan`
- `send_go_signal()` -> POST `/signal`
- `execute_action(action)` -> POST `/action`

Speaking plan derivations:

- `word_count`: token count from final sanitized text
- `estimated_duration_ms`: derived from `word_count / words_per_second`
- `recommended_tick_ms`: bounded interval in [90, 260]
- `go`: optional immediate-start bit

Failure behavior:

- default: print warning and continue
- strict mode: raise exception if POST fails

---

## 5. ESP32 firmware internals (`repo.ino`)

## 5.1 Network role

- ESP32 runs in Access Point mode:
  - SSID: `RepoRobot`
  - password: `12345678`
- HTTP server on port 80

---

## 5.2 Current pin map and kinematics

Pin map:

- mouth: pin 15
- left arm: pin 4
- right arm: pin 17
- left eye: pin 21
- right eye: pin 18

Configured ranges:

- mouth: closed=100, half=112, open=125
- arms: min=30, center=90, max=150
- left eye: min=40, center=90, max=120
- right eye: min=50, center=90, max=140

Servo timing metadata:

- mouth step delay: 8 ms (smooth mode)
- arm step delay: 5 ms
- eye step delay: 3 ms

---

## 5.3 State model

`RobotState`:

- `STATE_IDLE`
- `STATE_LISTENING`
- `STATE_THINKING`
- `STATE_SPEAKING`

State behavior:

- LISTENING:
  - arms animated with triangle wave
  - eyes centered
  - mouth closed
- THINKING:
  - eyes animated through configured ranges
  - arms center
  - mouth closed
- SPEAKING:
  - requires `speakingPlan.active=true` to animate speaking
  - mouth animates between closed/half/open by random ticks
  - arms animated
  - eyes centered
- IDLE:
  - speaking inactive
  - targets frozen to current body positions except mouth target closed

---

## 5.4 Motion primitives

Core helpers:

- `setTarget(axis, target)`
- `stepAxis(axis, smooth=false)`
  - smooth mode: degree-by-degree using `stepDelayMs`
  - non-smooth mode: immediate jump to target
- `triangleWave(nowMs, periodMs, min, max)`

Applied in loop:

- mouth uses smooth stepping (`stepAxis(mouthAxis, true)`)
- arms and eyes use immediate stepping (`stepAxis(axis)`)

This mixed mode provides:

- smoother mouth movement
- snappier expressive limbs/eyes

---

## 5.5 Speaking plan logic

`SpeakingPlan` fields:

- `wordCount`
- `durationMs`
- `tickMs`
- `active`
- `startedAtMs`
- `lastMouthTickMs`

Speaking update sequence:

1. if inactive -> mouth target closed
2. enforce startup delay:

- `START_DELAY_MS = 2000`

3. after delay, elapsed speaking time is measured against `durationMs`
4. while active, mouth state changes every `tickMs` with random selection:

- 20% closed
- 40% half
- 40% open

5. when elapsed >= duration -> deactivate and close mouth

Important implication:

- there is a firmware-level fixed 2-second delay before mouth animation starts after GO.
- if tighter sync is needed, reduce or remove `START_DELAY_MS`.

---

## 5.6 HTTP handlers on ESP32

### POST `/state`

Input JSON:

```json
{
  "state": "LISTENING|THINKING|SPEAKING|IDLE"
}
```

Behavior:

- validates body and `state`
- applies robot state transition
- returns `200 OK` on success

### POST `/speaking-plan`

Input JSON:

```json
{
  "word_count": 24,
  "estimated_duration_ms": 9000,
  "recommended_tick_ms": 140,
  "go": 0
}
```

Behavior:

- stores plan values with bounds
- if `go==1`, activates speaking immediately
- otherwise waits for `/signal`

### POST `/signal`

Input JSON (optional):

```json
{
  "go": 1
}
```

Behavior:

- if go is 1 (or omitted), sets speaking active and resets speaking timers

### POST `/action`

Input JSON:

```json
{
  "action": "OPEN|HALF|CLOSE|LISTENING|THINKING|SPEAKING|IDLE"
}
```

Behavior:

- OPEN/HALF/CLOSE directly affect mouth target
- state tokens map to state transitions

---

## 6. End-to-end timing and synchronization

## 6.1 Current timing model

1. Python sends `SPEAKING` state and speaking plan (`go=0`)
2. Python starts TTS playback chain
3. Python callback sends `/signal` GO near playback start
4. ESP32 receives GO and starts speaking timeline
5. ESP32 speaking animation itself waits `START_DELAY_MS` (currently 2000 ms)

Net effect:

- sync improved versus response-time GO
- but firmware still intentionally offsets mouth animation by 2 seconds

If near-lip-sync is required:

- set `START_DELAY_MS` to ~0-300 ms in firmware
- keep GO callback strategy in Python

---

## 7. Operational flows

## 7.1 Typical live run

1. connect PC to ESP32 AP
2. run:

```powershell
c:/Users/aroml/Repo/.venv/Scripts/python.exe .\main.py --live --robot-ip 192.168.4.1
```

3. press Enter to start recording
4. speak
5. press Enter to stop (or timeout)
6. observe LISTENING -> THINKING -> SPEAKING -> IDLE sequence

## 7.2 File-based run

```powershell
c:/Users/aroml/Repo/.venv/Scripts/python.exe .\main.py --audio-file .\intro.wav --robot-ip 192.168.4.1
```

## 7.3 TTS-disabled diagnostic run

```powershell
c:/Users/aroml/Repo/.venv/Scripts/python.exe .\main.py --audio-file .\intro.wav --no-tts --robot-ip 192.168.4.1
```

---

## 8. Manual API test suite (offline AP mode)

PowerShell setup:

```powershell
$ip = "192.168.4.1"
```

Mouth actuator test:

```powershell
Invoke-RestMethod -Uri "http://$ip/action" -Method Post -Body (@{action="OPEN"} | ConvertTo-Json -Compress) -ContentType "application/json"
Invoke-RestMethod -Uri "http://$ip/action" -Method Post -Body (@{action="HALF"} | ConvertTo-Json -Compress) -ContentType "application/json"
Invoke-RestMethod -Uri "http://$ip/action" -Method Post -Body (@{action="CLOSE"} | ConvertTo-Json -Compress) -ContentType "application/json"
```

State transitions:

```powershell
Invoke-RestMethod -Uri "http://$ip/state" -Method Post -Body (@{state="LISTENING"} | ConvertTo-Json -Compress) -ContentType "application/json"
Invoke-RestMethod -Uri "http://$ip/state" -Method Post -Body (@{state="THINKING"} | ConvertTo-Json -Compress) -ContentType "application/json"
Invoke-RestMethod -Uri "http://$ip/state" -Method Post -Body (@{state="SPEAKING"} | ConvertTo-Json -Compress) -ContentType "application/json"
Invoke-RestMethod -Uri "http://$ip/state" -Method Post -Body (@{state="IDLE"} | ConvertTo-Json -Compress) -ContentType "application/json"
```

Speaking plan test:

```powershell
Invoke-RestMethod -Uri "http://$ip/speaking-plan" -Method Post -Body (@{word_count=24;estimated_duration_ms=9000;recommended_tick_ms=140;go=0} | ConvertTo-Json -Compress) -ContentType "application/json"
Invoke-RestMethod -Uri "http://$ip/signal" -Method Post -Body (@{go=1} | ConvertTo-Json -Compress) -ContentType "application/json"
```

---

## 9. Logging and observability

Python log markers:

- `[main] Listening...`
- `[main] Transcribing...`
- `[main] Generating response...`
- `[main] Speaking response...`
- `[repo] <response>`

ESP32 serial markers:

- `SERVO ATTACHED:` or `SERVO ATTACH FAILED:`
- `STATE -> ...`
- `STATE PAYLOAD:`
- `SPEAKING PLAN PAYLOAD:`
- `GO SIGNAL RECEIVED`

Recommendation:

- always keep serial monitor open while validating motion behavior
- correlate serial timestamps with POST command times

---

## 10. Failure modes and diagnostics

## 10.1 HTTP returns OK but no motion

Most likely causes:

- servo power rail issue (brownout under load)
- ground reference not shared across ESP32 and servo supply
- pin wiring mismatch against firmware map
- servo mechanically jammed or stalled

Diagnostic order:

1. verify serial shows handler logs and state transitions
2. test `/action OPEN/HALF/CLOSE` first
3. verify each servo channel individually with a minimal single-servo sketch
4. only then test multi-state animation logic

## 10.2 STT works but no response audio

Check:

- piper model file exists at configured path
- ffplay available in PATH
- `--no-tts` not enabled

## 10.3 LLM output rejected by sanitizer

Behavior is intentional for invalid outputs.

- pipeline retries once with stricter instruction
- if still unusable, turn exits with clear log

---

## 11. Security and deployment notes

Current AP credentials are hardcoded and should be treated as development defaults.

Recommendations for production:

- rotate AP credentials
- add endpoint auth token or HMAC
- add request rate limiting on ESP32 handlers
- externalize pin map and kinematics in config

---

## 12. Extension points

1. Motor abstraction layer in firmware:

- split mouth, arms, eyes into dedicated controller units

2. Better lip-sync model:

- derive mouth-open probability from phoneme or energy envelope
- remove fixed startup delay in firmware

3. Streaming STT loop:

- move from turn-based capture to chunked continuous listening

4. Command semantics:

- parse LLM output for explicit robot actions and route through `/action`

5. Telemetry channel:

- add `/status` endpoint with current state, servo targets, and uptime

---

## 13. Known legacy/deprecated paths

- `repo.py`: legacy monolithic prototype, not current orchestrator
- `run.ps1`: legacy helper for CUDA DLL PATH setup

These are retained for reference but should not be treated as canonical runtime entrypoints.

---

## 14. Canonical runtime entrypoint

Use `main.py` as the authoritative host-side runtime.
Use `repo.ino` as the authoritative firmware runtime.

This pair defines the current production behavior of the local voice + robot-state pipeline.
