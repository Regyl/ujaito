"""Persist assessed Connectively questions."""

from __future__ import annotations

from datetime import datetime, timezone

import psycopg
from psycopg.types.json import Json

from db.models import postgres_connect_kwargs
from model import AssessedQuestion
from util.annotations import timed

INSERT_QUESTION = """
INSERT INTO questions (
    featured_question_id,
    question,
    source,
    due_date,
    public_link,
    source_url,
    is_haro_query,
    categories,
    can_solve,
    fit_reason
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def _parse_due_date(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _question_row(item: AssessedQuestion) -> tuple:
    question = item.question
    return (
        question.featuredQuestionId,
        question.question,
        question.source,
        _parse_due_date(question.due_date),
        question.publicLink,
        question.sourceUrl,
        question.isHaroQuery,
        Json(question.categories),
        item.assessment.can_solve,
        item.assessment.reason,
    )


@timed
def write_questions(questions: list[AssessedQuestion]) -> None:
    with psycopg.connect(**postgres_connect_kwargs()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE questions")
            for item in questions:
                cursor.execute(INSERT_QUESTION, _question_row(item))

@timed
def write_question(question: AssessedQuestion) -> None:
    with psycopg.connect(**postgres_connect_kwargs()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(INSERT_QUESTION, _question_row(question))

def get_question_ids() -> set[int]:
    with psycopg.connect(**postgres_connect_kwargs()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT featured_question_id FROM questions")
            return {row[0] for row in cursor.fetchall()}