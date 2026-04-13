# Repo Voice Pipeline — Copilot Instructions

## Project Overview

This project implements a real-time conversational voice pipeline for a robot named **Repo**.

The system captures audio from a microphone, transcribes speech using Whisper on GPU, generates responses using a local LLM (Gemma), and converts those responses into speech using a Text-to-Speech engine. The output may also trigger robot actions.

Primary interaction:

User speaks
→ Speech-to-Text
→ LLM generates response
→ Robot speaks response
→ Optional robot movement

The architecture starts with a simple **batch-based MVP**, but the system is designed to transition quickly into **near real-time streaming interaction**.

Flexibility is important: components may change as performance and reliability requirements become clearer.

---

# Current System Status

The following components are already working:

- Python environment configured
- GPU acceleration working
- Whisper transcription working with GPU
- cuBLAS DLL path configured
- Transcription pipeline validated
- Local execution confirmed

The system currently runs in batch mode.

Example:

User speaks
→ audio file saved
→ transcription executed
→ text printed

This is the functional baseline.

---

# Primary Goal

Build a modular, local-first conversational voice system for the robot.

The system must:

- Run locally
- Use GPU acceleration
- Support natural conversation
- Generate spoken responses
- Support incremental upgrades
- Transition to streaming interaction soon

---

# Core Interaction Loop

The robot must behave conversationally.

Pipeline:

1. Listen for speech
2. Detect wake word
3. Record audio
4. Transcribe speech
5. Generate response using LLM
6. Clean response text
7. Speak response
8. Optionally execute robot action

Conceptual flow:

Microphone
→ Wake word detection
→ Audio capture
→ Speech-to-Text
→ LLM response generation
→ Text cleanup
→ Text-to-Speech
→ Robot response

---

# Wake Word Requirement

The system must support a wake word.

Example wake word:

Repo

Behavior:

If wake word not detected:

Ignore audio

If wake word detected:

Start processing speech

The wake word system must be:

Lightweight
Fast
Interruptible

The wake word detection may initially be implemented using simple text matching after transcription.

Example:

If transcription starts with:

Repo

Then:

Continue processing

Otherwise:

Ignore

---

# Streaming Requirement

Streaming is not optional long-term — it is the next milestone after the MVP.

Initial implementation:

Batch processing

Next implementation:

Short audio chunks

Final implementation:

Continuous streaming interaction

Streaming must:

Reduce latency
Allow interruption
Support continuous listening

Streaming is expected to be implemented soon.

---

# Core Modules

The system must be structured into clear modules.

Do not merge responsibilities.

---

## audio_input.py

Responsible for:

- Capturing microphone audio
- Managing recording sessions
- Handling streaming audio chunks
- Saving audio files
- Managing sample rate configuration

Responsibilities:

- No transcription logic
- No AI logic
- No robot logic

Only audio capture.

---

## speech_to_text.py

Responsible for:

- Loading Whisper model
- Running transcription
- Managing GPU execution
- Returning recognized text

Responsibilities:

- No microphone control
- No robot control
- No response generation

Only speech recognition.

---

## text_processing.py

This module contains the conversational intelligence of the system.

Responsible for:

- Sending transcription text to the local LLM (Gemma)
- Generating conversational responses
- Applying prompt engineering
- Enforcing output formatting rules
- Preparing text for speech output

This module is not just parsing — it is the brain of the system.

---

# LLM Configuration

The system uses:

Local model:

Gemma

Execution environment:

Local inference

The LLM must:

Generate concise responses
Avoid verbose reasoning
Avoid internal thinking output
Be conversational
Be speech-friendly

---

# Prompt Engineering Requirements

The system prompt must enforce:

No chain-of-thought output
No internal reasoning
No markdown formatting
No special symbols that TTS cannot interpret

The model must produce:

Plain conversational text

Never produce:

**bold text**

Markdown formatting

Bullet lists

Code blocks

Special formatting symbols

---

# Output Sanitization Rules

Before sending text to TTS, the system must clean the output.

Remove:

Asterisks
Markdown formatting
Extra whitespace
Special symbols not suitable for speech

Example transformation:

Input:

**Hola, ¿cómo estás?**

Output:

Hola, ¿como estas?

This step is mandatory.

---

## text_to_speech.py

Responsible for:

- Generating speech audio from text
- Playing audio output
- Managing voice settings
- Managing playback timing

Responsibilities:

- No microphone logic
- No transcription logic
- No AI logic

Only speech output.

---

## robot_controller.py

Responsible for:

- Sending movement commands
- Executing robot actions
- Managing hardware communication
- Handling serial communication with ESP32

Responsibilities:

- No audio logic
- No AI logic

Only robot control.

---

## main.py

Responsible for:

- Orchestrating the pipeline
- Managing execution flow
- Coordinating modules
- Managing conversation loop

Responsibilities:

- No heavy logic
- No hardware-specific implementation

Only coordination.

---

# MVP Behavior

The MVP must:

Listen
Transcribe speech
Generate response using LLM
Speak response

Nothing more is required initially.

Correct behavior example:

Listening...
Transcribing...
Generating response...
Speaking response...

---

# Near-Term Milestones

The system will evolve through these steps:

Stage 1:

Batch transcription

Stage 2:

Conversational responses

Stage 3:

Wake word detection

Stage 4:

Short audio chunk processing

Stage 5:

Streaming interaction

These milestones are expected to be implemented in sequence.

---

# Performance Constraints

The system should prioritize:

Stability over speed
Clarity over complexity
Predictability over optimization

Avoid:

Premature optimization
Unnecessary abstraction
Hidden side effects

---

# Error Handling Rules

Always:

Log errors
Fail clearly
Avoid silent failures

Never:

Ignore exceptions
Suppress critical errors
Retry indefinitely without limit

---

# Logging Requirements

Every major step must log its state.

Example:

Listening
Wake word detected
Recording
Transcribing
Generating response
Speaking
Executing command

Logs must be readable and minimal.

---

# Hardware Integration Goal

The robot will eventually respond physically to voice commands.

Possible actions:

Move forward
Move backward
Turn left
Turn right
Stop

Voice commands should trigger these actions.

---

# Development Philosophy

Keep the system:

Simple
Modular
Observable
Replaceable

Every component must be swappable without redesigning the system.

---

# What Copilot Should Do

Assist with:

Small functions
Clear module boundaries
Simple implementations
Readable code

Avoid:

Large monolithic code
Hidden logic
Complex frameworks

---

# System Constraints

The system must run:

Locally
Offline-capable
Without cloud dependencies

---

# Current Implementation Mode

Batch conversational interaction.

Streaming interaction is the next milestone.

---

End of instructions.
