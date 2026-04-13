import subprocess

def ask_llm(prompt):
    result = subprocess.run(
        ["ollama", "run", "gemma4:e4b", ],
        input=prompt,
        text=True,
        capture_output=True,
        encoding="utf-8"
    )

    return result.stdout.strip()

response = ask_llm("Hola, ¿cómo estás?")
print(response)