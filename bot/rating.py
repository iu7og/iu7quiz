"""
      ===== IU7QUIZ RATING SYSTEM =====
      Copyright (C) 2020 IU7OG Team.

      Модуль содержит набор функций для расчета результата ответа студента по времени реагирования,
      времени ответа, сложности вопроса, номера попытки ответа
      (а так же функция расчета общего рейтинга всех студентов).
"""


import json
from math import exp
import bot.config as cfg
from bot.dbinstances import Student, Question


def waiting_score(time_in_hours):
    """
        Расчет доли баллов за быстроту реакции.
    """

    if cfg.DEVELOP_MODE:
        print("waiting time in hours:", time_in_hours, end="\n\n")
    return exp(-cfg.HALF_WAITING_FACTOR * time_in_hours)


def answer_speed_score(time_in_secs, good_time):
    """
        Расчет доли баллов за быстроту ответа.
    """

    score = 9 * good_time / (time_in_secs + 9 * good_time)
    if cfg.DEVELOP_MODE:
        print("answer time:", time_in_secs,
              "\ngood time:", good_time, "score:", score)
    return score


def calculate_score(q_complexity, waiting_time, answer_time, attempt, good_answer_time):
    """
        Формула расчета суммарного кол-ва баллов за ответ (учитывающая все характеристики).
    """

    answer_score = (cfg.WAITING_FACTOR * waiting_score(waiting_time) +
                    cfg.ANSWER_TIME_FACTOR * answer_speed_score(answer_time, good_answer_time))
    complexity = (1 - cfg.COMPLEXITY_FACTOR * q_complexity)

    if cfg.DEVELOP_MODE:
        print("answer time:", answer_time, "\nwaiting time:", waiting_time,
              "\nanswer score:", answer_score,
              "(", cfg.WAITING_FACTOR, "for answer time and", cfg.ANSWER_TIME_FACTOR,
              "for waiting time)\n")
        print("complexity factor in final formula: ", complexity, end="\n\n")
        print("attempt number: ", attempt, end="\n\n")
        print("final score:", 100 / attempt *
              answer_score * complexity, end="\n\n")

    return 100 / attempt * answer_score * complexity


def answer_summary(student, question, answer_number=-1):
    """
        Расчет баллов для студента student, при ответе на вопрос question.
    """

    # Выгрузка поля, отвечающего в поле данных студента `student` за вопрос `question`
    datastore = json.loads(student.data)[question.day]

    q_complexity = 1 - (question.first_to_answer / question.total_answers)
    waiting_time = datastore["right"][answer_number][0]
    time_of_answer = datastore["right"][answer_number][1]
    attempt = answer_number + 1 + datastore["wrong"] if \
        answer_number != -1 else len(datastore["right"]) + datastore["wrong"]
    good_answer_time = question.best_time_to_answer

    if cfg.DEVELOP_MODE:
        print("student: ", student.tg_login, end="\n\n")
        print("question: ", question.text, end="\n\n")
        print("question stat:\nfirst to answer:", question.first_to_answer, "\nall answers:",
              question.total_answers, "\ncomplexity:", q_complexity, end="\n\n")
        print("waiting time:", waiting_time, end="\n\n")
        print("answer time:", time_of_answer, end="\n\n")
        print("answer number:", answer_number, "\nright answers:", len(datastore["right"]),
              "\nwrong answers:", datastore["wrong"], "attempt:", attempt, end="\n\n")
        print("question good time:", question.best_time_to_answer, end="\n\n")

    return calculate_score(q_complexity, waiting_time, time_of_answer, attempt, good_answer_time)


def get_rating():
    """
        Возвращает отсортированный массив кортежей-пар (nickname, summary).
    """

    rating = dict()
    questions = Question.objects()

    for student in Student.objects():
        summary = 0
        datastore = json.loads(student.data)

        for question in questions:
            if len(datastore) > question.day:
                for i in range(len(datastore[question.day]["right"])):
                    summary += answer_summary(student, question, i)
            else:
                break

        if student.login not in rating:
            rating[student.login] = summary / len(questions) if summary != 0 else 0
        else:
            i = 1
            while (student.login + f"({i})" in rating)
                i += 1
            rating[student.login + f"({i})"] = summary / len(questions) if summary != 0 else 0
    if cfg.DEVELOP_MODE:
        print("rating:\n", rating, end="\n\n")

    return sorted(rating.items(), key=lambda x: x[1], reverse=True)
