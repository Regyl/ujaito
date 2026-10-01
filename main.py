"""Fetch Connectively questions and load them into PostgreSQL."""

from __future__ import annotations

import argparse
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from client import ConnectivelyClient, LmStudioClient
from db.models import jdbc_properties, jdbc_url
from exception import ConnectivelyError
from model import BACKGROUND, AssessedQuestion, LoginRequest, Question
from util.annotations import timed
from util.log import setup_logging

log = logging.getLogger(__name__)
load_dotenv()

ARROW_SCHEMA = pa.schema(
    [
        pa.field("question", pa.string(), nullable=False),
        pa.field("source", pa.string()),
        pa.field("due_date", pa.timestamp("us", tz="UTC")),
        pa.field("publicLink", pa.string()),
        pa.field("featuredQuestionId", pa.int64(), nullable=False),
        pa.field("sourceUrl", pa.string()),
        pa.field("isHaroQuery", pa.bool_()),
        pa.field("categories", pa.list_(pa.string()), nullable=False),
        pa.field("can_solve", pa.bool_(), nullable=False),
        pa.field("fit_reason", pa.string(), nullable=False),
    ]
)


def is_technology(question: Question) -> bool:
    return any(category.strip().casefold() == "technology" for category in question.categories)


def _parse_due_date(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def questions_to_arrow(questions: list[AssessedQuestion]) -> pa.Table:
    return pa.table(
        {
            "question": [item.question.question for item in questions],
            "source": [item.question.source for item in questions],
            "due_date": [_parse_due_date(item.question.due_date) for item in questions],
            "publicLink": [item.question.publicLink for item in questions],
            "featuredQuestionId": [item.question.featuredQuestionId for item in questions],
            "sourceUrl": [item.question.sourceUrl for item in questions],
            "isHaroQuery": [item.question.isHaroQuery for item in questions],
            "categories": [item.question.categories for item in questions],
            "can_solve": [item.assessment.can_solve for item in questions],
            "fit_reason": [item.assessment.reason for item in questions],
        },
        schema=ARROW_SCHEMA,
    )

def _postgres_jdbc_jar() -> str:
    destination = Path(os.getenv("POSTGRESQL_JAR_PATH"))
    if destination.is_file() and destination.stat().st_size > 0:
        return str(destination)
    raise ConnectivelyError("No PostgreSQL JDBC driver path were provided", 0)


@timed
def write_questions(table: pa.Table) -> None:
    pg_driver = _postgres_jdbc_jar()
    with tempfile.TemporaryDirectory(prefix="connectively-") as directory:
        parquet_path = str(Path(directory) / "questions.parquet")
        pq.write_table(table, parquet_path)
        spark = (
            SparkSession.builder.master("local[*]")
            .appName("connectively-questions")
            .config("spark.sql.execution.arrow.pyspark.enabled", "true")
            .config("spark.driver.extraClassPath", pg_driver)
            .config("spark.executor.extraClassPath", pg_driver)
            .config("spark.ui.enabled", "true")
            .config("spark.ui.port", "4040")
            .getOrCreate()
        )
        ui_url = spark.sparkContext.uiWebUrl or "http://localhost:4040"
        log.info("Spark UI at %s", ui_url)
        try:
            frame = spark.read.parquet(parquet_path).select(
                F.col("featuredQuestionId").cast("long").alias("featured_question_id"),
                F.col("question"),
                F.col("source"),
                F.col("due_date"),
                F.col("publicLink").alias("public_link"),
                F.col("sourceUrl").alias("source_url"),
                F.col("isHaroQuery").alias("is_haro_query"),
                F.to_json(F.col("categories")).alias("categories"),
                F.col("can_solve"),
                F.col("fit_reason"),
            )
            properties = jdbc_properties()
            properties["truncate"] = "true"
            frame.write.option("truncate", "true").jdbc(
                jdbc_url(),
                "questions",
                mode="overwrite",
                properties=properties,
            )
        finally:
            time.sleep(120)
            spark.stop()


def _login_request_from_env() -> LoginRequest:
    username = os.getenv("CONNECTIVELY_USERNAME")
    password = os.getenv("CONNECTIVELY_PWD")
    if not username or not password:
        raise ConnectivelyError(
            "CONNECTIVELY_USERNAME and CONNECTIVELY_PASSWORD are required",
            status=0,
        )
    return LoginRequest(username=username, password=password)


def main() -> None:
    setup_logging()

    client = ConnectivelyClient()
    client.login(_login_request_from_env())
    questions = client.question_list()
    technology = [item for item in questions if is_technology(item)]
    log.info("fetched %s questions, kept %s in Technology", len(questions), len(technology))
    studio = LmStudioClient()
    assessed = [
        AssessedQuestion(question=item, assessment=studio.assess(item.question, BACKGROUND))
        for item in technology
    ]
    table = questions_to_arrow(assessed)
    write_questions(table)
    log.info("saved %s questions", table.num_rows)


if __name__ == "__main__":
    main()
