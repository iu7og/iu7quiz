"""
      ===== IU7QUIZ TELEGRAM BOT =====
      Copyright (C) 2020 IU7OG Team.

      Telegram-бот, помогающий студентам кафедры ИУ7 закрепить лекционный материал по курсу
      "Программирование на СИ", путём рассылки вопросов по прошедшим лекциям.
"""

from datetime import datetime
from functools import reduce
from random import randint

import json
import time
import multiprocessing
import telebot
import schedule
import mongoengine

import bot.config as cfg
from bot.dbinstances import Student, Question

bot = telebot.TeleBot(cfg.TOKEN)
mongoengine.connect(host=cfg.HOST)


def create_leaderboard_page(btn, prev_page=None):
    """
        Создание одной страницы лидерборда.
    """

    # Позже заменить на вызов get_rating()
    students_ = Student.objects()
    students = []
    for student in students_:
        students.append((student.login, randint(1, 9999)))
    students = sorted(students, key=lambda x: x[1])

    if prev_page is None:
        new_page_start = 0
    else:
        split_page = prev_page.split("\n")
        if btn == "▶️":
            new_page_start = int(split_page[-1][:split_page[-1].find(".")])
        else:
            new_page_start = int(
                split_page[0][:split_page[0].find(".")]) - cfg.LB_PAGE_SIZE - 1

    page_list = students[new_page_start:new_page_start + cfg.LB_PAGE_SIZE]
    page_text = ""

    for i in range(len(page_list)):
        curr_index = i + 1 + new_page_start
        page_text += cfg.LB_MEDALS.setdefault(curr_index, str(curr_index) + ".") + \
            " @" + page_list[i][0] + ". Рейтинг: " + \
            str(page_list[i][1]) + "\n"

    is_border = len(page_list) != cfg.LB_PAGE_SIZE or new_page_start == 0

    return page_text, is_border


def update_status(user_id, status):
    """
        Обновление текущего статуса у студента. Возможные статусы:

        1. registration - студент проходит процесс регистрации (выбор группы).
        2. standby - режим ожидания, у студента нет активных вопросов на данный момент.
        3. is_ready - бот ждёт подтверждения готовности ответить на вопрос.
        4. question - вопрос выслан, ожидания нажатия кнопки с ответом.
    """

    student = Student.objects(user_id=user_id).first()
    student.status = status
    student.save()


def create_markup(btns):
    """
        Создание клавиатуры из inline кнопок в два столбца.
    """

    markup = telebot.types.InlineKeyboardMarkup()

    for btn_odd, btn_even in zip(btns[::2], btns[1::2]):
        markup.add(
            telebot.types.InlineKeyboardButton(
                text=btn_odd, callback_data=btn_odd),
            telebot.types.InlineKeyboardButton(
                text=btn_even, callback_data=btn_even)
        )

    return markup


def send_confirmation():
    """
        Отправка сообщения с вопросом о подтверждении готовности отвечать на вопрос.
    """

    for student in Student.objects():
        if student.status == "standby":
            update_status(student.user_id, "is_ready")

            # Время отправки сообщения записывается в поле студента (qtime_start)
            student.qtime_start = int(time.time())

            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(text=cfg.READY_BTN, callback_data=cfg.READY_BTN))

            bot.send_message(student.user_id, "📝")
            bot.send_message(
                student.user_id,
                "Привет, готовы ли вы сейчас ответить на вопросы по прошедшей лекции?",
                reply_markup=markup
            )


def schedule_message():
    """
        Планировщик сообщений.
    """

    schedule.every(100).minutes.do(send_confirmation)
    while True:
        schedule.run_pending()
        time.sleep(1)


@bot.message_handler(commands=["start"])
def authorization(message):
    """
        Выбор учебной группы для авторизации.
    """

    if not Student.objects(user_id=message.chat.id):
        student = Student(
            user_id=message.chat.id,
            login=message.chat.username,
            status="registration"
        )

        student.save()
        bot.send_message(
            message.chat.id,
            "💬 Укажите свою учебную группу: ",
            reply_markup=create_markup(cfg.GROUPS_BTNS)
        )

    else:
        bot.send_message(
            message.chat.id, "⚠️ Вы уже зарегистрированы в системе.")


"""
@bot.message_handler(commands=["unreg"])
def delete(message):
    #Отладочная комманда.

    Question.objects().delete()
    Student.objects().delete()
    question = Question(
        day=2,
        text="ФИО преподавателя, читающего лекции по Программированию в данном семестре: ",
        answers=
            ["A. Кострицкий Антон Александрович",
            "B. Кострицкий Александр Сергеевич",
            "C. Кострицкий Сергей Владимирович",
            "D. Кострицкий Игорь Владимирович"],
        correct_answer="C"
    )
    print(question.answers)
    question.save()

    print(message)
    print(Student.objects(user_id=message.from_user.id))
    Student.objects(user_id=message.from_user.id).delete()
    print(Student.objects(user_id=message.from_user.id))

    for i in range(103):
        student = Student(
            user_id=randint(1, 999999),
            login="user"+str(randint(1,999)),
            group=str(randint(1,9999999999)),
            status="standby"
        )

        student.save()
"""


@bot.message_handler(commands=["leaderboard"])
def show_leaderboard(message):
    """
        Вывод лидерборда среди учеников.
    """

    student = Student.objects(user_id=message.from_user.id).first()

    if student.status == "standby":
        page = create_leaderboard_page(cfg.SCROLL_BTNS[1])

        if Student.objects.count() > cfg.LB_PAGE_SIZE:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    text=cfg.SCROLL_BTNS[1],
                    callback_data=cfg.SCROLL_BTNS[1])
            )

            bot.send_message(message.chat.id, page, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, page)


