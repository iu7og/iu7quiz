"""
      ===== IU7QUIZ BOT CONFIG =====
      Copyright (C) 2020 IU7OG Team.

      Настройки и константы для бота.
"""

from math import log
from datetime import datetime
import os

# Конфигурация серверной части бота.
TOKEN = os.environ['TOKEN']

# Конфигурация MongoDB.
DB_NAME = os.environ['DB_NAME']
DB_USER = os.environ['DB_USER']
DB_PASS = os.environ['DB_PASS']
DB_HOST = os.environ['DB_HOST']
HOST = f"mongodb://{DB_USER}:{DB_PASS}@{DB_HOST}:27017/{DB_NAME}"

# Конфигурация клиентской части бота.
GROUPS_BTNS = ("ИУ7-21Б", "ИУ7-22Б", "ИУ7-23Б", "ИУ7-24Б", "ИУ7-25Б", "ИУ7-26Б")
ANSWERS_BTNS = {"A": 1, "B": 2, "C": 3, "D": 4}
SCROLL_BTNS = ("◀️", "▶️")
READY_BTN = "Готов"
LB_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}
LB_PAGE_SIZE = 10
LECTOR_ID = "ID"
LIVE_Q_DELAY = 60
FIRST_CLASS = datetime(2020, 2, 6, 21, 37)
CLASS_OFFSET = 14

# Конфигурация рейтинговой системы.
# Коэффициенты главной формулы.
WAITING_FACTOR = 0.35
ANSWER_TIME_FACTOR = 1 - WAITING_FACTOR
ERR_DCRMNT_FACTOR = 0.2
COMPLEXITY_FACTOR = 0.2
SYMBOLS_PER_SECOND = 25

# Коэффициент потери баллов за ожидание (кол-во часов,
# когда из-за ожидания теряется 50% баллов за ожидание).
HALF_WAITING_HOURS = 12
HALF_WAITING_FACTOR = log(2) / HALF_WAITING_HOURS

# Флаг отладочной печати (если True, то она будет)
DEV_MODE_RATING = False
DEV_MODE_QUEUE = True

# Настройки времени
FIRST_QUESTION_DAY = datetime(2020, 2, 5, 10, 0)
