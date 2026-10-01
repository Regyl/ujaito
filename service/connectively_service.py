import logging

from client import ConnectivelyClient, LmStudioClient, TelegramClient
from model import AssessedQuestion, ConnectivelyQuestion
from repository import connectively_repository

log = logging.getLogger(__name__)

def is_technology(question: ConnectivelyQuestion) -> bool:
    return any(category.strip().casefold() == "technology" for category in question.categories)

def _filter(questions: list[ConnectivelyQuestion]) -> list[ConnectivelyQuestion]:
    filtered_questions = list()
    processed_ids = connectively_repository.get_question_ids()
    for question in questions:
        if is_technology(question) and question.featuredQuestionId not in processed_ids:
            filtered_questions.append(question)
    return filtered_questions


def run() -> None:
    connectively = ConnectivelyClient()
    questions = connectively.question_list()
    filtered_questions = _filter(questions)
    log.info("fetched %s questions, kept %s", len(questions), len(filtered_questions))
    lmstudio = LmStudioClient()
    telegram = TelegramClient()
    for tech_question in filtered_questions:
        assessment = lmstudio.assess(tech_question)
        assessed_question = AssessedQuestion(question=tech_question, assessment=assessment)
        log.info("[%s] assessed", assessed_question.question.featuredQuestionId)

        if assessed_question.assessment.can_solve:
            telegram.notify(assessed_question)
            log.info("[%s] notification sent", assessed_question.question.featuredQuestionId)

        connectively_repository.write_question(assessed_question)