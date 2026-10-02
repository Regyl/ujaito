"""Persist Greenhouse job posts."""

from __future__ import annotations

from dataclasses import asdict

import psycopg
from psycopg.types.json import Json

from db.models import postgres_connect_kwargs
from model.greenhouse import GreenhouseJob
from util.annotations import timed

INSERT_JOB = """
INSERT INTO jobs (
    board,
    job_id,
    model
) VALUES (%s, %s, %s)
ON CONFLICT (board, job_id) DO UPDATE SET model = EXCLUDED.model
"""


@timed
def write_job(job: GreenhouseJob) -> None:
    with psycopg.connect(**postgres_connect_kwargs()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(INSERT_JOB, (job.board, job.job_id, Json(asdict(job))))
