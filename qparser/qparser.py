"""
    ===== IU7QUIZ QUESTIONS PARSER =====
    Copyright (C) 2020 IU7OG Team.

    Модуль для парсинга вопросов по лекциям из текстового файла.
"""


import os
import mongoengine
from bot.config import DB_NAME, DB_USER, DB_PASS
from bot.dbinstances import Question

RECORD_SIZE = 6

DB_IP = os.environ['DB_IP']
HOST = f"mongodb://{DB_USER}:{DB_PASS}@{DB_IP}:27017/{DB_NAME}"


def parse_questions():
    """
        Парсинг вопросов из файла.
    """

    mongoengine.connect(host=HOST)

    questions = Question.objects.count()

    with open("./qparser/questions.txt") as file:
        data = file.read().splitlines()

    for i in range(0, len(data), RECORD_SIZE):
        question = Question(
            day=questions + (i // RECORD_SIZE) + 1,
            text=data[i % RECORD_SIZE],
            answers=[data[j % RECORD_SIZE] for j in range(1, RECORD_SIZE - 1)],
            correct_answer=data[(i + RECORD_SIZE - 1) % RECORD_SIZE]
        )
        question.save()

    mongoengine.disconnect()


if __name__ == "__main__":
    parse_questions()
