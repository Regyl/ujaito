"""Public Greenhouse job post."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GreenhouseJob:
    board: str
    job_id: int
    title: str
    absolute_url: str
    location: str
    content: str
    payload: dict
