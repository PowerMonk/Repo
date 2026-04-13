# Propósito: preparar el PATH para poder ejecutar whisper ya que usa CUDA 12.x y yo tengo CUDA 13.X

# Deprecado porque agregué la ruta al PATH del sistema, pero lo dejo por si acaso

$env:PATH = "C:\Users\aroml\AppData\Local\Programs\Python\Python312\Lib\site-packages\nvidia\cublas\bin;" + $env:PATH
python .\test_whisper.py

