"""
      ===== IU7QUIZ BOT CONFIG =====
      Copyright (C) 2020 IU7OG Team.

      Настройки и константы для бота.
"""

import os

TOKEN = os.environ['TOKEN']
DB_NAME = os.environ['DB_NAME']
DB_USER = os.environ['DB_USER']
DB_PASS = os.environ['DB_PASS']
HOST = f"mongodb://{DB_USER}:{DB_PASS}@127.0.0.1:27017/{DB_NAME}"
GROUPS = ["ИУ7-21Б", "ИУ7-22Б", "ИУ7-23Б", "ИУ7-24Б", "ИУ7-25Б", "ИУ7-26Б"]
