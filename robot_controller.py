import json
import time
from typing import Any
from urllib import error, request


STATE_COMPONENTS = {
    "LISTENING": {"arms": True, "eyes": False, "mouth": False},
    "THINKING": {"arms": False, "eyes": True, "mouth": False},
    "SPEAKING": {"arms": True, "eyes": False, "mouth": True},
    "IDLE": {"arms": False, "eyes": False, "mouth": False},
}


class RobotController:
    """Real-time robot state publisher over HTTP for ESP32 integration."""

    def __init__(
        self,
        ip_address: str = "192.168.4.1",
        timeout_seconds: float = 0.12,
        enabled: bool = True,
        strict: bool = False,
    ) -> None:
        self.base_url = f"http://{ip_address}"
        self.timeout_seconds = timeout_seconds
        self.enabled = enabled
        self.strict = strict

    def _post_json(self, path: str, payload: dict[str, Any]) -> bool:
        if not self.enabled:
            return False

        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds):
                return True
        except (error.URLError, TimeoutError) as err:
            message = f"[robot] Failed POST {path}: {err}"
            if self.strict:
                raise RuntimeError(message) from err
            print(message)
            return False

    def set_state(self, state: str, extra: dict[str, Any] | None = None) -> bool:
        normalized_state = state.upper()
        payload = {
            "state": normalized_state,
            "components": STATE_COMPONENTS.get(normalized_state, {}),
            "timestamp_ms": int(time.time() * 1000),
        }
        if extra:
            payload.update(extra)
        return self._post_json("/state", payload)

    def send_speaking_plan(
        self,
        text: str,
        words_per_second: float = 2.8,
        start_immediately: bool = False,
    ) -> bool:
        words = [token for token in text.split() if token.strip()]
        word_count = len(words)
        estimated_duration_ms = int((word_count / max(words_per_second, 0.1)) * 1000)
        tick_ms = max(90, min(260, int(estimated_duration_ms / max(word_count, 1))))

        payload = {
            "word_count": word_count,
            "estimated_duration_ms": estimated_duration_ms,
            "mouth_states": ["CLOSED", "HALF_OPEN", "OPEN"],
            "recommended_tick_ms": tick_ms,
            "go": 1 if start_immediately else 0,
            "timestamp_ms": int(time.time() * 1000),
        }
        return self._post_json("/speaking-plan", payload)

    def send_go_signal(self) -> bool:
        payload = {
            "go": 1,
            "timestamp_ms": int(time.time() * 1000),
        }
        return self._post_json("/signal", payload)

    def execute_action(self, action: str) -> None:
        self._post_json(
            "/action",
            {
                "action": action,
                "timestamp_ms": int(time.time() * 1000),
            },
        )
