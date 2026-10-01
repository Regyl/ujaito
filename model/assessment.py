"""Fit check stored with a Connectively question."""

from __future__ import annotations

from dataclasses import dataclass

from model.connectively import ConnectivelyQuestion


@dataclass(frozen=True)
class FitAssessment:
    can_solve: bool
    reason: str


@dataclass(frozen=True)
class AssessedQuestion:
    question: ConnectivelyQuestion
    assessment: FitAssessment
