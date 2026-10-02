"""Fetch Connectively questions and load them into PostgreSQL."""

from __future__ import annotations

import logging

from dotenv import load_dotenv

from model.run_type import RunType
from service import connectively_service, greenhouse_service
from util.log_util import setup_logging

log = logging.getLogger(__name__)


def main(run_type: RunType) -> None:
    load_dotenv()
    setup_logging()

    log.info(f"Starting {run_type.name}")
    match run_type:
        case RunType.CONNECTIVELY:
            connectively_service.run()
        case RunType.GREENHOUSE:
            greenhouse_service.run(
                included_keywords=["java", "relocation"],
                excluded_keywords=[],
                included_phrases=[],
                excluded_phrases=[],
            )
    log.info(f"Finished {run_type.name}")


if __name__ == "__main__":
    main(RunType.GREENHOUSE)
