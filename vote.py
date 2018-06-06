import argparse
import os
import pickle
import re
import signal
import sys
import time
from random import randint

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

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


def Utf8File(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logfile = os.path.abspath('vote-%d.log' % randint(100000, 999999))
        ch = logging.FileHandler(logfile, mode='w', encoding='utf-8')
        fmt = "'%(asctime)s', %(message)s"
        datefmt = '%Y-%m-%d %H:%M:%S'
        ch.setFormatter(logging.Formatter(fmt, datefmt))
        logger.addHandler(ch)
    return logger


utf8File = None


def FILE(s):
    global utf8File
    if not utf8File:
        utf8File = Utf8File('file')
    utf8File.info(s)


def PRINT(s, end='\n'):
    utf8Stdout.write(s + end)
    utf8Stdout.flush()

class State():
    def __init__(self, s1, s2, name, url, msg):
        self.s1 = s1
        self.s2 = s2
        self.name = name
        self.url = url
        self.msg = msg

    def __str__(self):
        return "'%s', '%s', '%s', '%s', %s" % (self.s1, self.s2, self.name, self.url, str(self.msg)[1:-1])


class PlickelTool():
    def load(self, filePath):
        if os.path.exists(filePath):
            with open(filePath, 'rb') as f:
                return pickle.load(f)
        return None, None

    def save(self, filePath, obj):
        with open(filePath, 'wb') as f:
            pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


class VoteBot:
    from selenium import webdriver
    def __init__(self, headless=False):
        self.driver = self.getBrowser(headless)
        if headless:
            INFO("浏览器初始化完成(headless)")
        else:
            INFO("浏览器初始化完成")

    def initVoteInfo(self):
        fp = os.path.abspath('numberList.pickle');
        pt = PlickelTool()
        self.team, self.number = pt.load(fp)
        if not self.number or not self.team:
            self.team = self.getTeamList()
            self.number = self.getNumberList()
            pt.save(fp, (self.team, self.number))
        else:
            self.get('https://akb48-sousenkyo.jp/akb/search/results?t_id=1', '.wrap h1')
        INFO("成功获取成员列表成功")

    def getTeamList(self):
        self.get('https://akb48-sousenkyo.jp/akb/search/teams', '.wrap h1')
        a = self.find_by_css_s('dd a')
        return [(dd.text, dd.get_attribute('href')) for dd in a]

    def getNumberInfo(self, link):
        self.get(link, '.wrap h1')
        list = self.find_by_css_s('dd a')
        return [(dd.text, dd.get_attribute('href')) for dd in list]

    def getNumberList(self):
        l = []
        for (team, link) in self.team:
            l += self.getNumberInfo(link)

        dic = {}
        for (name, link) in l:
            a = name.split('／')
            dic.update({a[0]: (a[0], a[1], link)})
        return dic

    def getBrowser(self, headless=False):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('headless')
        options.add_argument('lang=zh_CN.UTF-8')
        options.add_argument(
            'user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36"')
        browser = webdriver.Chrome(chrome_options=options)
        browser.implicitly_wait(10)
        return browser

    def vote(self, s1, s2, name):
        url, msg = self.getLinkWithNamecheck(name, False)
        if not url: return [msg]
        ss1, ss2 = self.serialCheck(s1, s2)
        if not ss1 or not ss2:
            return ['(%s,%s)错误的序列号格式' % (s1, s2)]
        return self.voteNoSafeCheck(s1, s2, name, url)

    def voteNoSafeCheck(self, s1, s2, name, url):
        self.get(url, '#vote a')
        if self.checkVotePaper(name):
            self.sendKeys('#serial1', s1)
            self.sendKeys('#serial2', s2)
            self.click('#vote a')
            return State(s1, s2, name, url, self.getMsg());
        return State(s1, s2, name, url, '投票失败请检查你的网络')

    def voteFromFile(self, filePath, name):
        url, msg = self.getLinkWithNamecheck(name)
        if not url: return msg

        INFO('验证成功，倒计时13s后开始投票给(%s),如果有任何疑问，您可以使用(ctrl + c)主动退出程序' % name)
        self.countdown(13)
        INFO('投票开始(%s)' % name)

        with open(filePath) as f:
            id = 0
            while True:
                lines = f.readlines(100)
                if not lines: break
                for serial in lines:
                    if len(serial) > 0:
                        s1, s2 = self.serialCheck(serial)
                        if s1 and s2:
                            state = self.voteNoSafeCheck(s1, s2, name, url)
                        else:
                            state = State(serial.strip(), '', name, url, ('投票エラー', '注册码格式错误'))
                        INFO('%d, ' % id + str(state))
                        FILE('%d, ' % id + str(state))
                        id += 1

        return '投票完成(%s)' % name

    def checkVotePaper(self, name):
        return True in [(name in e.text) for e in self.find_by_css_s('.lead')]

    def getMsg(self, time=5):
        WebDriverWait(self.driver, time).until(EC.visibility_of(self.find_by_css('.wrap h1')))
        return [self.find_by_css('.wrap h1').text] + [e.text.replace('\n', '') for e in self.find_by_css_s('.lead')]

    def sendKeys(self, css, s):
        self.find_by_css(css).send_keys(s)

    def click(self, css):
        self.find_by_css(css).click()

    def find_by_css(self, css):
        return self.driver.find_element_by_css_selector(css)

    def find_by_css_s(self, css):
        return self.driver.find_elements_by_css_selector(css)

    def get(self, url, css, time=5):
        self.driver.get(url)
        WebDriverWait(self.driver, time).until(EC.visibility_of(self.find_by_css(css)))

    def _find_link_by_name(self, name):
        if name in self.number:
            return self.number[name]
        else:
            return None, None, None

    def close(self):
        if self.driver:
            self.driver.close()

    def countdown(self, lineLength, ds=1, fs='=', fs2=['-', '\\', '|', '/'], bs=''):
        def ext(signum, frame):
            print('')
            ERROR('您使用(ctrl + c)主动退出了程序')
            exit(0)

        signal.signal(signal.SIGINT, ext)
        signal.signal(signal.SIGTERM, ext)

        lineTmpla = '{:%s<%s} {} {:<2}' % (bs, lineLength)
        for s in range(lineLength):
            j = lineLength - s
            print('\r' + lineTmpla.format(fs * j, fs2[j % (len(fs2))], j), end='')
            time.sleep(ds)
        print('\r' + '  ' * lineLength + '\r', end='')

    def inputCheck(self, msg, val):
        return RAWINPUT(msg) == val

    def getLinkWithNamecheck(self, name, inputCheck=True):
        nname, ename, url = self._find_link_by_name(name)
        if not url:
            return None, '(%s)不是有效的成员姓名,请检查你的输入' % name

        if inputCheck:
            s = RAWINPUT("确认要投票给(%s),请再次输入成员姓名:" % nname)
            if s != nname:
                return None, '输入(%s)与预期不符,退出程序' % s
        return url, ''

    def serialCheck(self,s1,s2=None):
        return _serialCheck(s1, s2)

def _serialCheck(s1, s2=None):
    if s2 is None:
        s = s1.split()
        if len(s) == 2 and len(s[0]) == 8 and len(s[1]) == 8:
            s1 = s[0]
            s2 = s[1]
        elif len(s) == 1 and len(s[0]) == 16:
            s1 = s[0][0:8]
            s2 = s[0][8:]
        else:
            return None, None
    r1 = re.match(r'[0-9a-z]{8}', s1)
    r2 = re.match('[0-9a-z]{8}', s2)

    if r1: r1 = r1.group(0)
    if r2: r2 = r2.group(0)
    return r1, r2


def _argparse():
    parser = argparse.ArgumentParser(description="AKB48 2018年世界总选举自助投票程序")
    parser.add_argument('-headless', action='store_true', help='启用浏览器无头模式')

    subparsers = parser.add_subparsers()
    voteParser = subparsers.add_parser('vote', help='投票')
    voteParser.add_argument('-name', type=str, required=True, help='目标成员日语全名，使用空格分隔姓与名，并包括在双引号里，如(-name "大岛 优子")')
    voteGroup = voteParser.add_mutually_exclusive_group(required=True)
    voteGroup.add_argument('-serial', type=str, nargs=2,
                           help='序列码，使用空格分隔序列码前后的两部分，每部分各八位共十六位，如(-serial 12345678 87654321)')
    voteGroup.add_argument('-file', type=str, help='序列码列表文件，每条序列码占用一行，使用空格分隔序列码前后的两部分，每部分各八位共十六位')
    return parser.parse_args()


if __name__ == "__main__":
    arg = _argparse()

    if arg.serial and None in _serialCheck(arg.serial[0], arg.serial[1]):
        ERROR('(%s,%s)错误的序列号格式' % (arg.serial[0], arg.serial[1]))
        sys.exit(0)
    elif arg.file and not os.path.exists(arg.file):
        ERROR('(%s)文件未找到' % arg.file)
        sys.exit(0)

    try:
        bot = VoteBot(arg.headless)
    except Exception as e:
        ERROR(e)
        sys.exit(0)

    bot.initVoteInfo()
    if arg.file:
        INFO(bot.voteFromFile(arg.file, arg.name))
    elif arg.serial:
        INFO(bot.vote(arg.serial[0], arg.serial[1], arg.name))
    bot.close()
