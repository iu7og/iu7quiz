"""
    ===== IU7QUIZ QUESTIONS PARSER =====
    Copyright (C) 2020 IU7OG Team.

    Модуль для парсинга вопросов по лекциям из текстового файла.
"""


import os
import mongoengine
import gspread
import schedule
from oauth2client.service_account import ServiceAccountCredentials

from bot.config import HOST, SYMBOLS_PER_SECOND, RECORD_SIZE, SH_CREDENTIALS, SH_URL
from bot.dbinstances import Question


def parse_to_mongo():
    """
        Парсинг вопросов из Google таблиц.
    """

    mongoengine.connect(host=HOST)

    scope = ["https://spreadsheets.google.com/feeds"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(SH_CREDENTIALS, scope)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_url(SH_URL)
    worksheet = spreadsheet.worksheet("Лекция")

    db_questions_count = Question.objects.count()
    gs_questions_count = len(worksheet.get_all_values())

    for i in range(db_questions_count, gs_questions_count):
        data = worksheet.row_values(i + 1)
        best_time_to_answer = len("".join(data[0:5])) / SYMBOLS_PER_SECOND
        question = Question(
            day=i,
            text=data[0],
            answers=[data[j] for j in range(1, 5)],
            correct_answer=data[5],
            best_time_to_answer=best_time_to_answer
        )
        question.save()

    mongoengine.disconnect()


if __name__ == "__main__":
    parse_to_mongo()
