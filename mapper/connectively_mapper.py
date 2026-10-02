import re

from model import AssessedQuestion, ConnectivelyQuestion
from util import file_util

MAX_TEXT_LENGTH = 4096
BACKGROUND_FILE_PATH = "connectively/background.txt"
_MARKDOWN_V2_SPECIAL = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")


def _escape_markdown_v2(value: object) -> str:
    return _MARKDOWN_V2_SPECIAL.sub(r"\\\1", str(value))


def get_tg_notification(item: AssessedQuestion) -> str:
    source = _escape_markdown_v2(item.question.source)
    source_url = _escape_markdown_v2(item.question.sourceUrl)
    due_date = _escape_markdown_v2(item.question.due_date)
    categories = _escape_markdown_v2(", ".join(item.question.categories))
    question = _escape_markdown_v2(item.question.question)
    reason = _escape_markdown_v2(item.assessment.reason)
    link = _escape_markdown_v2(item.question.publicLink)
    msg = (
        f"*Company:* [{source}]({source_url})\n"
        f"*Due date:* {due_date}\n"
        f"*Categories:* {categories}\n"
        "\n"
        "\\-\\-\\-\\-\\-\\-\n"
        f"*Question:* {question}\n"
        "\n"
        "\\-\\-\\-\\-\\-\\-\n"
        f"*Apply reason:* {reason}\n"
        "\n"
        f"[Link]({link})"
    )
    return msg[:MAX_TEXT_LENGTH]

def get_ai_prompt(item: ConnectivelyQuestion) -> str:
    background = file_util.get_file_payload(BACKGROUND_FILE_PATH)
    return (
        "Decide whether this candidate can credibly answer the journalist query "
        "from their background alone.\n\n"
        f"Candidate background:\n{background}\n\n"
        f"Question:\n{item.question}\n\n"
        'Respond with JSON only: {"can_solve": true or false, "reason": "one or two sentences"}'
    )