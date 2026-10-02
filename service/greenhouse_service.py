"""Fetch public Greenhouse jobs that mention both Java and relocation."""

from __future__ import annotations

import json
import logging
import re
from urllib.error import HTTPError

from client import greenhouse
from mapper import greenhouse_mapper
from repository import greenhouse_repository
from util import file_util, format_util

log = logging.getLogger(__name__)

COMPANIES_LIST_FILE_PATH = "greenhouse/greenhouse_companies.json"
_JAVA = re.compile(r"\bjava\b", re.IGNORECASE)
_RELOCATION = re.compile(r"relocation", re.IGNORECASE)

def matches(job: dict) -> bool:
    title = str(job.get("title") or "")
    content = format_util.plain_text(str(job.get("content") or ""))
    text = f"{title}\n{content}"
    return _JAVA.search(text) is not None and _RELOCATION.search(text) is not None


def run() -> None:
    boards = json.loads(file_util.get_file_payload(COMPANIES_LIST_FILE_PATH))
    for board in boards:
        try:
            jobs = greenhouse.fetch_jobs(board)
        except (Exception, OSError) as exc:
            if isinstance(exc, HTTPError) and exc.status == 404:
                log.debug(f"Failed to fetch jobs for board {board}")
            else:
                log.error(f"Failed to fetch jobs for board {board}: {exc}")
            continue


        for job in jobs:
            if not matches(job):
                continue

            model = greenhouse_mapper.apply(board, job)
            greenhouse_repository.write_job(model)
            log.info("found %s", model.absolute_url)
