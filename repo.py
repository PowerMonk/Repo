import subprocess
from faster_whisper import WhisperModel
import sys

sys.stdout.reconfigure(encoding="utf-8")

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

def listen():

    segments, info = model.transcribe(
        "audio.wav",
        language="es"
    )

    text = ""

    for segment in segments:
        text += segment.text

    return text


def ask_llm(prompt):

    result = subprocess.run(
        ["ollama", "run", "gemma4:e4b"],
        input=prompt,
        text=True,
        capture_output=True,
        encoding="utf-8"
    )

    return result.stdout


def speak(text):

    command = (
        'echo "' + text + '" | '
        'python -m piper '
        '--model es_ES-sharvard-medium.onnx '
        '--output-raw | '
        'ffplay -ar 22050 -f s16le -i - -nodisp -autoexit'
    )

    subprocess.run(command, shell=True)


while True:

    input("Presiona ENTER para hablar")

    user_text = listen()

    print("Usuario:", user_text)

    response = ask_llm(user_text)

    print("Repo:", response)

    speak(response)