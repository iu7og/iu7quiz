"""
      ===== IU7QUIZ TELEGRAM BOT =====
      Copyright (C) 2020 IU7OG Team.

      Телеграм бот, помогающий студентам кафедры ИУ7 закрепить лекционный материал по курсу
      "Программирование на СИ", путём рассылки вопросов по прошедшим лекциям.
"""

import time
from multiprocessing import Process
import telebot
import schedule
from dbinstances import Student
from config import BOT_TOKEN, GROUPS

bot = telebot.TeleBot(BOT_TOKEN)

def schedule_message():
    """
        ...
    """
    def sending_messages():
        """
            wrapper
        """

        for student in Student.objects():
            bot.send_message(student.user_id, "Тестовое сообщение...")

    schedule.every(2).minutes.do(sending_messages)
    while True:
        schedule.run_pending()
        time.sleep(1)


@bot.message_handler(commands=['start'])
def authorization(message):
    """
        Уведомление студента о выборе группы, отправление сообщений с inline-кнопками.
    """

    if not Student.objects(user_id=message.from_user.id):
        markup = telebot.types.InlineKeyboardMarkup()

        for group_odd, group_even in zip(GROUPS[::2], GROUPS[1::2]):
            markup.add(
                telebot.types.InlineKeyboardButton(text=group_odd, callback_data=group_odd),
                telebot.types.InlineKeyboardButton(text=group_even, callback_data=group_even)
            )

        bot.send_message(message.chat.id, "💬 Укажите свою группу: ", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "⚠️ Вы уже зарегистрированы в системе.")


@bot.message_handler(commands=['unreg'])
def delete(message):
    """
        debug
    """
    print(message)
    print(Student.objects(user_id=message.from_user.id))
    Student.objects(user_id=message.from_user.id).delete()
    print(Student.objects(user_id=message.from_user.id))


@bot.message_handler(commands=['leaderboard'])
def show_leaderboard(message):
    """
        Пока что просто заготовка под лидерборд
    """

    if Student.objects(user_id=message.from_user.id):
        msg = ''
        for student in Student.objects():
            msg += "Логин: " + str(student.login) + "\nГруппа: " + student.group + "\n"
    else:
        msg = '❌ Пожалуйста, завершите процес регистрации в системе (укажите свою группу).'

    bot.send_message(message.chat.id, msg)


@bot.message_handler(commands=['help'])
def help_message(message):
    """
        заготовка под хелпмеседж
    """

    bot.send_message(message.chat.id, "Тут будет какое то хелпмесседж...")


@bot.message_handler(func=lambda message: True)
def echo_message(message):
    """
        хз че тут будет, если вообще будет
    """
    bot.reply_to(message, 'форкбота...')


@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    """
        Обработка нажатия inline-кнопок студентом.
    """

    bot.answer_callback_query(call.id)
    if not Student.objects(user_id=call.message.chat.id):
        student = Student(
            user_id=call.message.chat.id,
            login=call.message.chat.username,
            group=call.data
        )

        student.save()
        bot.send_message(call.message.chat.id, '✅ Вы успешно зарегистрированы в системе.')


if __name__ == "__main__":
    Process(target=schedule_message, args=()).start()
    bot.polling()
