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


def waiting_func(time):
    """
        Расчет доли баллов за быстроту реакции
        time - время ответа в часах
    """

    return exp(-config.HALF_WAITING_FACTOR * time)


def answr_func(time, good_time):
    """
        Расчет доли баллов за быстроту ответа.
        time - время ответа в секундах.
        good_time - время ответа в секундах, за которое получаешь 90%.
        (можно настроить не 90, заменив 9 на что-то другое (например, для получения
        80% нужно заменить на 8)).
    """

    return 9 * good_time / (time + 9 * good_time)


def formula(q_cmplx, t1, t2, atmpt, good_t2):
    """
        Формула расчета суммарного кол-ва баллов за ответ (учитывающая все характеристики).
        q_cmplx - сложность вопроса (question complexity).
        t1 - время ожидания готовности.
        t2 - время ответа.
        good_t2 - хорошее время ответа (на 90%).
        atmpt - номер попытки.
    """

    return 100 / atmpt * (config.WAITING_FACTOR * waiting_func(t1) +
                          config.ANSWR_TIME_FACTOR * answr_func(t2, good_t2)) * \
        (1 - config.CMPLXITY_FACTOR * q_cmplx)


def answer_summary(stdnt, qstn, i=-1):
    """
        Расчет баллов для студента stdnt, при ответе на вопрос qstn,
        i-ый раз (по умолчанию - последний).
    """

    return formula(
        1 - qstn.first_to_answer / qstn.total_answers,
        stdnt.data[qstn.day]['right'][i][0],
        stdnt.data[qstn.day]['right'][i][1],
        i + 1 + stdnt.data["wrong"] if i != -
        1 else len(stdnt.data['right']) + stdnt.data['wrong'],
        qstn.best_time_to_answer
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
