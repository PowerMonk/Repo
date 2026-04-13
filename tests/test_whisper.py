import os

# Rutas donde están las DLL de CUDA 12 instaladas por pip
os.add_dll_directory(
    r"C:\Users\aroml\AppData\Local\Programs\Python\Python312\Lib\site-packages\nvidia\cublas\bin"
)

# (opcional pero recomendado)
# os.add_dll_directory(
#  r"C:\Users\aroml\AppData\Local\Programs\Python\Python312\Lib\site-packages\nvidia\cudnn\bin"
# ) 

from faster_whisper import WhisperModel

print("Loading model...")

model = WhisperModel(
    "small",
    device="cuda",
    compute_type="float16"
)

print("Transcribing...")

segments, info = model.transcribe(
    "audio.wav",
    language="es"
)

for segment in segments:
    print(segment.text)

print("Done.")