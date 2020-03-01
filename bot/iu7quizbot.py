"""
      ===== IU7QUIZ TELEGRAM BOT =====
      Copyright (C) 2020 IU7OG Team.

      Telegram-бот, помогающий студентам кафедры ИУ7 закрепить лекционный материал по курсу
      "Программирование на СИ", путём рассылки вопросов по прошедшим лекциям.
"""

from datetime import datetime, date
from random import shuffle, choice, seed, randint

import logging
import ssl

import json
import time
import multiprocessing
import telebot
import schedule
import mongoengine

from aiohttp import web

import bot.config as cfg
import bot.statistics as stat
import bot.rating as rt
from bot.dbinstances import Student, Question
from bot.gsparser import parse_to_mongo

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

bot = telebot.TeleBot(cfg.TOKEN)
mongoengine.connect(host=cfg.HOST)

app = web.Application()


async def handle(request):
    """
        AIOHTTP обработчик.
    """

    if request.match_info.get("token") == bot.token:
        request_body_dict = await request.json()
        update = telebot.types.Update.de_json(request_body_dict)
        bot.process_new_updates([update])
        return web.Response()

    return web.Response(status=403)


app.router.add_post("/{token}/", handle)

bot.remove_webhook()
bot.set_webhook(url=cfg.WEBHOOK_URL_BASE + cfg.WEBHOOK_URL_PATH)

context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_cert_chain(cfg.WEBHOOK_SSL_CERT, cfg.WEBHOOK_SSL_PRIV)


def generate_r2d2():
    """
        Создание братьев R2-D2.
    """
    seed(datetime.now())
    return f"R{randint(0, 100)}-D{randint(0, 100)}"


def find_student(user_id, students):
    """
        Поиск студента по user id в рейтинге всех студентов.
    """

    student = Student.objects(user_id=user_id).first()
    student_info = list(filter(lambda x: x[0] == student.login, students))[0]
    return student_info, students.index(student_info) + 1


def create_leaderboard_page(btn, user_id, prev_page=None):
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
            new_page_start = int(split_page[2][:split_page[2].find(".")]) - cfg.LB_PAGE_SIZE - 1

    medals = cfg.LB_MEDALS.copy()  # Иначе в определенный момент память просто закончится.
    page_list = students[new_page_start:new_page_start + cfg.LB_PAGE_SIZE]

    student, place = find_student(user_id, students)
    page_text = f"🔥 Ваше место в рейтинге: *{medals.setdefault(place, str(place) + '. ')}*" + \
        f"Рейтинг: *{student[1]:.2f}*\n\n"

    for i, page in enumerate(page_list):
        prefix = "" if page[0][0] == "[" else "@"
        curr_index = i + 1 + new_page_start
        tmp = page[0].replace("_", "\\_")
        page_text += f"{medals.setdefault(curr_index, str(curr_index) + '. ')}" + \
            f"{prefix}{tmp} ({page[2]}). Рейтинг: {page[1]:.2f}\n"

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
        if (student.status == "standby" or student.status == "live_question") \
                and len(student.queue) and student.queue[0]["days_left"] <= 0:
            student.status = "is_ready"

            # Функция возвращает измененный объект студента (имитация передачи по ссылке).
            # (p.s.: в функции записывается время отправления сообщения с вопросом о готовности).
            student = send_single_confirmation(student, True)
            student.save()


def send_single_confirmation(student, is_first):
    """
        Отправка одному студенту сообщения с вопросом о готовности отвечать на вопрос.
    """

    # Время отправки сообщения записывается в поле студента (qtime_start).
    student.qtime_start = time.time()

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(text=cfg.READY_BTN, callback_data=cfg.READY_BTN))

    if is_first:
        message = "Доброго времени суток! " + \
            "Готовы ли вы сейчас ответить на вопросы по прошедшей лекции?"
    else:
        message = "💡 У меня появился к Вам новый вопрос! Готовы ответить?"

    try:
        bot.send_message(student.user_id, "📝")
        bot.send_message(student.user_id, message, reply_markup=markup)
    except telebot.apihelper.ApiException:
        print("Заблокировал бота:", student.user_id, student.login)

    return student


