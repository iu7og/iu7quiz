"""
    ===== IU7QUIZ QUESTIONS PARSER =====
    Copyright (C) 2020 IU7OG Team.

    Модуль для парсинга вопросов по лекциям из текстового файла.
"""


import os
import mongoengine
from bot.config import DB_NAME, DB_USER, DB_PASS
from bot.dbinstances import Question


WEEK = 7
RECORD_SIZE = 6

DB_IP = os.environ['DB_IP']
HOST = f"mongodb://{DB_USER}:{DB_PASS}@{DB_IP}:27017/{DB_NAME}"


def parse_to_mongo():
    """
        Парсинг вопросов из файла.
    """

    mongoengine.connect(host=HOST)

    qcount = Question.objects.count()

    with open("./data/questions.txt") as file:
        for i in range(WEEK):
            data = [next(file)[:-1] for _ in range(RECORD_SIZE)]
            best_time_to_answer = len("".join(data[0:5)))
            question = Question(
                day=qcount + i,
                text=data[0],
                answers=[data[j] for j in range(1, 5)],
                correct_answer=data[5],
                best_time_to_answer=best_time_to_answer
            )
            question.save()

    mongoengine.disconnect()


if __name__ == "__main__":
    parse_to_mongo()