@bot.message_handler(commands=["help"])
def help_message(message):
    """
        Информация о боте.
    """

    student = Student.objects(user_id=message.from_user.id).first()

    if student.status == "standby":
        bot.send_message(
            message.chat.id, "Тут напишем про себя и про преподавателей.")


# @bot.message_handler(func=lambda message: True)
# def echo_message(message):
#     """
#         Задать вопрос преподавателю во время лекции.
#     """
#     bot.reply_to(message, "📮 Ваш вопрос принят!")


@bot.callback_query_handler(lambda call: call.data in cfg.GROUPS_BTNS)
def query_handler_reg(call):
    """
        Обработка нажатия inline-кнопок с выбором группы студентом.
    """

    bot.answer_callback_query(call.id)
    student = Student.objects(user_id=call.message.chat.id).first()

    if student.status == "registration":
        student.group = call.data
        student.status = "standby"
        student.save()

        bot.send_message(call.message.chat.id,
                         "✅ Вы успешно зарегистрированы в системе.")


@bot.callback_query_handler(lambda call: call.data == cfg.READY_BTN)
def query_handler_ready(call):
    """
        Высылание вопроса с inline-кнопками тем,
        кто подтвердил готовность отвечать на вопрос.
    """

    bot.answer_callback_query(call.id)
    student = Student.objects(user_id=call.message.chat.id).first()

    if student.status == "is_ready":
        questions = Question.objects(day__mod=(7, datetime.today().weekday()))
        question = questions[len(questions) - 1]

        # Вычисление номера вопроса
        day = (len(questions) - 1) * 7 + datetime.today().weekday()

        datastore = json.loads(student.data)
        # Если по какой-то причине нет словаря, описывающего вопрос сегодняшнего дня,
        # то добавить словари для сегодняшнего дня и всех предыдущих.
        while (len(datastore) <= day):
            datastore.append(dict())

        # В качестве объекта рассматривается словарь, относящийся к сегодняшнему дню.
        question_object = datastore[day]

        # Если словарь пуст (то есть был только что создан), то проинициализируем его
        # (записав в первое время - время реакции, однако, если будет дан неправильный ответ, то
        # ответ будет удален).
        if "wrong" not in question_object.keys() or "right" not in question_object.keys():
            question_object["wrong"] = 0
            question_object["right"] = [[(int(time.time()) - student.qtime_start) / 3600, 0]]

        # Если словарь уже был проинициализирован (то есть это не первый ответ на данный вопрос),
        # то записать время реакции в последнюю пару времен (то есть в последний ответ).
        else:
            question_object["right"].append([(int(time.time()) - student.qtime_start) // 3600, 0])

        # Записать время приема ответа на сообщение с готовностью (== время отправки вопроса).
        student.qtime_start = call.message.chat.time
        # Обновление информации об ответах на вопрос у студента.
        student.data = json.dumps(datastore)

        update_status(call.message.chat.id, "question")

        bot.send_message(
            call.message.chat.id,
            "❓ " + question.text +
            reduce(lambda x, y: x + "📌 " + y + "\n", question.answers, "\n\n"),
            reply_markup=create_markup(cfg.ANSWERS_BTNS)
        )


@bot.callback_query_handler(lambda call: call.data in cfg.ANSWERS_BTNS)
def query_handler_questions(call):
    """
        Обработка нажатия inline-кнопок с выбором ответа студентом.
        Обновление статистики после ответа на вопрос.
    """

    bot.answer_callback_query(call.id)
    student = Student.objects(user_id=call.message.chat.id).first()

    if student.status == "question":
        questions = Question.objects(day__mod=(7, datetime.today().weekday()))
        question = questions[len(questions) - 1]
        update_status(call.message.chat.id, "standby")

        day = (len(questions) - 1) * 7 + datetime.today().weekday()
        datastore = json.loads(student.data)
        question_object = datastore[day]

        if call.data == question.correct_answer:
            # Если ответ студент дал впервые, обновить статистику для вопроса
            if (len(question_object["right"]) == 1 and question_object["wrong"] == 0):
                question.first_to_answer += 1
                question.answers += 1
            # Если ответ правильный, запомнить время ответа (время реакции уже имеется в данных).
            question_object["right"][-1][1] = call.message.chat.time - student.qtime_start
            student.qtime_start = 0
            bot.send_message(
                call.message.chat.id, "✅ Верно! Ваш ответ засчитан.")
        else:
            # Если ответ на вопрос дан впервые, обновить статистику.
            if (len(question_object["right"]) == 1 and question_object["wrong"] == 0):
                question.answers += 1
            question_object["wrong"] += 1
            # Удалить последний ответ из верных, если он оказался неверным.
            question_object["right"].pop()
            bot.send_message(
                call.message.chat.id, "❌ К сожалению, ответ неправильный и он не будет засчитан.")

        student.data = json.dumps(datastore)


@bot.callback_query_handler(lambda call: call.data in cfg.SCROLL_BTNS)
def query_handler_scroll(call):
    """
        Обновление сообщения с лидербордом при нажатии кнопок назад / вперёд.
    """

    bot.answer_callback_query(call.id)
    new_page, is_border = create_leaderboard_page(call.data, call.message.text)

    if is_border:
        markup = telebot.types.InlineKeyboardMarkup()
        new_btn = "◀️" if call.data == "▶️" else "▶️"
        markup.add(
            telebot.types.InlineKeyboardButton(text=new_btn, callback_data=new_btn))
    else:
        markup = create_markup(cfg.SCROLL_BTNS)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        text=new_page,
        message_id=call.message.message_id,
        reply_markup=markup
    )


if __name__ == "__main__":
    multiprocessing.Process(target=schedule_message, args=()).start()
    bot.polling()
