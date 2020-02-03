"""
      ===== IU7QUIZ TELEGRAM BOT =====
      Copyright (C) 2020 IU7OG Team.

      Telegram-бот, помогающий студентам кафедры ИУ7 закрепить лекционный материал по курсу
      "Программирование на СИ", путём рассылки вопросов по прошедшим лекциям.
"""

from datetime import datetime
#from random import randint, shuffle
from random import shuffle


import json
import time
import multiprocessing
import telebot
import schedule
import mongoengine

import bot.config as cfg
import bot.statistics as stat
import bot.rating as rt
from bot.dbinstances import Student, Question

bot = telebot.TeleBot(cfg.TOKEN)
mongoengine.connect(host=cfg.HOST)


def create_leaderboard_page(btn, prev_page=None):
    """
        Создание одной страницы лидерборда.
    """

    students = rt.get_rating()

    if prev_page is None:
        new_page_start = 0
    else:
        split_page = prev_page.split("\n")
        if btn == "▶️":
            new_page_start = int(split_page[-1][:split_page[-1].find(".")])
        else:
            new_page_start = int(
                split_page[0][:split_page[0].find(".")]) - cfg.LB_PAGE_SIZE - 1

    page_text = ""
    page_list = students[new_page_start:new_page_start + cfg.LB_PAGE_SIZE]
    medals = cfg.LB_MEDALS.copy()  # Иначе в определенный момент память просто закончится.

    for i, page in enumerate(page_list):
        curr_index = i + 1 + new_page_start
        page_text += f"{medals.setdefault(curr_index, str(curr_index) + '. ')}" + \
            f"@{page[0]}. Рейтинг: {page[1]:.2f}\n"

    is_border = len(page_list) != cfg.LB_PAGE_SIZE or new_page_start == 0

    return page_text, is_border


def create_markup(btns):
    """
        Создание клавиатуры из inline кнопок в два столбца.
    """

    markup = telebot.types.InlineKeyboardMarkup()

    for btn_odd, btn_even in zip(btns[::2], btns[1::2]):
        markup.add(
            telebot.types.InlineKeyboardButton(text=btn_odd, callback_data=btn_odd),
            telebot.types.InlineKeyboardButton(text=btn_even, callback_data=btn_even)
        )

    return markup


def send_confirmation():
    """
        Отправка сообщения с вопросом о подтверждении готовности отвечать на вопрос.
    """

    for student in Student.objects():
        if student.status == "standby":
            student.status = "is_ready"

            student = send_single_confirmation(student)
            student.save()


def send_single_confirmation(student):
    """
        Отправка одному студенту сообщения с вопросом о готовности отвечать на вопрос.
    """

    # Время отправки сообщения записывается в поле студента (qtime_start)
    student.qtime_start = time.time()

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton(text=cfg.READY_BTN, callback_data=cfg.READY_BTN)
    )

    bot.send_message(student.user_id, "📝")
    bot.send_message(
        student.user_id,
        "Доброго времени суток! " + \
        "Готовы ли вы сейчас ответить на вопросы по прошедшей лекции?",
        reply_markup=markup
    )
    return student


def update_queue():
    """
        big baby tape
    """

    today_question_day = (datetime.datetime.today() - cfg.FIRST_QUESTION_DAY).days

    for student in Student.objects():
        new_queue = list(map(lambda x: x.update({"days_left": x["days_left"] - 1}), student.queue))
        new_queue.insert(0, {"question_day": today_question_day, "days_left": 0})

        student.queue = new_queue
        student.save()

    send_confirmation()


def schedule_message():
    """
        Планировщик сообщений.
    """

    schedule.every().day.at("10:00").do(update_queue)
    #schedule.every(1).minute.do(send_confirmation)
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

        bot.send_message(
            message.chat.id,
            "💬 Укажите свою учебную группу: ",
            reply_markup=create_markup(cfg.GROUPS_BTNS)
        )

        student.save()

    else:
        bot.send_message(message.chat.id, "⚠️ Вы уже зарегистрированы в системе.")


