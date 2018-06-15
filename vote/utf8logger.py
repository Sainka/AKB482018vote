# -*- coding: utf-8 -*-
import os
import sys
from random import randint

p = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if p not in sys.path:
    sys.path.insert(0, p)

import sys, logging


def equalUtf8(coding):
    return coding is None or coding.lower() in ('utf8', 'utf-8', 'utf_8')


class CodingWrappedWriter(object):
    def __init__(self, coding, writer):
        self.flush = getattr(writer, 'flush', lambda: None)

        wcoding = getattr(writer, 'encoding', None)
        wcoding = 'gb18030' if (wcoding in ('gbk', 'cp936')) else wcoding

        if not equalUtf8(wcoding):
            self._write = lambda s: writer.write(
                s.decode(coding).encode(wcoding, 'ignore')
            )
        else:
            self._write = writer.write

    def write(self, s):
        self._write(s)
        self.flush()


import io

if hasattr(sys.stdout, 'buffer') and (not equalUtf8(sys.stdout.encoding)):
    if sys.stdout.encoding in ('gbk', 'cp936'):
        coding = 'gb18030'
    else:
        coding = 'utf-8'
    utf8Stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=coding)
else:
    utf8Stdout = sys.stdout


def Utf8Logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        ch = logging.StreamHandler(utf8Stdout)
        fmt = '[%(asctime)s] [%(levelname)s] %(message)s'
        datefmt = '%Y-%m-%d %H:%M:%S'
        ch.setFormatter(logging.Formatter(fmt, datefmt))
        logger.addHandler(ch)
    return logger


logging.getLogger("").setLevel(logging.CRITICAL)

utf8Logger = Utf8Logger('Utf8Logger')

_thisDict = globals()

for name in ('CRITICAL', 'ERROR', 'WARN', 'INFO', 'DEBUG'):
    _thisDict[name] = getattr(utf8Logger, name.lower())

RAWINPUT = input


def Utf8File(lname):
    logger = logging.getLogger(lname)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        ch = logging.FileHandler('%s.log' % lname, mode='w', encoding='utf-8')
        fmt = "%(asctime)s, %(message)s"
        datefmt = '%Y-%m-%d %H:%M:%S'
        ch.setFormatter(logging.Formatter(fmt, datefmt))
        logger.addHandler(ch)
    return logger


utf8FileList = {}


def FILE(s, lname="vote"):
    global utf8FileList
    if lname not in utf8FileList:
        utf8FileList[lname] = Utf8File(lname)
    utf8FileList[lname].info(s)


def PRINT(s, end='\n'):
    utf8Stdout.write(s + end)
    utf8Stdout.flush()


def test():
    s = RAWINPUT("请输入一串中文：")
    PRINT(s)
    INFO(s)
    CRITICAL(s)
    FILE(s)


if __name__ == '__main__':
    test()
