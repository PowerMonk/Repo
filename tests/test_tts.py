import subprocess

def speak(text):

    command = (
        'echo "' + text + '" | '
        'python -m piper '
        '--model models/es_ES-sharvard-medium.onnx '
        '--output-raw | '
        'ffplay -ar 22050 -f s16le -i - -nodisp -autoexit'
    )

    subprocess.run(command, shell=True)

speak("Hola, soy Repo")