def update_queue():
    """
        Функция добавления "вопроса дня".
    """

    today_question_day = (datetime.today() - cfg.FIRST_QUESTION_DAY).days

    for student in Student.objects(status__ne="registration"):

        if cfg.DEV_MODE_QUEUE:
            print(f"Daily update queue of user: {student.login}\nQueue before: {student.queue}")

        # Кол-во дней ожидания у вопросов, которые уже находятся в очереди, уменьшается на 1
        # (p.s.: Если кол-во дней ожидания <= 0, то вопрос должен быть отправлен сегодня).
        need_miss_msg = False
        for questions in student.queue:
            questions["days_left"] -= 1
            if questions["days_left"] <= -cfg.MISS_DAYS:
                need_miss_msg = True

        if need_miss_msg:
            bot.send_message(student.user_id, cfg.MISS_MESSAGE)

        # Вопрос дня добавляется на самое первое место
        for i in range(today_question_day * cfg.QUESTION_PORTION,
                       (today_question_day + 1) * cfg.QUESTION_PORTION):
            student.queue.insert(0, {"question_day": i, "days_left": 0})

        if cfg.DEV_MODE_QUEUE:
            print(f"Queue after: {student.queue}\n")

        student.save()

    # Предложения ответить будут разосланы тем, кто свободен.
    send_confirmation()


def end_notifications():
    """
        Функция рассылки информации о том, что больше нельзя задавать вопросы лектору.
    """

    if date.today().isocalendar()[1] % 2:
        for student in Student.objects(status__ne="registration"):
            bot.send_message(student.user_id,
                             "🛑 Начиная с этого момента вы больше не можете задать вопрос лектору.")


def questions_notification():
    """
        Функция рассылки информации о том, что можно задавать вопросы лектору.
    """

    if date.today().isocalendar()[1] % 2:
        for student in Student.objects(status__ne="registration"):
            bot.send_message(student.user_id, "📬")
            bot.send_message(student.user_id,
                             "Начиная с этого момента вы можете задать вопрос лектору.")


def schedule_bot():
    """
        Планировщик сообщений.
    """

    schedule.every().tuesday.at("08:30").do(questions_notification)
    schedule.every().day.at("09:00").do(parse_to_mongo)
    schedule.every().tuesday.at("10:05").do(end_notifications)
    schedule.every().day.at("10:05").do(update_queue)

    while True:
        schedule.run_pending()
        time.sleep(1)

        
@bot.message_handler(commands=["start"])
def authorization(message):
    """
        Выбор учебной группы для авторизации.
    """

    if not Student.objects(user_id=message.chat.id):

        questions_queue = list()
        count_missed_questions = \
            (datetime.today() - cfg.FIRST_QUESTION_DAY).days * cfg.QUESTION_PORTION

        if count_missed_questions > 0:
            questions_queue = [{"question_day": i, "days_left": 0}
                               for i in range(count_missed_questions + cfg.QUESTION_PORTION)]

        login = message.chat.username

        if message.chat.username is None:
            login = f"[{generate_r2d2()}](tg://user?id={str(message.chat.id)})"

        student = Student(
            user_id=message.chat.id,
            login=login,
            status="registration",
            queue=questions_queue
        )

        bot.send_message(
            message.chat.id,
            "💬 Укажите свою учебную группу: ",
            reply_markup=create_markup(cfg.GROUPS_BTNS)
        )

        student.save()

    else:
        bot.send_message(message.chat.id, "⚠️ Вы уже зарегистрированы в системе.")


@bot.message_handler(func=lambda msg: Student.objects(user_id=msg.chat.id).first() is None)
def unregistered_handler(msg):
    authorization(msg)
    print("Айди клоуна: ", msg.chat.id, msg.chat.username)


@bot.message_handler(commands=["leaderboard"])
def show_leaderboard(message):
    """
        Вывод лидерборда среди учеников.
    """

    student = Student.objects(user_id=message.from_user.id).first()

    if student.status == "standby" and int(time.time()) - student.lb_timeout > cfg.LB_TIMEOUT:
        student.lb_timeout = int(time.time())
        student.save()

        page = create_leaderboard_page(cfg.SCROLL_BTNS[1], message.chat.id)

        if Student.objects.count() > cfg.LB_PAGE_SIZE:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton(
                    text=cfg.SCROLL_BTNS[1],
                    callback_data=cfg.SCROLL_BTNS[1]
                )
            )

            bot.send_message(message.chat.id, page, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, page, parse_mode="Markdown")

    elif student.status == "standby":
        bot.send_message(message.chat.id, "⏰ Вы недавно вызывали лидерборд. Повторите через " +
                         f"{cfg.LB_TIMEOUT - (int(time.time()) - student.lb_timeout)} секунд.")

    else:
        bot.send_message(message.chat.id,
                         "⛔️ Прежде чем вызвать лидерборд, ответьте на вопросы бота.")


