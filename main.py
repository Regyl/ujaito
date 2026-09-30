"""Fetch Connectively questions and load them into PostgreSQL."""

from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlretrieve

import pyarrow as pa
import pyarrow.parquet as pq
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from client import ConnectivelyClient
from db.models import jdbc_properties, jdbc_url
from exception import ConnectivelyError
from model import LoginRequest, Question
from util.annotations import timed
from util.log import setup_logging

from dotenv import load_dotenv

log = logging.getLogger(__name__)
load_dotenv()

# os.environ["JAVA_HOME"] = "/path/to/your/java/jdk"
JDBC_DRIVER_URL = (
    "https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.7/postgresql-42.7.7.jar"
)

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
    ]
)


def _parse_due_date(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def questions_to_arrow(questions: list[Question]) -> pa.Table:
    return pa.table(
        {
            "question": [item.question for item in questions],
            "source": [item.source for item in questions],
            "due_date": [_parse_due_date(item.due_date) for item in questions],
            "publicLink": [item.publicLink for item in questions],
            "featuredQuestionId": [item.featuredQuestionId for item in questions],
            "sourceUrl": [item.sourceUrl for item in questions],
            "isHaroQuery": [item.isHaroQuery for item in questions],
            "categories": [item.categories for item in questions],
        },
        schema=ARROW_SCHEMA,
    )


def _java_binary() -> str:
    home = os.environ.get("JAVA_HOME")
    if home:
        for name in ("java.exe", "java"):
            candidate = Path(home) / "bin" / name
            if candidate.is_file():
                return str(candidate)
    return "java"


def _require_java_17() -> None:
    try:
        completed = subprocess.run(
            [_java_binary(), "-version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ConnectivelyError("Java 17 or newer is required to run Spark", status=0) from exc
    output = f"{completed.stderr}\n{completed.stdout}"
    match = re.search(r'version "(?:1\.)?(\d+)', output)
    major = int(match.group(1)) if match else 0
    if major < 17:
        raise ConnectivelyError(
            f"Java 17 or newer is required to run Spark (found Java {major or 'unknown'})",
            status=0,
        )


def _postgres_jdbc_jar() -> str:
    destination = Path(os.getenv("POSTGRESQL_JAR_PATH"))
    if destination.is_file() and destination.stat().st_size > 0:
        return str(destination)
    raise ConnectivelyError("No PostgreSQL JDBC driver path were provided", 0)


@timed
def write_questions(table: pa.Table) -> None:
    _require_java_17()
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
    parser = argparse.ArgumentParser(description="Load Connectively questions into PostgreSQL")
    parser.add_argument(
        "--top-opportunities",
        action="store_true",
        help='Fetch top opportunities (query param top_opportunities=true)',
    )
    args = parser.parse_args()

    client = ConnectivelyClient()
    client.login(_login_request_from_env())
    questions = client.question_list(
        top_opportunities=True if args.top_opportunities else None
    )
    table = questions_to_arrow(questions)
    write_questions(table)
    log.info("saved %s questions", table.num_rows)


if __name__ == "__main__":
    main()
