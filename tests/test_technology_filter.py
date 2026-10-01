"""Technology category filter and LM Studio assessment parsing."""

from __future__ import annotations

import pytest

from client.lmstudio import parse_fit_assessment
from exception import LmStudioError
from main import is_technology
from model import ConnectivelyQuestion


def _question(*categories: str) -> ConnectivelyQuestion:
    return ConnectivelyQuestion(
        question="How do you scale a backend?",
        source=None,
        due_date=None,
        publicLink=None,
        featuredQuestionId=1,
        sourceUrl=None,
        isHaroQuery=None,
        categories=list(categories),
    )


def test_technology_category_passes() -> None:
    assert is_technology(_question("Technology"))
    assert is_technology(_question("Business", " technology "))


def test_other_categories_do_not_pass() -> None:
    assert not is_technology(_question("Business"))
    assert not is_technology(_question())


def test_parse_raw_json() -> None:
    result = parse_fit_assessment(
        '{"can_solve": true, "reason": " Kafka and distributed systems match. "}'
    )
    assert result.can_solve is True
    assert result.reason == "Kafka and distributed systems match."


def test_parse_fenced_json() -> None:
    text = '```json\n{"can_solve": false, "reason": "This is a consumer finance query."}\n```'
    result = parse_fit_assessment(text)
    assert result.can_solve is False
    assert result.reason == "This is a consumer finance query."


def test_parse_json_with_preamble() -> None:
    text = 'Here is the decision: {"can_solve": true, "reason": "EDR platform experience applies."}'
    result = parse_fit_assessment(text)
    assert result.can_solve is True


def test_parse_rejects_invalid_assessment() -> None:
    with pytest.raises(LmStudioError):
        parse_fit_assessment("not json")
    with pytest.raises(LmStudioError):
        parse_fit_assessment('{"can_solve": 1, "reason": "numeric flag"}')
    with pytest.raises(LmStudioError):
        parse_fit_assessment('{"can_solve": true, "reason": "  "}')
