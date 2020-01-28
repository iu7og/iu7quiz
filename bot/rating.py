"""
      ===== IU7QUIZ TELEGRAM BOT =====
      Copyright (C) 2020 IU7OG Team.

      Модуль содержит набор функций для расчета результата ответа студента по времени реагирования,
      времени ответа, сложности вопроса, номера попытки ответа
      (а так же функция расчета общего рейтинга всех студентов).
"""


from math import exp
import config
from dbinstances import Student, Question


def waiting_score(time_in_hours):
    """
        Расчет доли баллов за быстроту реакции.
    """

    return exp(-config.HALF_WAITING_FACTOR * time_in_hours)


def answer_speed_score(time_in_secs, good_time):
    """
        Расчет доли баллов за быстроту ответа.
    """

    return 9 * good_time / (time_in_secs + 9 * good_time)


def calculate_score(q_complexity, waiting_time, answer_time, attempt, good_answer_time):
    """
        Формула расчета суммарного кол-ва баллов за ответ (учитывающая все характеристики).
    """

    answer_score = (config.WAITING_FACTOR * waiting_score(waiting_time) +
                    config.ANSWER_TIME_FACTOR * answer_speed_score(answer_time, good_answer_time))
    complexity = (1 - config.COMPLEXITY_FACTOR * q_complexity)
    return 100 / attempt * answer_score * complexity


def answer_summary(student, question, answer_time=-1):
    """
        Расчет баллов для студента student, при ответе на вопрос question,
    """

    q_complexity = 1 - (question.first_to_answer / question.total_answers),
    waiting_time = student.data[question.day]['right'][answer_time][0]
    time_of_answer = student.data[question.day]['right'][answer_time][1]
    attempt = answer_time + 1 + student.data["wrong"] if \
    answer_time != -1 else len(student.data['right']) + student.data['wrong']
    good_answer_time = question.best_time_to_answer

    return calculate_score(q_complexity, waiting_time, time_of_answer, attempt, good_answer_time)


def get_rating():
    """
        Возвращает отсортированный массив кортежей-пар (nickname, summary).
    """

    rating = dict()

    for student in Student.objects():
        summary = 0

        for question in Question.objects():
            for i in range(len(student.data[question.day]["right"])):
                summary += answer_summary(student, question, i)

        rating[student.tg_login] = summary

    return sorted(rating.items(), key=lambda x: x[1])
