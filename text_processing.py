import os
import json
import re
import subprocess
import unicodedata
from urllib import error, request


SYSTEM_PROMPT = (
    "You are Repo, a concise conversational robot assistant. "
    "Reply in plain text only. Do not use markdown, bullets, code blocks, quotes, "
    "asterisks, or internal reasoning. Keep replies short and engineer-friendly. "
    "Respond in Spanish with at most 3 sentences. Never output the word Thinking."
)


def detect_and_strip_wake_word(text: str, wake_word: str) -> tuple[bool, str]:
    normalized = text.strip()
    if not normalized:
        return False, ""

    pattern = re.compile(rf"^\s*{re.escape(wake_word)}[,:\-\s]*", re.IGNORECASE)
    if not pattern.search(normalized):
        return False, normalized

    cleaned = pattern.sub("", normalized).strip()
    return True, cleaned or normalized


def build_prompt(user_text: str) -> str:
    return f"{SYSTEM_PROMPT}\n\nUser: {user_text}\nRepo:"


def ask_llm(user_text: str, model: str = "gemma4:e4b", timeout_seconds: int = 60) -> str:
    prompt = build_prompt(user_text)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw)
        text = (parsed.get("response") or "").strip()
        if text:
            return text
    except (error.URLError, TimeoutError, json.JSONDecodeError):
        pass

    env = dict(os.environ)
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt,
        text=True,
        capture_output=True,
        encoding="utf-8",
        timeout=timeout_seconds,
        env=env,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "LLM call failed")

    return result.stdout.strip()


def _strip_reasoning_scaffold(text: str) -> str:
    cleaned = text or ""
    cleaned = re.sub(r"(?is)<think>.*?</think>", " ", cleaned)
    cleaned = re.sub(r"(?is)^.*?\.\.\.\s*done\s+thinking\.\s*", "", cleaned)

    marker_pattern = re.compile(
        r"(?i)(final answer|respuesta final|answer|respuesta)\s*:\s*"
    )
    marker_match = marker_pattern.search(cleaned)
    if marker_match:
        cleaned = cleaned[marker_match.end() :]

    cleaned = re.sub(r"(?i)^\s*thinking\s*\.\.\.\s*", "", cleaned)
    cleaned = re.sub(r"(?im)^\s*thinking process\s*:\s*", "", cleaned)
    cleaned = re.sub(
        r"(?i)here'?s\s+a\s+thinking\s+process\s+to\s+generate\s+the\s+appropriate\s+response\s*:\s*",
        "",
        cleaned,
    )
    cleaned = re.sub(r"(?im)^\s*\d+\.\s+\*\*.*$", "", cleaned)
    cleaned = re.sub(r"(?im)^\s*[\*\-]\s+.*$", "", cleaned)

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", cleaned) if part.strip()]
    if paragraphs:
        cleaned = paragraphs[-1]

    banned_phrases = [
        "thinking process",
        "internal reasoning",
        "analyze the persona",
        "constraints",
        "chain of thought",
        "analyze the request",
        "constraint check",
        "final polish",
        "final output generation",
    ]
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    kept_sentences = [
        sentence
        for sentence in sentences
        if sentence.strip()
        and not any(phrase in sentence.lower() for phrase in banned_phrases)
    ]

    if kept_sentences:
        return " ".join(kept_sentences).strip()

    return ""


def _remove_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _remove_emojis(text: str) -> str:
    return re.sub(
        r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F1E6-\U0001F1FF]",
        "",
        text,
    )


def sanitize_for_speech(text: str, max_chars: int = 280) -> str:
    cleaned = _strip_reasoning_scaffold(text)
    cleaned = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", cleaned)
    cleaned = re.sub(r"[\x00-\x08\x0B-\x1F\x7F]", "", cleaned)
    cleaned = re.sub(r"```[\s\S]*?```", " ", cleaned)
    cleaned = re.sub(r"^[\-\*\u2022\d\.\)\s]+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"[*_`~#<>\[\]\(\){}|]", "", cleaned)
    cleaned = re.sub(r"[\"'\u201c\u201d\u2018\u2019]", "", cleaned)
    cleaned = _remove_emojis(cleaned)
    cleaned = _remove_accents(cleaned)
    cleaned = cleaned.replace("¿", "").replace("¡", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    meta_tokens = [
        "tone/style",
        "forbidden word",
        "current input",
        "language:",
        "length:",
        "constraints",
        "system prompt",
    ]
    if any(token in cleaned.lower() for token in meta_tokens):
        cleaned = ""

    if not cleaned:
        return ""

    if len(cleaned) > max_chars:
        truncated = cleaned[:max_chars].rstrip()
        last_space = truncated.rfind(" ")
        if last_space > int(max_chars * 0.6):
            truncated = truncated[:last_space].rstrip()
        cleaned = truncated
        if not cleaned.endswith((".", "!", "?")):
            cleaned += "."

    return cleaned
