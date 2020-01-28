"""
      ===== IU7QUIZ TELEGRAM BOT =====
      Copyright (C) 2020 IU7OG Team.

      Модуль содержит набор функций для расчета результата ответа студента по времени реагирования,
      времени ответа, сложности вопроса, номера попытки ответа
      (а так же функция расчета общего рейтинга всех студентов)
"""


from math import exp
import config
from dbinstances import Student, Question


def waiting_func(time_in_hours):
    """
        Расчет доли баллов за быстроту реакции.
    """

    return exp(-config.HALF_WAITING_FACTOR * time_in_hours)


def answr_func(time_in_secs, good_time):
    """
        Расчет доли баллов за быстроту ответа.
        good_time - время ответа в секундах, за которое получаешь 90%.
        (можно настроить не 90, заменив 9 на что-то другое (например, для получения
        80% нужно заменить на 8)).
    """

    return 9 * good_time / (time_in_secs + 9 * good_time)


def calculate_score(q_cmplx, waiting_time, answer_time, atmpt, good_answer_time):
    """
        Формула расчета суммарного кол-ва баллов за ответ (учитывающая все характеристики).
        q_cmplx - сложность вопроса (question complexity).
        good_answer_time - хорошее время ответа (на 90%).
        atmpt - номер попытки.
    """

    answer_score = (config.WAITING_FACTOR * waiting_func(waiting_time) +
                    config.ANSWER_TIME_FACTOR * answr_func(answer_time, good_answer_time))
    complexity = (1 - config.COMPLEXITY_FACTOR * q_cmplx)
    return 100 / atmpt * answer_score * complexity


def answer_summary(student, question, answer_time=-1):
    """
        Расчет баллов для студента student, при ответе на вопрос question,
        answer_time-ый раз (по умолчанию - последний).
    """

    return calculate_score(
        1 - question.first_to_answer / question.total_answers,
        student.data[question.day]['right'][answer_time][0],
        student.data[question.day]['right'][answer_time][1],
        i + 1 + student.data["wrong"] if
        i != -1 else len(student.data['right']) + student.data['wrong'],
        question.best_time_to_answer
    )


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
