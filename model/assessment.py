"""Fit check stored with a Connectively question."""

from __future__ import annotations

from dataclasses import dataclass

from model.connectively import Question


@dataclass(frozen=True)
class FitAssessment:
    can_solve: bool
    reason: str


@dataclass(frozen=True)
class AssessedQuestion:
    question: Question
    assessment: FitAssessment
