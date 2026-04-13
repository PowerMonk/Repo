import argparse

from audio_input import record_microphone_until_enter, select_audio_source
from speech_to_text import SpeechToText
from text_processing import ask_llm, detect_and_strip_wake_word, sanitize_for_speech
from text_to_speech import TextToSpeech


def run_once(
    audio_file: str | None,
    live_mode: bool,
    recording_file: str,
    max_record_seconds: int,
    model_size: str,
    language: str,
    llm_model: str,
    wake_word: str | None,
    no_tts: bool,
) -> None:
    print("[main] Listening...")
    if live_mode:
        source = record_microphone_until_enter(
            output_path=recording_file,
            sample_rate=16000,
            channels=1,
            max_seconds=max_record_seconds,
        )
    else:
        source = select_audio_source(audio_file)
    print(f"[main] Audio source: {source}")

    stt = SpeechToText(model_size=model_size, language=language)

    print("[main] Transcribing...")
    user_text = stt.transcribe_file(source)
    if not user_text:
        print("[main] No speech detected.")
        return

    print(f"[user] {user_text}")

    if wake_word:
        detected, stripped_text = detect_and_strip_wake_word(user_text, wake_word)
        if not detected:
            print(f"[main] Wake word not detected ({wake_word}). Ignoring audio.")
            return
        user_text = stripped_text
        print(f"[main] Wake word detected. Prompt text: {user_text}")

    print("[main] Generating response...")
    raw_response = ask_llm(user_text, model=llm_model)
    clean_response = sanitize_for_speech(raw_response)

    if not clean_response:
        print("[main] First response unusable after sanitization. Retrying once...")
        retry_text = (
            "Responde en espanol con maximo 3 frases. "
            "Solo entrega la respuesta final, sin formato ni explicaciones internas. "
            f"Pregunta: {user_text}"
        )
        retry_raw_response = ask_llm(retry_text, model=llm_model)
        clean_response = sanitize_for_speech(retry_raw_response)

    if not clean_response:
        print("[main] Empty model response after sanitization.")
        return

    print(f"[repo] {clean_response}")

    if no_tts:
        print("[main] TTS disabled (--no-tts).")
        return

    print("[main] Speaking response...")
    tts = TextToSpeech()
    tts.speak(clean_response)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repo voice pipeline MVP")
    parser.add_argument("--audio-file", default=None, help="Path to a .wav file (default: intro.wav or audio.wav)")
    parser.add_argument("--live", action="store_true", help="Capture audio from microphone instead of file")
    parser.add_argument("--recording-file", default="audio.wav", help="Output .wav path used in --live mode")
    parser.add_argument("--max-record-seconds", type=int, default=25, help="Safety limit for live recording")
    parser.add_argument("--model-size", default="small", help="Whisper model size")
    parser.add_argument("--language", default="es", help="Transcription language")
    parser.add_argument("--llm-model", default="gemma4:e4b", help="Ollama model name")
    parser.add_argument("--wake-word", default=None, help="Optional wake word to enforce at the start of transcript")
    parser.add_argument("--no-wake-word", action="store_true", help="Disable wake-word filtering")
    parser.add_argument("--no-tts", action="store_true", help="Skip speech playback")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    wake_word = None if args.no_wake_word else (args.wake_word.strip() if args.wake_word else None)
    run_once(
        audio_file=args.audio_file,
        live_mode=args.live,
        recording_file=args.recording_file,
        max_record_seconds=args.max_record_seconds,
        model_size=args.model_size,
        language=args.language,
        llm_model=args.llm_model,
        wake_word=wake_word,
        no_tts=args.no_tts,
    )


if __name__ == "__main__":
    main()
