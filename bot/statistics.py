"""
      ===== IU7QUIZ STATISTICS COLLECTOR =====
      Copyright (C) 2020 IU7OG Team.

      В данном модуле содержатся функции, обновляющие статистику студентов и вопросов
      во время получения сообщения о готовности, а также во время ответа на вопрос
      (правильного или неправильного).
"""
import time
import json
import math


def ready_update(datastore, day, start_time):
    """
        Данная функция обновляет информацию в данных студента, когда тот получает вопрос.
    """

    # Если по какой-то причине нет словаря, описывающего вопрос сегодняшнего дня,
    # то добавить словари для сегодняшнего дня и всех предыдущих.
    while len(datastore) <= day:
        datastore.append(dict())
        # Проинициализируем словарь.
        datastore[-1]["right"] = list()
        datastore[-1]["wrong"] = list()

    return datastore, (time.time() - start_time) / 3600


def right_answer_handler(question_object, question, times_cortege, queue):
    """
        Обработка статистики вопроса и данных студента при правильном ответе на вопрос.
    """

    sum_len = len(question_object["right"]) + len(question_object["wrong"])
    # Если ответ студент дал впервые, обновить статистику для вопроса.
    if sum_len == 0:
        question.first_to_answer += 1
        question.total_answers += 1

    # Если ответ правильный, запомнить время ответа.
    question_object["right"].append(
        [times_cortege[2], times_cortege[0] - times_cortege[1]])

    # Обработка очереди.
    # (p.s.: sum_len вычислялся по старой статистике (перед добавлением
    # нового правильного ответа)).
    if sum_len != 0 and len(question_object["wrong"]) > 0 and \
            sum_len - question_object["wrong"][-1] < 2:
        days_left = 2 + sum_len

        i = 0
        while i < len(queue) and queue[i]["days_left"] <= days_left:
            i += 1

        queue.insert(i, {"days_left": days_left, "question_day": question.day})
    queue.pop(0)

    return question_object, question, queue


def wrong_answer_handler(question_object, question, queue):
    """
        Обработка статистики вопроса и данных студента при неправильном ответе на вопрос.
    """

    sum_len = len(question_object["right"]) + len(question_object["wrong"])
    # Если ответ на вопрос дан впервые, обновить статистику.
    if sum_len == 0:
        question.total_answers += 1
    question_object["wrong"].append(sum_len)

    # Обработка очереди.
    days_left = 2 + sum_len

    i = 0
    while i < len(queue) and queue[i]["days_left"] <= days_left:
        i += 1

    queue.insert(i, {"days_left": days_left, "question_day": question.day})
    queue.pop(0)

    return question_object, question, queue


def stat_msg(student):
    """
        Функция создания строки со статистикой за все время.
    """

    datastore = json.loads(student.data)

    if not datastore:
        return "🧐 Для вас еще нет статистики."

    # 1 элемент - минимальное время ответа, 2 - вопрос, на который был дан ответ за это время.
    min_time = math.inf
    # Аналогично пункту выше, только для максимального времени ответа.
    max_time = 0
    alltime_right = 0
    alltime_total = 0
    # Аналогично 2 пунктам выше, только для максимального времени ожидания.
    max_wait = 0

    for question in datastore:
        # Подсчет общего кол-ва ответов и правильных ответов.
        alltime_right += len(question["right"])
        alltime_total += len(question["right"]) + len(question["wrong"])

        # Поиск лучшего и худшего времен ответа (учет только первой попытки).
        if question["right"]:
            if question["right"][0][1] > max_time:
                max_time = question["right"][0][1]
            if question["right"][0][1] < min_time:
                min_time = question["right"][0][1]
            if question["right"][0][0] > max_wait:
                max_wait = question["right"][0][0]

    if min_time == math.inf:
        return "🧐 Вы еще не давали правильных ответов на вопросы."

    total_stat = f"🧮 Процент правильных ответов: *{alltime_right / alltime_total * 100:.2f}% (на " \
        f"{alltime_right}/{alltime_total} был дан правильный ответ)*\n" \
        f"🤔 Наибольшее время ожидания: *{max_wait * 60:.3f} минут*\n" \
        f"🏃‍♂️ Самый быстрый ответ (❓): *{min_time:.3f} секунд*\n" \
        f"🚶‍♂️ Самый долгий ответ (❓): *{max_time:.3f} секунд*\n" \
        "\n❓ - учитываются только первые попытки ответов"
    return total_stat
