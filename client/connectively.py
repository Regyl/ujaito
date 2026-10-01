"""Typed client for the Connectively Free API."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from exception import AuthError, ConnectivelyError, ForbiddenError, ValidationError
from model import LoginRequest, Question
from util.annotations import timed

BASE_URL = "https://www.connectively.us/api/external-users"


class ConnectivelyClient:
    """Typed client for the Connectively Free API.

    The JWT is cached and sent as ``x-access-token``. A 401 on an authenticated
    call clears the cache, logs in again, and retries that call once.
    """

    def __init__(self, base_url: str = BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")
        self._token: str | None = None
        self._credentials: LoginRequest | None = None

    @timed
    def login(self, request: LoginRequest) -> str:
        if not request.username:
            raise ValidationError("username is required", status=400)
        if not 8 <= len(request.password) <= 30:
            raise ValidationError("password must be 8-30 characters", status=400)

        self._credentials = request
        _status, token, _body = self._request(
            "POST",
            "/login",
            body={"username": request.username, "password": request.password},
            auth=False,
        )
        if not token or not token.strip():
            raise AuthError(f"login response missing x-access-token {_body}", status=401)
        self._token = token.strip()
        return self._token

    @timed
    def question_list(self) -> list[Question]:
        query: dict[str, str] | None = None
        _status, _token, body = self._request("GET", "/question-list", query=query)
        payload = json.loads(body.decode("utf-8")) if body else []
        if not isinstance(payload, list):
            raise ConnectivelyError("question list response was not an array", status=500)
        return [_parse_question(item) for item in payload]

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict | None = None,
        query: dict[str, str] | None = None,
        auth: bool = True,
        allow_reauth: bool = True,
    ) -> tuple[int, str | None, bytes]:
        headers = {"Accept": "application/json"}
        data: bytes | None = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if auth:
            if self._token is None:
                self._reauthenticate()
            headers["x-access-token"] = self._token or ""

        url = f"{self._base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"

        status, token, raw = _send(Request(url, data=data, headers=headers, method=method))
        if status == 401 and auth and allow_reauth:
            self._token = None
            self._reauthenticate()
            return self._request(
                method,
                path,
                body=body,
                query=query,
                auth=True,
                allow_reauth=False,
            )
        if status == 400:
            raise ValidationError(_error_message(raw) or "validation error", status=400)
        if status == 401:
            raise AuthError(_error_message(raw) or "unauthorized", status=401)
        if status == 403:
            raise ForbiddenError(_error_message(raw) or "insufficient permissions", status=403)
        if status >= 400:
            raise ConnectivelyError(_error_message(raw) or f"HTTP {status}", status=status)
        return status, token, raw

    def _reauthenticate(self) -> None:
        if self._credentials is None:
            raise AuthError("not logged in", status=401)
        self.login(self._credentials)


def _send(request: Request) -> tuple[int, str | None, bytes]:
    try:
        with urlopen(request, timeout=60) as response:
            return response.status, response.headers.get("x-access-token"), response.read()
    except HTTPError as exc:
        token = exc.headers.get("x-access-token") if exc.headers is not None else None
        return exc.code, token, exc.read()
    except URLError as exc:
        raise ConnectivelyError(f"request failed: {exc.reason}", status=0) from exc


def _error_message(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(payload, dict):
        for key in ("message", "error", "detail"):
            value = payload.get(key)
            if value:
                return str(value)
    return text


def _parse_question(item: dict) -> Question:
    if not isinstance(item, dict):
        raise ConnectivelyError("question entry was not an object", status=500)
    categories = item.get("categories") or []
    if not isinstance(categories, list):
        raise ConnectivelyError("question categories was not an array", status=500)
    question = item.get("question")
    featured_id = item.get("featuredQuestionId")
    if not isinstance(question, str) or featured_id is None:
        raise ConnectivelyError("question entry missing required fields", status=500)
    return Question(
        question=question,
        source=item.get("source"),
        due_date=item.get("due_date"),
        publicLink=item.get("publicLink"),
        featuredQuestionId=int(featured_id),
        sourceUrl=item.get("sourceUrl"),
        isHaroQuery=item.get("isHaroQuery"),
        categories=[str(category) for category in categories],
    )
