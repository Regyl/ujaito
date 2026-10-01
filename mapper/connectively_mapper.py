from model import AssessedQuestion, ConnectivelyQuestion
from util import file_util

MAX_TEXT_LENGTH = 4096
BACKGROUND_FILE_PATH = "connectively/background.txt"

def get_tg_notification(item: AssessedQuestion) -> str:
    msg = f"""
    Company: {item.question.source}
    Due date: {item.question.due_date}
    Categories: {", ".join(item.question.categories)}
    
    ----
    Question: {item.question.question}
    
    ---
    Apply reason: {item.assessment.reason}
    
    Link: {item.question.publicLink}
    """
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