# -*- coding:utf-8 -*-
import os
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCOUNTS_FILE = os.path.join(BASE_DIR,'conf','accounts.ini')

HOST = '127.0.0.1'
PORT = 8083

MAX_CONCURRENT_COUNT = 2

LOG_PATH = os.path.join(BASE_DIR,'log')
LOG_LEVEL = logging.INFO
LOG_FORMATTER = logging.Formatter(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p')