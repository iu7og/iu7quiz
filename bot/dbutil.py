"""
      ===== IU7QUIZ DB UTIL =====
      Copyright (C) 2020 IU7OG Team.

      Работа с БД прямыми запросами.
"""

from telebot import apihelper

from bot.gsparser import parse_to_mongo
from bot.iu7quizbot import update_queue, send_confirmation, bot
from bot.config import ALLOWED_STATUS
from bot.dbinstances import Student, Question


def usage():
    """
        Информаиця об использовании утилиты.
    """

    msg = "🔥 IU7QUIZ DB UTIL\nДоступные команды:" + \
        "\t1. Вызввать update_queue - /dev updqueue\n" + \
        "\t2. Вызвать send_confirmation - /dev sndconfirm\n" + \
        "\t3. Вызвать parse_to_mongo - /dev prsmongo\n" + \
        "\t4. Разослать сообщение - /dev sendmsg <status> <сообщение>\n" + \
        "\t4. Разослать сообщение по ID - /dev sendmsgid <id> <сообщение>\n" + \
        "\t5. Состояние фонового процесса - /dev checkproc\n" + \
        "\t6. Посмотреть последний загруженный вопрос - /dev lastquest\n" + \
        "\t7. Посмотреть статус юзера - /dev status <id>\n" + \
        "\t8. Изменить статус юзера - /dev change_status <id> <status>\n\n" + \
        "❗️ Узнать ID: @userinfobot"

    return msg


def form_request(message):
    """
        Парсинг сообщения в запрос в виде словаря.
    """

    splitted = message.split()
    if len(splitted) == 2:
        request = {"command": splitted[1]}

    elif len(splitted) == 3:
        request = {"command": splitted[1], "data" : {"status": splitted[2]}}

    elif len(splitted) == 4:
        command = splitted[1]
        message = splitted[3]

        if command == "sendmsg":
            request = {
                "command": command,
                "data": {"status": splitted[2], "message": message}
            }

        elif command == "sendmsgid":
            request = {
                "command": command,
                "data": {"id": int(splitted[2]), "message": message}
            }

        else:
            request = {
                "command": command,
                "data": {"id": int(splitted[2]), "status": splitted[3]}
            }
    else:
        request = {"command": "usage"}

    return request


def upd_queue_handler():
    """
        Вызов функции update_queue.
    """

    try:
        update_queue()
    except Exception:
        return "❌ При выполнение update_queue возникла ошибка"

    return "✅ update_queue успешно выполнена"


def send_confirm_handler():
    """
        Вызов функции send_confirmation.
    """

    try:
        send_confirmation()
    except Exception:
        return "❌ При выполнение send_confirmation возникла ошибка"

    return "✅ send_confirmation успешно выполнена"


def parse_mongo_handler():
    """
        Вызов функции parse_to_mongo.
    """

    try:
        parse_to_mongo()
    except Exception:
        return "❌ При выполнение parse_to_mongo возникла ошибка"

    return "✅ parse_to_mongo успешно выполнена"


def blocked_users_message(users):
    """
        Формирование сообщения о заблокированных пользователях.
    """

    msg = ""
    for user in users:
        msg += user["login"] + str(user["id"]) + "\n"

    return msg


def message_by_status(data):
    """
        Рассылка сообщения по полю status.
    """

    if len(data) != 2:
        return "❌ Неверно заданны аргументы. См. /dev usage"

    if data["status"] not in ALLOWED_STATUS:
        return f"✅ Статуса {data['status']} не существует."

    blocked_id = []
    for student in Student.objects(status=data["status"]):
        try:
            bot.send_message(student.user_id, data["message"])
        except apihelper.ApiException:
            blocked_id.append({"login": student.login, "id": student.user_id})

    if blocked_id:
        info = "⚠️ Не удалось отправить сообщения для:\n" + blocked_users_message(blocked_id)
    else:
        info = f"✅ Сообщение для юзеров со стаусом {data['status']} успешно отправленно."

    return info


def message_by_id(data):
    """
        Отправка сообщения по ID.
    """

    if Student.objects(user_id=data["id"]) is None:
        return f"❌ ID {data['id']} нет в БД."

    bot.send_message(data["id"], data["message"])

    return f"✅ Сообщение для ID: {data['id']} успешно отправленно."


def check_process():
    """
        Информация о существовании параллельного процесса.
    """

    return "В разработке"


def check_last_question():
    """
        Вывод последних трех вопросв.
    """

    count = Question.objects.count()
    last3_qst = Question.objetcs[count - 3:count]

    msg = "Последние 3 вопроса в ДБ:\n"
    for question in last3_qst:
        msg += question.text + "\n"

    return msg


def check_status(data):
    """
        Получение информации о состоянии (статуса) юзера.
    """

    if student:= Student.objects(user_id=data["user_id"]) is None:
        return f"❌ ID {data['user_id']} нет в БД."

    student = student.first()

    return f"ID: {student.user_id}, статус: {student.status}"


def update_status(data):
    """
        Задача состояния (статуса) юзера в ручную.
    """

    if data["status"] not in ALLOWED_STATUS:
        return f"✅ Статуса {data['status']} не существует."

    if student:= Student.objects(user_id=data["id"]) is None:
        return f"❌ ID {data['user_id']} нет в БД."

    student = student.first()
    student.status = data["status"]
    student.save()

    return f"✅ Статус {data['status']} для {data['id']} успешно установлен."


def dev_menu(request):
    """
        Обращение к внутренностям бота.
    """

    menu = {
        "updqueue": upd_queue_handler,
        "sndconfirm": send_confirm_handler,
        "prsmongo": parse_mongo_handler,
        "sendmsg": message_by_status,
        "sendmsgid": message_by_id,
        "checkproc": check_process,
        "lastquest": check_last_question,
        "status": check_status,
        "change_status": update_status,
        "usage": usage
    }

    if request["command"] in menu:
        func = menu.get(request["command"])
    else:
        func = menu.get("usage")

    return func(request["data"]) if "data" in request else func()
