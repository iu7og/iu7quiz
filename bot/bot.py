"""
      ===== IU7QUIZ TELEGRAM BOT =====
      Copyright (C) 2020 IU7OG Team.

      Telegram-бот, помогающий студентам кафедры ИУ7 закрепить лекционный материал по курсу
      "Программирование на СИ", путём рассылки вопросов по прошедшим лекциям.
"""

from datetime import datetime
from functools import reduce

from random import randint

import time
import multiprocessing
import telebot
import schedule
import mongoengine

from dbinstances import Student, Question
from config import TOKEN, HOST, GROUPS_BTNS, ANSWERS_BTNS, READY_BTN, SCROLL_BTNS

bot = telebot.TeleBot(TOKEN)
mongoengine.connect(host=HOST)


def update_status(user_id, status):
    """
        Обновление текущего статуса у студента. Возможные статусы:

        1. registration - студент проходит процесс регистрации (выбор группы).
        2. standby - режим ожидания, у студента нет активных вопросов на данный момент.
        3. confirmation - бот ждёт подтверждения готовности ответить на вопрос.
        4. question - вопрос выслан, ожидания нажатия кнопки с ответом.
    """

    student = Student.objects(user_id=user_id).first()
    student.status = status
    student.save()


def create_markup(buttons):
    """
        Создание клавиатуры из inline кнопок в два столбца.
    """

    markup = telebot.types.InlineKeyboardMarkup()

    for btn_odd, btn_even in zip(buttons[::2], buttons[1::2]):
        markup.add(
            telebot.types.InlineKeyboardButton(
                text=btn_odd, callback_data=btn_odd),
            telebot.types.InlineKeyboardButton(
                text=btn_even, callback_data=btn_even)
        )

    return markup


def schedule_message():
    """
        Планировщик сообщений.
    """
    def sending_confirmation():
        """
            Отправка сообщения с вопросом о подтверждении готовности отвечать на вопрос.
        """

        for student in Student.objects():
            if student.status == "standby":
                update_status(student.user_id, "confirmation")

                markup = telebot.types.InlineKeyboardMarkup()
                markup.add(
                    telebot.types.InlineKeyboardButton(text=READY_BTN, callback_data=READY_BTN))

                bot.send_message(student.user_id, "📝")
                bot.send_message(
                    student.user_id,
                    "Привет, готовы ли вы сейчас ответить по прошедшей лекции? ",
                    reply_markup=markup
                )

    schedule.every(1).minutes.do(sending_confirmation)
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
            reply_markup=create_markup(GROUPS_BTNS)
        )

    else:
        bot.send_message(
            message.chat.id, "⚠️ Вы уже зарегистрированы в системе.")



@bot.message_handler(commands=["unreg"])
def delete(message):
    #Отладочная комманда.

    Question.objects().delete()
    Student.objects().delete()
    question = Question(
        day=1,
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



@bot.message_handler(commands=["leaderboard"])
def show_leaderboard(message):
    """
        Вывод лидерборда среди учеников.
    """

    student = Student.objects(user_id=message.from_user.id).first()

    if student.status == "standby":
        msg = reduce(lambda x, y: x + "Логин: @" + str(y.login) + \
            "\nГруппа: " + y.group + "\n", Student.objects(), "")
        bot.send_message(message.chat.id, msg, reply_markup=create_markup(SCROLL_BTNS))


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


@bot.callback_query_handler(lambda call: call.data in GROUPS_BTNS)
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

        student = Student(
            user_id=call.message.chat.id,
            login=call.message.chat.username,
            group=call.data
        )

        bot.send_message(call.message.chat.id,
                         "✅ Вы успешно зарегистрированы в системе.")


@bot.callback_query_handler(lambda call: call.data == READY_BTN)
def query_handler_ready(call):
    """
        Высылание вопроса с inline-кнопками тем,
        кто подтвердил готовность отвечать на вопрос.
    """

    bot.answer_callback_query(call.id)
    student = Student.objects(user_id=call.message.chat.id).first()
    questions = Question.objects(day__mod=(datetime.today().weekday(), 0))
    question = questions[len(questions) - 1]

    if student.status == "confirmation":
        update_status(call.message.chat.id, "question")
        bot.send_message(
            call.message.chat.id,
            "❓ " + question.text + \
                reduce(lambda x, y: x + "📌 " + y + "\n", question.answers, "\n\n"),
            reply_markup=create_markup(ANSWERS_BTNS)
        )


@bot.callback_query_handler(lambda call: call.data in ANSWERS_BTNS)
def query_handler_questions(call):
    """
        Обработка нажатия inline-кнопок с выбором ответа студентом.
    """

    bot.answer_callback_query(call.id)
    student = Student.objects(user_id=call.message.chat.id).first()

    if student.status == "question":
        questions = Question.objects(day__mod=(datetime.today().weekday(), 0))
        question = questions[len(questions) - 1]
        update_status(call.message.chat.id, "standby")

        if call.data == question.correct_answer:
            bot.send_message(
                call.message.chat.id, "✅ Верно! Ваш ответ засчитан.")
        else:
            bot.send_message(
                call.message.chat.id, "❌ К сожалению, ваш ответ неправильный.")


@bot.callback_query_handler(lambda call: call.data in SCROLL_BTNS)
def query_handler_scroll(call):
    """
        Обновление сообщения с лидербордом при нажатии кнопок назад / вперёд.
    """

    bot.answer_callback_query(call.id)

    if call.data == "◀️":
        updated_msg = "Назад..." + str(randint(1, 9999999999))
    else:
        updated_msg = "Вперёд.." + str(randint(1, 99999999999))

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        text=updated_msg,
        message_id=call.message.message_id,
        reply_markup=create_markup(SCROLL_BTNS)
    )


if __name__ == "__main__":
    multiprocessing.Process(target=schedule_message, args=()).start()
    bot.polling()
