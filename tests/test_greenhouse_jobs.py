"""Keyword matcher for Greenhouse job posts. No live HTTP."""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from unittest.mock import patch

from mapper.greenhouse_mapper import apply as to_job
from service import greenhouse_service
from service.greenhouse_service import matches

_SEARCH = dict(
    included_keywords=["java"],
    excluded_keywords=[],
    included_phrases=["relocation"],
    excluded_phrases=[],
)


def test_both_keywords_required() -> None:
    assert matches({"title": "Java Engineer", "content": "<p>We offer relocation.</p>"}, **_SEARCH)
    assert matches({"title": "JAVA platform", "content": "<p>Relocation package</p>"}, **_SEARCH)
    assert not matches({"title": "Java Engineer", "content": "<p>Remote only.</p>"}, **_SEARCH)
    assert not matches({"title": "Designer", "content": "<p>relocation package</p>"}, **_SEARCH)


def test_javascript_does_not_match() -> None:
    assert not matches(
        {"title": "JavaScript Engineer", "content": "<p>We offer relocation.</p>"},
        **_SEARCH,
    )


def test_html_is_stripped_before_matching() -> None:
    job = {
        "title": "Engineer",
        "content": "<div><strong>Java</strong> role with relocation support</div>",
    }
    assert matches(job, **_SEARCH)


def test_excluded_keyword_rejects_whole_word_only() -> None:
    assert not matches(
        {"title": "Java Intern", "content": "<p>We offer relocation.</p>"},
        **(_SEARCH | {"excluded_keywords": ["intern"]}),
    )
    assert matches(
        {"title": "JavaScript Engineer", "content": "<p>We offer relocation.</p>"},
        included_keywords=[],
        excluded_keywords=["java"],
        included_phrases=["relocation"],
        excluded_phrases=[],
    )
    assert not matches(
        {"title": "Java and JavaScript Engineer", "content": "<p>We offer relocation.</p>"},
        included_keywords=[],
        excluded_keywords=["java"],
        included_phrases=["relocation"],
        excluded_phrases=[],
    )


def test_excluded_phrase_rejects_matching_post() -> None:
    terms = _SEARCH | {"excluded_phrases": ["no visa"]}
    assert not matches(
        {"title": "Java Engineer", "content": "<p>We offer relocation. No visa sponsorship.</p>"},
        **terms,
    )
    assert matches(
        {"title": "Java Engineer", "content": "<p>We offer relocation.</p>"},
        **terms,
    )


def test_phrase_matches_inside_longer_word() -> None:
    job = {"title": "JavaScript Engineer", "content": "<p>We offer relocation.</p>"}
    assert matches(
        job,
        included_keywords=[],
        excluded_keywords=[],
        included_phrases=["java", "relocation"],
        excluded_phrases=[],
    )
    assert not matches(job, **_SEARCH)


def test_job_model_keeps_the_full_post() -> None:
    payload = {
        "id": 7,
        "title": "Java Engineer",
        "absolute_url": "https://example.test/jobs/7",
        "location": {"name": "Berlin"},
        "content": "<p>Java relocation</p>",
        "departments": [{"name": "Engineering"}],
    }
    job = to_job("stripe", payload)
    stored = asdict(job)
    assert set(stored) == {item.name for item in fields(job)}
    assert stored["source"] == "greenhouse"
    assert stored["board"] == "stripe"
    assert stored["job_id"] == 7
    assert stored["location"] == "Berlin"
    assert stored["payload"]["departments"] == [{"name": "Engineering"}]


def test_run_fetches_every_board_and_keeps_going_after_a_failure() -> None:
    boards = ["alpha", "missing", "beta"]
    fetched: list[str] = []
    written: list[object] = []

    def fetch_jobs(board: str) -> list[dict]:
        fetched.append(board)
        if board == "missing":
            raise OSError("board unavailable")
        if board == "alpha":
            return [
                {
                    "id": 7,
                    "title": "Java Engineer",
                    "absolute_url": "https://example.test/jobs/7",
                    "location": {"name": "Berlin"},
                    "content": "<p>Java relocation</p>",
                }
            ]
        return [
            {
                "id": 8,
                "title": "Designer",
                "absolute_url": "https://example.test/jobs/8",
                "content": "<p>Remote only.</p>",
            }
        ]

    with (
        patch(
            "service.greenhouse_service.file_util.get_file_payload",
            return_value=json.dumps(boards),
        ),
        patch("service.greenhouse_service.greenhouse.fetch_jobs", side_effect=fetch_jobs),
        patch("service.greenhouse_service.greenhouse_repository.write_job", side_effect=written.append),
    ):
        greenhouse_service.run(**_SEARCH)

    assert set(fetched) == set(boards)
    assert len(fetched) == len(boards)
    assert len(written) == 1
    assert written[0].board == "alpha"
    assert written[0].job_id == 7
