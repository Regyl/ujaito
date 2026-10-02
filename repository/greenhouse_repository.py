"""Persist Greenhouse job posts."""

from __future__ import annotations

import psycopg
from psycopg.types.json import Json

from db.models import postgres_connect_kwargs
from model.greenhouse import GreenhouseJob
from util.annotations import timed

INSERT_JOB = """
INSERT INTO jobs (
    source,
    board,
    job_id,
    title,
    absolute_url,
    location,
    content,
    payload
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (source, board, job_id) DO UPDATE SET
    title = EXCLUDED.title,
    absolute_url = EXCLUDED.absolute_url,
    location = EXCLUDED.location,
    content = EXCLUDED.content,
    payload = EXCLUDED.payload
"""


@timed
def write_job(job: GreenhouseJob) -> None:
    with psycopg.connect(**postgres_connect_kwargs()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                INSERT_JOB,
                (
                    job.source,
                    job.board,
                    job.job_id,
                    job.title,
                    job.absolute_url,
                    job.location,
                    job.content,
                    Json(job.payload),
                ),
            )
