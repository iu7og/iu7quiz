"""
      ===== IU7QUIZ STATISTICS COLLECTOR =====
      Copyright (C) 2020 IU7OG Team.

      В данном модуле содержатся функции, обновляющие статистику студентов и вопросов
      во время получения сообщения о готовности, а также во время ответа на вопрос
      (правильного или неправильного).
"""
import time


def ready_update(datastore, day, start_time):
    """
        Данная функция обновляет информацию в данных студента, когда тот получает вопрос.
    """

    # Если по какой-то причине нет словаря, описывающего вопрос сегодняшнего дня,
    # то добавить словари для сегодняшнего дня и всех предыдущих.
    while len(datastore) <= day:
        datastore.append(dict())

    # В качестве объекта рассматривается словарь, относящийся к сегодняшнему дню.
    question_object = datastore[day]

    # Если словарь пуст (то есть был только что создан), то проинициализируем его.
    if "wrong" not in question_object or "right" not in question_object:
        question_object["wrong"] = list()
        question_object["right"] = list()

    # Если словарь уже был проинициализирован (то есть это не первый ответ на данный вопрос),
    # то записать время реакции.

    return datastore, (time.time() - start_time) / 3600


def right_answer_handler(question_object, question, times_array, queue):
    """
        Обработка статистики вопроса и данных студента при правильном ответе на вопрос.
    """

    sum_len = len(question_object["right"]) + len(question_object["wrong"])
    # Если ответ студент дал впервые, обновить статистику для вопроса.
    if sum_len == 0:
        question.first_to_answer += 1
        question.total_answers += 1

    # Если ответ правильный, запомнить время ответа.
    question_object["right"].append([times_array[2], times_array[0] - times_array[1]])

    # Обработка очереди.
    if sum_len != 0 and sum_len - question_object["wrong"][-1] < 2:
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
