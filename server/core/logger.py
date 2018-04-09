# -*- coding:utf-8 -*-
import os
import logging
from logging import handlers

from conf.settings import(
    LOG_PATH, LOG_LEVEL, LOG_FORMATTER
)


def set_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    fh = logging.FileHandler(os.path.join(LOG_PATH,name+'.log'),encoding='utf-8')
    # fh = handlers.TimedRotatingFileHandler(filename=os.path.join(LOG_PATH,name+'.log'),when='S',interval=2,backupCount=2,encoding='utf-8')
    logger.addHandler(fh)

    fh_formatter = LOG_FORMATTER
    fh.setFormatter(fh_formatter)

    return logger