@bot.message_handler(commands=["info"])
def info_message(message):
    """
        Информация о боте.
    """

    student = Student.objects(user_id=message.from_user.id).first()

    if student.status == "standby":
        bot.send_message(message.chat.id, cfg.INFO_MSG, parse_mode="markdown")

    else:
        bot.send_message(message.chat.id,
                         "⛔️ Прежде чем посмотреть информацию, ответьте на вопросы бота.")


@bot.message_handler(commands=["help"])
def help_message(message):
    """
        Помощь в использовании бота.
    """

    student = Student.objects(user_id=message.from_user.id).first()

    if student.status == "standby":
        bot.send_message(message.chat.id, cfg.HELP_MSG, parse_mode="markdown")

    elif student.status == "registration":
        bot.send_message(message.chat.id, "️👮🏻‍♀️ Выберите группу.")

    elif student.status == "is_ready":
        answer = "📚 Нажмите кнопку готов, если готовы ответить на вопрос."
        bot.send_message(message.chat.id, answer)

    elif student.status == "question":
        variants = ["🅰️", "🅱️"]
        answer = f"Я ничего не понимаю на человеческом, но вариант {choice(variants)} " \
            "выглядит привлекательно!"
        bot.send_message(message.chat.id, answer)

    elif student.status == "live_question":
        answer = "📚 Задайте свой вопрос:"
        bot.send_message(message.chat.id, answer)

    else:
        bot.send_message(message.chat.id, "Ничем не могу помочь, напишите разработчикам...")


@bot.message_handler(commands=["rules"])
def rules_message(message):
    """
        Правила работы бота.
    """

    student = Student.objects(user_id=message.from_user.id).first()

    if student.status == "standby":
        bot.send_message(message.chat.id, cfg.RULES_MSG, parse_mode="markdown")

    elif student.status == "live_question":
        bot.send_message(message.chat.id, "⛔️ Прежде чем посмотреть правила, задайте свой вопрос.")

    else:
        bot.send_message(message.chat.id,
                         "⛔️ Прежде чем посмотреть правила, ответьте на вопросы бота.")


@bot.message_handler(commands=["stat"])
def send_stat(message):
    """
        Отправляет сообщение со статистикой при запросе пользователя (командой /stat).
    """

    student = Student.objects(user_id=message.chat.id).first()
    if student.status == "standby":
        bot.send_message(message.chat.id, stat.stat_msg(student), parse_mode="markdown")
    else:
        bot.send_message(message.chat.id,
                         "⛔️ Прежде чем вызвать статистику, ответьте на вопросы бота.")


@bot.message_handler(commands=["question"])
def live_question_handler(message):
    """
        Задать вопрос преподавателю во время лекции.
    """

    if student := Student.objects(user_id=message.chat.id):
        student = student.first()

        if student.status == "standby":
            time_delta = datetime.today() - cfg.FIRST_CLASS_DAY
            if time_delta.seconds <= cfg.CLASS_DURATION and time_delta.days % cfg.CLASS_OFFSET == 0:
                if time.time() - student.last_live_q >= cfg.LIVE_Q_DELAY:
                    student.last_live_q = time.time()
                    student.status = "live_question"

                    student.save()

                    bot.send_message(message.chat.id, "🖋️ Введите ваш вопрос:")
                else:
                    spam_time = int(cfg.LIVE_Q_DELAY - (time.time() - student.last_live_q))
                    time_msg = f"⏰ Подождите {spam_time} секунд прежде чем еще раз задавать вопрос."
                    bot.send_message(message.chat.id, time_msg)
            else:
                bot.send_message(
                    message.chat.id, "⛔ Вопросы можно задавать только во время лекции.")
        elif student.status == "live_question":
            bot.send_message(message.chat.id, "🖋️ Введите ваш вопрос:")
        else:
            bot.send_message(
                message.chat.id, "⛔ Прежде чем задавать вопросы, ответьте на вопросы бота.")


@bot.message_handler(
    func=lambda msg: Student.objects(user_id=msg.chat.id).first().status == "live_question")
def question_sender(msg):
    """
        Пересылка вопроса преподавателю.
    """

    student = Student.objects(user_id=msg.chat.id).first()

    bot.send_message(cfg.LECTOR_ID, msg.text)
    bot.send_message(msg.chat.id, "📮 Ваш вопрос принят!")

    student.status = "standby"
    student.save()


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


