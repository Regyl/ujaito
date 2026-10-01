"""Typed client for the Telegram Bot API."""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from exception.telegram import TelegramError
from mapper import connectively_mapper
from model.assessment import AssessedQuestion
from util.annotations import timed

API_URL = "https://api.telegram.org/bot{token}/sendMessage"
TIMEOUT_SECONDS = 30


class TelegramClient:
    """Sends a MarkdownV2 alert for a question the candidate can answer."""

    def __init__(self, bot_token: str | None = None, chat_id: str | None = None) -> None:
        token = bot_token if bot_token is not None else os.getenv("TELEGRAM_BOT_TOKEN")
        chat = chat_id if chat_id is not None else os.getenv("TELEGRAM_CHAT_ID")
        if not token or not token.strip():
            raise TelegramError("TELEGRAM_BOT_TOKEN is required", status=0)
        if chat is None or not str(chat).strip():
            raise TelegramError("TELEGRAM_CHAT_ID is required", status=0)
        self._bot_token = token.strip()
        self._chat_id = str(chat).strip()

    @timed
    def notify(self, item: AssessedQuestion) -> None:
        body = json.dumps(
            {
                "chat_id": self._chat_id,
                "text": connectively_mapper.get_tg_notification(item),
                "parse_mode": "MarkdownV2",
            }
        ).encode("utf-8")
        request = Request(
            API_URL.format(token=self._bot_token),
            data=body,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        status, raw = _send(request)
        if status >= 400:
            raise TelegramError(_error_message(raw) or f"HTTP {status}", status=status)
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError as exc:
            raise TelegramError("send response was not JSON", status=500) from exc
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            raise TelegramError(_error_message(raw) or "send failed", status=status or 500)


def _send(request: Request) -> tuple[int, bytes]:
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()
    except URLError as exc:
        raise TelegramError(f"request failed: {exc.reason}", status=0) from exc


def _error_message(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(payload, dict):
        description = payload.get("description")
        if isinstance(description, str) and description:
            return description
    return text
