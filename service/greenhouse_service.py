"""Fetch public Greenhouse jobs that match caller-supplied terms."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from urllib.error import HTTPError

from client import greenhouse
from mapper import greenhouse_mapper
from repository import greenhouse_repository
from util import file_util, format_util

log = logging.getLogger(__name__)

COMPANIES_LIST_FILE_PATH = "greenhouse/greenhouse_companies.json"
_MAX_WORKERS = 16


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    return re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    return re.compile(re.escape(phrase), re.IGNORECASE)


def matches(
    job: dict,
    *,
    included_keywords: Sequence[str],
    excluded_keywords: Sequence[str],
    included_phrases: Sequence[str],
    excluded_phrases: Sequence[str],
) -> bool:
    title = str(job.get("title") or "")
    content = format_util.plain_text(str(job.get("content") or ""))
    text = f"{title}\n{content}"
    excluded = [_keyword_pattern(keyword) for keyword in excluded_keywords]
    excluded.extend(_phrase_pattern(phrase) for phrase in excluded_phrases)
    if any(pattern.search(text) for pattern in excluded):
        return False
    included = [_keyword_pattern(keyword) for keyword in included_keywords]
    included.extend(_phrase_pattern(phrase) for phrase in included_phrases)
    return all(pattern.search(text) for pattern in included)


def _process_board(
    board: str,
    *,
    included_keywords: Sequence[str],
    excluded_keywords: Sequence[str],
    included_phrases: Sequence[str],
    excluded_phrases: Sequence[str],
) -> None:
    try:
        jobs = greenhouse.fetch_jobs(board)
    except (Exception, OSError) as exc:
        if isinstance(exc, HTTPError) and exc.status == 404:
            log.debug(f"Failed to fetch jobs for board {board}")
        else:
            log.error(f"Failed to fetch jobs for board {board}: {exc}")
        return

    for job in jobs:
        if not matches(
            job,
            included_keywords=included_keywords,
            excluded_keywords=excluded_keywords,
            included_phrases=included_phrases,
            excluded_phrases=excluded_phrases,
        ):
            continue

        model = greenhouse_mapper.apply(board, job)
        greenhouse_repository.write_job(model)
        log.info(f"found {model.title}:{model.location}")


def run(
    *,
    included_keywords: Sequence[str],
    excluded_keywords: Sequence[str],
    included_phrases: Sequence[str],
    excluded_phrases: Sequence[str],
) -> None:
    boards = json.loads(file_util.get_file_payload(COMPANIES_LIST_FILE_PATH))
    process = partial(
        _process_board,
        included_keywords=included_keywords,
        excluded_keywords=excluded_keywords,
        included_phrases=included_phrases,
        excluded_phrases=excluded_phrases,
    )
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        list(executor.map(process, boards))
