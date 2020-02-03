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

    # Если словарь пуст (то есть был только что создан), то проинициализируем его
    # (записав в первое время - время реакции, однако, если будет дан неправильный ответ, то
    # ответ будет удален).
    if "wrong" not in question_object or "right" not in question_object:
        question_object["wrong"] = 0
        question_object["right"] = [
            [(int(time.time()) - start_time) // 3600, 0]]

    # Если словарь уже был проинициализирован (то есть это не первый ответ на данный вопрос),
    # то записать время реакции в последнюю пару времен (то есть в последний ответ).
    else:
        question_object["right"].append(
            [(int(time.time()) - start_time) // 3600, 0])
    return datastore


def right_answer_handler(question_object, question, time_now, start_time):
    """
        Обработка статистики вопроса и данных студента при правильном ответе на вопрос.
    """

    # Если ответ студент дал впервые, обновить статистику для вопроса.
    if len(question_object["right"]) == 1 and question_object["wrong"] == 0:
        question.first_to_answer += 1
        question.total_answers += 1
    # Если ответ правильный, запомнить время ответа (время реакции уже имеется в данных).
    question_object["right"][-1][1] = time_now - start_time
    return question_object, question


def wrong_answer_handler(question_object, question):
    """
        Обработка статистики вопроса и данных студента при неправильном ответе на вопрос.
    """

    # Если ответ на вопрос дан впервые, обновить статистику.
    if len(question_object["right"]) == 1 and question_object["wrong"] == 0:
        question.total_answers += 1
    question_object["wrong"] += 1
    # Удалить последний ответ из верных, если он оказался неверным.
    question_object["right"].pop()
    return question_object, question
