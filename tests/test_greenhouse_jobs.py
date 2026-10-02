"""Keyword matcher for Greenhouse job posts. No live HTTP."""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from unittest.mock import patch

from mapper.greenhouse_mapper import apply as to_job
from service import greenhouse_service
from service.greenhouse_service import matches


def test_both_keywords_required() -> None:
    assert matches({"title": "Java Engineer", "content": "<p>We offer relocation.</p>"})
    assert matches({"title": "JAVA platform", "content": "<p>Relocation package</p>"})
    assert not matches({"title": "Java Engineer", "content": "<p>Remote only.</p>"})
    assert not matches({"title": "Designer", "content": "<p>relocation package</p>"})


def test_javascript_does_not_match() -> None:
    assert not matches(
        {"title": "JavaScript Engineer", "content": "<p>We offer relocation.</p>"}
    )


def test_html_is_stripped_before_matching() -> None:
    job = {
        "title": "Engineer",
        "content": "<div><strong>Java</strong> role with relocation support</div>",
    }
    assert matches(job)


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
        greenhouse_service.run()

    assert set(fetched) == set(boards)
    assert len(fetched) == len(boards)
    assert len(written) == 1
    assert written[0].board == "alpha"
    assert written[0].job_id == 7
