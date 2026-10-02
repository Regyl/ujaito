"""Keyword matcher for Greenhouse job posts. No live HTTP."""

from __future__ import annotations

from dataclasses import asdict, fields

from service.greenhouse_service import matches, to_job


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
