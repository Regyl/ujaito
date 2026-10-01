"""Fetch Connectively questions and load them into PostgreSQL."""

from __future__ import annotations

import logging

from dotenv import load_dotenv

from service import connectively_service
from util.log_util import setup_logging

log = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()
    setup_logging()

    connectively_service.run()


if __name__ == "__main__":
    main()
