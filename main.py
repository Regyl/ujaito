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

    match run_type:
        case RunType.CONNECTIVELY:
            log.info("Starting Connectively Questions")
            connectively_service.run()
        case RunType.GREENHOUSE:
            log.info("Starting Greenhouse Jobs")
            greenhouse_service.run()
    log.info("Finish")


if __name__ == "__main__":
    main(RunType.GREENHOUSE)