"""
@bot.message_handler(commands=["unreg"])
def delete(message):
        #Отладочная комманда.

    Question.objects().delete()
    Student.objects().delete()
    question = Question(
        day=datetime.today().weekday(),
        text="ФИО преподавателя, читающего лекции по Программированию в данном семестре: ",
        answers=
            ["Кострицкий Антон Александрович",
            "Кострицкий Александр Сергеевич",
            "Кострицкий Сергей Владимирович",
            "Кострицкий Игорь Владимирович"],
            correct_answer="B",
            best_time_to_answer=5
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
            login="user"+str(randint(1,10)),
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
                    callback_data=cfg.SCROLL_BTNS[1]
                )
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
        bot.send_message(message.chat.id, "Тут напишем про себя и про преподавателей.")


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
        bot.send_message(call.message.chat.id, "✅ Вы успешно зарегистрированы в системе.")

        student.group = call.data
        student.status = "standby"
        student.save()


@bot.callback_query_handler(lambda call: call.data == cfg.READY_BTN)
def query_handler_ready(call):
    """
        Высылание вопроса с inline-кнопками тем,
        кто подтвердил готовность отвечать на вопрос.
    """

    bot.answer_callback_query(call.id)
    student = Student.objects(user_id=call.message.chat.id).first()
    today_question_day = (datetime.datetime.today() - cfg.FIRST_QUESTION_DAY).days

    if student.status == "is_ready":
<<<<<<< HEAD
        questions = Question.objects(day=today_question_day)
        question = questions[len(questions) - 1]
=======
        # Номер вопроса берется у первого вопроса в очереди
        day = student.queue[0]["question_day"]
>>>>>>> feature/questions-queue

        question = Question.objects(day=day).first()

        datastore = json.loads(student.data)
        datastore, student.waiting_time = stat.ready_update(datastore, day, student.qtime_start)

        # Записать время приема ответа на сообщение с готовностью (== время отправки вопроса).
        student.qtime_start = time.time()
        # Обновление информации об ответах на вопрос у студента.
        student.data = json.dumps(datastore)
        shuffle(question.answers)

        message = f"❓ {question.text}\n\n"
        for btn, answer in zip(cfg.ANSWERS_BTNS, question.answers):
            message += f"📌{btn}. {answer}\n"

        bot.send_message(
            call.message.chat.id,
            message,
            reply_markup=create_markup(list(cfg.ANSWERS_BTNS.keys()))
        )

        student.status = "question"
        student.save()


@bot.callback_query_handler(lambda call: call.data in cfg.ANSWERS_BTNS)
def query_handler_questions(call):
    """
        Обработка нажатия inline-кнопок с выбором ответа студентом.
        Обновление статистики после ответа на вопрос.
    """

    bot.answer_callback_query(call.id)
    student = Student.objects(user_id=call.message.chat.id).first()
    today_question_day = (datetime.datetime.today() - cfg.FIRST_QUESTION_DAY).days

    if student.status == "question":
<<<<<<< HEAD
        questions = Question.objects(day=today_question_day)
        question = questions[len(questions) - 1]
=======
        day = student.queue[0]["question_day"]
        question = Question.objects(day=day).first()
>>>>>>> feature/questions-queue

        datastore = json.loads(student.data)

        # 4 - emoji + вариант ответа (перед самим ответом)
        student_answer = call.message.text.split("\n")[cfg.ANSWERS_BTNS[call.data] + 1][4:]
        correct_answer = question.answers[cfg.ANSWERS_BTNS[question.correct_answer] - 1]

        # Очередь очищается от текущего вопроса (и обзаводится новым в некоторых случаях)
        # внутри handler'ов.
        if student_answer == correct_answer:
            datastore[day], question, student.queue = stat.right_answer_handler(
                datastore[day], question, time.time(), student.qtime_start,
                student.queue, student.waiting_time)
            bot.send_message(call.message.chat.id, "✅ Верно! Ваш ответ засчитан.")
        else:
            datastore[day], question, student.queue = stat.wrong_answer_handler(
                datastore[day], question, student.queue)
            bot.send_message(call.message.chat.id,
                             "❌ К сожалению, ответ неправильный, и он не будет засчитан.")

        question.save()

        # Если есть вопросы, запланированные на сегодня, то еще раз спрашиваем о готовности
        # и задаем вопрос.
        if student.queue[0]["day_left"] <= 0:
            send_single_confirmation(student)
            student.status = "is_ready"
        else:
            student.status = "standby"

        student.data = json.dumps(datastore)
        student.qtime_start = 0
        student.waiting_time = 0

        student.save()


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
        markup.add(telebot.types.InlineKeyboardButton(text=new_btn, callback_data=new_btn))
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