def send_question(student):
    """
        Функция отправки вопроса (отправляет вопрос и замеряет нужную статистику).
    """

    # Номер вопроса берется у первого вопроса в очереди.
    day = student.queue[0]["question_day"]
    question = Question.objects(day=day).first()

    if cfg.DEV_MODE_QUEUE:
        print(f"Queue of {student.login} after ready confirmation: {student.queue}",
              f"Got day {day}", sep='\n', end='\n\n')

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
        student.user_id,
        message,
        reply_markup=create_markup(list(cfg.ANSWERS_BTNS.keys()))
    )

    student.status = "question"
    student.save()


@bot.callback_query_handler(lambda call: call.data == cfg.READY_BTN)
def query_handler_ready(call):
    """
        Высылание вопроса с inline-кнопками тем,
        кто подтвердил готовность отвечать на вопрос.
    """

    bot.answer_callback_query(call.id)
    student = Student.objects(user_id=call.message.chat.id).first()

    if student.status == "is_ready":
        send_question(student)


@bot.callback_query_handler(lambda call: call.data in cfg.ANSWERS_BTNS)
def query_handler_questions(call):
    """
        Обработка нажатия inline-кнопок с выбором ответа студентом.
        Обновление статистики после ответа на вопрос.
    """

    bot.answer_callback_query(call.id)
    student = Student.objects(user_id=call.message.chat.id).first()

    if student.status == "question":
        day = student.queue[0]["question_day"]
        question = Question.objects(day=day).first()

        if cfg.DEV_MODE_QUEUE:
            print(f"Queue of {student.login} after answering the question (before)" +
                  f": {student.queue}", f"Got day {day}", sep='\n', end='\n\n')

        datastore = json.loads(student.data)

        # 4 - emoji + вариант ответа (перед самим ответом)
        student_answer = call.message.text.split("\n")[cfg.ANSWERS_BTNS[call.data] + 1][4:]
        correct_answer = question.answers[cfg.ANSWERS_BTNS[question.correct_answer] - 1]

        # Очередь очищается от текущего вопроса (и обзаводится новым в некоторых случаях)
        # внутри handler'ов.
        if student_answer == correct_answer:
            datastore[day], question, student.queue = stat.right_answer_handler(
                datastore[day],
                question,
                (time.time(), student.qtime_start, student.waiting_time),
                student.queue
            )

            bot.send_message(call.message.chat.id, "✅ Верно! Ваш ответ засчитан.")
        else:
            datastore[day], question, student.queue = stat.wrong_answer_handler(
                datastore[day], question, student.queue
            )

            bot.send_message(call.message.chat.id,
                             "❌ К сожалению, ответ неправильный, и он не будет засчитан.")

        question.save()

        # Обновить статистику.
        student.data = json.dumps(datastore)
        student.qtime_start = time.time()
        student.waiting_time = 0

        if cfg.DEV_MODE_QUEUE:
            print(f"Queue of {student.login} after answering the question (after) " +
                  f": {student.queue}", end='\n\n')
            print(f"Check update of the stat: {datastore[day]}\n")

        # Если есть вопросы, запланированные на сегодня, то еще раз спросить о готовности
        # и задать вопрос.
        if len(student.queue) != 0 and student.queue[0]["days_left"] <= 0:
            if cfg.DEV_MODE_QUEUE:
                print("Asking one more question\n")
            send_question(student)
        else:
            if cfg.DEV_MODE_QUEUE:
                print("No more questions for today")
            student.status = "standby"
            bot.send_message(call.message.chat.id,
                             "🏁 На сегодня у меня нет больше к тебе вопросов, до завтра!")

        student.save()


@bot.callback_query_handler(lambda call: call.data in cfg.SCROLL_BTNS)
def query_handler_scroll(call):
    """
        Обновление сообщения с лидербордом при нажатии кнопок назад / вперёд.
    """

    bot.answer_callback_query(call.id)
    new_page, is_border = create_leaderboard_page(
        call.data,
        call.message.chat.id,
        call.message.text
    )

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
        reply_markup=markup,
        parse_mode="Markdown"
    )


if __name__ == "__main__":
    multiprocessing.Process(target=schedule_bot, args=()).start()

    web.run_app(
        app,
        host=cfg.WEBHOOK_LISTEN,
        port=cfg.WEBHOOK_PORT,
        ssl_context=context,
    )
