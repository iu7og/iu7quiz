"""
      ===== IU7QUIZ STATISTICS COLLECTOR =====
      Copyright (C) 2020 IU7OG Team.

      В данном модуле содержатся функции, обновляющие статистику студентов и вопросов
      во время получения сообщения о готовности, а также во время ответа на вопрос
      (правильного или неправильного).
"""
import time
import json


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
    # 1 элемент - минимальное время ответа, 2 - вопрос, на который был дан ответ за это время.
    min_time = [datastore[0]["right"][0][1], 1]
    # Аналогично пункту выше, только для максимального времени ответа.
    max_time = [datastore[0]["right"][0][1], 1]
    alltime_right = 0
    alltime_total = 0
    # Аналогично 2 пунктам выше, только для максимального времени ожидания.
    max_wait = datastore[0]["right"][0][0]
    # Самый сложный вопрос - на котором было больше всего ошибок (1 - кол-во ошибок, 2 - вопрос)
    hardest_question = [len(datastore[0]["wrong"]), 1]

    for i in range(len(datastore)):
        question = datastore[i]

        # Подсчет общего кол-ва ответов и правильных ответов.
        alltime_right += len(question["right"])
        alltime_total += len(question["right"]) + len(question["wrong"])

        # Поиск лучшего и худшего времен ответа (учет только первой попытки).
        if question["right"]:
            if question["right"][0][1] > max_time[0]:
                max_time = [question["right"][0][1], i + 1]
            if question["right"][0][1] < min_time[0]:
                min_time = [question["right"][0][1], i + 1]
            if question["right"][0][1] > max_wait:
                max_wait = question["right"][0][1]

        # Поиск наиболее сложного вопроса.
        if len(question["wrong"]) > hardest_question[0]:
            hardest_question = [len(question["wrong"]), 1 + i]

    total_stat = f"Процент правильный ответов: {alltime_right / alltime_total * 100:.2f} (" \
        f"{alltime_right}/{alltime_total})\nСамый быстрый ответ*: {min_time[0]:.3f} секунд (" \
        f"{min_time[1]} вопрос)\nСамый долгий ответ*: {max_time[0]:.3f} секунд ({max_time[1]})" \
        f"\nНаибольшее время ожидания: {max_wait * 60:.3f} минут\n"

    if hardest_question[0] != 0:
        total_stat += f"Самый сложный вопрос: {hardest_question[1]} ({hardest_question[0]} "\
            "попыток)\n"

    total_stat += "\n* - учитываются только 1 попытки ответов."
    return total_stat


