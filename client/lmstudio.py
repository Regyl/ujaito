"""Typed client for a local LM Studio OpenAI-compatible server."""

from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from exception.lmstudio import LmStudioError
from model.assessment import FitAssessment
from util.annotations import timed

DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_MODEL = "google/gemma-4-e4b"
TIMEOUT_SECONDS = 180

_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


class LmStudioClient:
    """Asks a local model whether a background can answer a question."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_token: str | None = None,
    ) -> None:
        configured_url = base_url if base_url is not None else os.getenv("LM_STUDIO_BASE_URL")
        configured_model = model if model is not None else os.getenv("LM_STUDIO_MODEL")
        configured_token = api_token if api_token is not None else os.getenv("LM_STUDIO_API_TOKEN")
        if not configured_token or not configured_token.strip():
            raise LmStudioError("LM_STUDIO_API_TOKEN is required", status=0)
        self._base_url = (configured_url or DEFAULT_BASE_URL).rstrip("/")
        self._model = configured_model or DEFAULT_MODEL
        self._api_token = configured_token.strip()

    @timed
    def assess(self, question: str, background: str) -> FitAssessment:
        body = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": "Respond with JSON only. Do not add prose around the JSON object.",
                },
                {"role": "user", "content": _prompt(question, background)},
            ],
        }
        data = json.dumps(body).encode("utf-8")
        request = Request(
            f"{self._base_url}/chat/completions",
            data=data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_token}",
            },
            method="POST",
        )
        status, raw = _send(request)
        if status >= 400:
            raise LmStudioError(_error_message(raw) or f"HTTP {status}", status=status)
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError as exc:
            raise LmStudioError("completion response was not JSON", status=500) from exc
        return parse_fit_assessment(_message_content(payload))


def parse_fit_assessment(text: str) -> FitAssessment:
    if not text or not text.strip():
        raise LmStudioError("assessment response was empty", status=500)
    fenced = _FENCE.search(text)
    raw = fenced.group(1) if fenced else text
    if fenced is None:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end < start:
            raise LmStudioError("assessment response was not JSON", status=500)
        raw = raw[start : end + 1]
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LmStudioError("assessment response was not JSON", status=500) from exc
    if not isinstance(payload, dict):
        raise LmStudioError("assessment response was not an object", status=500)
    can_solve = payload.get("can_solve")
    reason = payload.get("reason")
    if not isinstance(can_solve, bool) or not isinstance(reason, str) or not reason.strip():
        raise LmStudioError("assessment response missing required fields", status=500)
    return FitAssessment(can_solve=can_solve, reason=reason.strip())


def _prompt(question: str, background: str) -> str:
    return (
        "Decide whether this candidate can credibly answer the journalist query "
        "from their background alone.\n\n"
        f"Candidate background:\n{background}\n\n"
        f"Question:\n{question}\n\n"
        'Respond with JSON only: {"can_solve": true or false, "reason": "one or two sentences"}'
    )


def _message_content(payload: object) -> str:
    if not isinstance(payload, dict):
        raise LmStudioError("completion response was not an object", status=500)
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise LmStudioError("completion response missing choices", status=500)
    message = choices[0].get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise LmStudioError("completion response missing content", status=500)
    return content


def _send(request: Request) -> tuple[int, bytes]:
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()
    except URLError as exc:
        raise LmStudioError(f"request failed: {exc.reason}", status=0) from exc


def _error_message(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        for key in ("message", "error", "detail"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
    return text
