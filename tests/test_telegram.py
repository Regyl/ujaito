"""Telegram alert text for solvable questions."""

from __future__ import annotations

from client.telegram import MAX_TEXT_LENGTH, format_alert
from model import AssessedQuestion, FitAssessment, Question


def _assessed(question: str, *, link: str | None, reason: str) -> AssessedQuestion:
    return AssessedQuestion(
        question=Question(
            question=question,
            source=None,
            due_date=None,
            publicLink=link,
            featuredQuestionId=7,
            sourceUrl=None,
            isHaroQuery=None,
            categories=["Technology"],
        ),
        assessment=FitAssessment(can_solve=True, reason=reason),
    )


def test_format_alert_includes_question_link_and_reason() -> None:
    text = format_alert(
        _assessed(
            "How do you run Kafka?",
            link="https://connectively.example/q/7",
            reason="Kafka experience applies.",
        )
    )
    assert "7" in text
    assert "How do you run Kafka?" in text
    assert "https://connectively.example/q/7" in text
    assert "Kafka experience applies." in text


def test_format_alert_omits_missing_link() -> None:
    text = format_alert(_assessed("How do you run Kafka?", link=None, reason="Kafka experience applies."))
    assert "How do you run Kafka?" in text
    assert "https://" not in text


def test_format_alert_truncates_to_telegram_limit() -> None:
    text = format_alert(_assessed("Q" * 5000, link="https://example.com/q", reason="because"))
    assert len(text) == MAX_TEXT_LENGTH
