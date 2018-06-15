import argparse
import os
import pickle
import re
import signal
import sys
import threading
import time
from argparse import ArgumentParser
from multiprocessing import cpu_count, Pool, JoinableQueue
from random import randint
import itertools

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from vote import INFO, FILE, DEBUG, ERROR, RAWINPUT, PRINT, pt, ft
from functools import reduce

def flatMap(func, iterable):
   return map(func,itertools.chain.from_iterable(iterable))

class State():
    def __init__(self, s1, s2, name, url, msg):
        self.s1 = s1
        self.s2 = s2
        self.name = name
        self.url = url
        self.msg = msg

    def __str__(self):
        return "%s, %s, %s, %s, %s" % (self.s1, self.s2, self.name, self.url, str(self.msg)[1:-1])


class VoteBot:
    from selenium import webdriver
    def __init__(self, headless=False,noimages=False):
        self.driver = self.getBrowser(headless,noimages)
        INFO('浏览器初始化完成'
             + ('(headless)'if headless else '')
             + ('(noimages)'if noimages else ''))

    def initVoteInfo(self):
        fp = os.path.abspath('numberList.pickle');
        self.team, self.number = pt.load(fp)
        if not self.number or not self.team:
            self.team = self.getTeamList()
            self.number = self.getNumberList(self.team)
            pt.save(fp, (self.team, self.number))
        else:
            self.get('https://akb48-sousenkyo.jp/akb/search/results?t_id=1', '.wrap h1')
        INFO("成员列表获取成功")

    def getTeamList(self):
        self.get('https://akb48-sousenkyo.jp/akb/search/teams', '.wrap h1')
        a = self.find_by_css_s('dd a')
        return [(dd.text,dd.get_attribute('href')) for dd in a]

    def getNumberInfo(self, link):
        self.get(link, '.wrap h1')
        list = self.find_by_css_s('dd a')
        return [(dd.text, dd.get_attribute('href')) for dd in list]

    def getNumberList(self,teamlist):
        return reduce(lambda d1,d2:dict(d1,**d2),
                      map(lambda ninfo:{ninfo[0][0]: (ninfo[0][0], ninfo[0][1], ninfo[1])},
                          flatMap(lambda ninfo:(ninfo[0].split('／'),ninfo[1]) ,
                                  map(lambda tinfo:self.getNumberInfo(tinfo[1]),teamlist))))

    def getBrowser(self, headless=False,noimages=False):
        options = webdriver.ChromeOptions()
        # options.add_argument('test-type')

        if headless:
            options.add_argument('headless')

        if noimages:
            options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})

        options.add_argument('lang=zh_CN.UTF-8')
        options.add_argument(
            'user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36"')
        options.add_experimental_option("excludeSwitches", ["ignore-certificate-errors"])
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

    def voteOneByOne(self, name, out=False):
        url, msg = self.getLinkWithNamecheck(name, False)
        if not url: return [msg]
        id = 0
        while True:
            s = RAWINPUT('请输入序列号(输入exit退出):')
            if s == 'exit': return '退出脚本'
            s1, s2 = self.serialCheck(s)
            if s1 and s2:
                state = self.voteNoSafeCheck(s1, s2, name, url)
            else:
                state = State(s.strip(), '', name, url, ('投票エラー', '投票码格式错误'))
            INFO('%d, ' % id + str(state))
            if not out:
                FILE('%d, ' % id + str(state))
            id += 1

    def voteFromFile(self, filePath, name, delay):
        url, msg = self.getLinkWithNamecheck(name)
        if not url: return msg
        INFO('验证成功，倒计时13s后开始投票给(%s),如果有任何疑问，您可以使用(ctrl + c)主动退出程序' % name)
        countdown(13)
        INFO('投票开始(%s)' % name)
        return self.voteBatchNoSafeCheck(filePath, url, name, delay)

    def readline(self,filePath,hint: int = -1):
        with open(filePath) as f:
            while True:
                lines = f.readlines(hint)
                if not lines: break
                for line in lines:
                    yield line


    def voteBatchNoSafeCheck(self, filePath, url, name, delay):
        id = 0
        for serial in self.readline(filePath,100):
            if not serial:break
            serial = serial.strip()
            if len(serial) > 0:
                s1, s2 = self.serialCheck(serial)
                if s1 and s2:
                    state = self.voteNoSafeCheck(s1, s2, name, url)
                else:
                    state = State(serial.strip(), '', name, url, ('投票エラー', '投票码格式错误'))
                INFO("%s, %d, " % (threading.current_thread().name, id) + str(state))
                FILE("%d, " % id + str(state), filePath)
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

    def get(self, url, css, wtime=3):
        t = 0
        while True:
            self.driver.get(url)
            try:
                WebDriverWait(self.driver, wtime).until(EC.visibility_of(self.find_by_css(css)))
            except Exception as e:
                ERROR(e)
                if self.driver.current_url == "https://akb48-sousenkyo.jp/akb/top/error?error=":
                    self.driver.get('https://akb48-sousenkyo.jp/akb/search/results?t_id=1')
                else:
                    if t >= 5:
                        raise TimeoutError("五次尝试后并不能访问正确的网络地址，脚本异常退出")
                    else:
                        t += 1
            else:
                break

    def find_link_by_name(self, name):
        if name in self.number:
            return self.number[name]
        else:
            return None, None, None

    def close(self):
        if self.driver:
            self.driver.close()


    def serialCheck(self, s1, s2=None):
        return _serialCheck(s1, s2)


def countdown(lineLength, ds=1, fs='=', fs2=['-', '\\', '|', '/'], bs=''):
    lineTmpla = '{:%s<%s} {} {:<2}' % (bs, lineLength)
    for s in range(lineLength):
        j = lineLength - s
        print('\r' + lineTmpla.format(fs * j, fs2[j % (len(fs2))], j), end='')
        time.sleep(ds)
    print('\r' + '  ' * lineLength + '\r', end='')


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
    parser.add_argument('-noimages', action='store_true', help='启用浏览器无图模式')
    parser.set_defaults(func=lambda x: PRINT('use (-h)'))

    subparsers = parser.add_subparsers()
    voteParser = subparsers.add_parser('vote', help='投票')
    voteParser.set_defaults(func=lambda x: PRINT('use (vote -h)'))
    voteSubParser = voteParser.add_subparsers()
    oneVoteParser = voteSubParser.add_parser('one', help='投入一票')
    oneVoteParser.add_argument('-serial', type=str, nargs=2, required=True,
                               help='序列码，使用空格分隔序列码前后的两部分，每部分各八位共十六位，如(-serial 12345678 87654321)')
    oneVoteParser.add_argument('-name', type=str, required=True, help='目标成员日语全名，使用空格分隔姓与名，并包括在双引号里，如(-name "大岛 优子")')
    oneVoteParser.set_defaults(func=oneVote)

    batchVoteParser = voteSubParser.add_parser('batch', help='读取投票码文件批量投票')
    batchVoteParser.add_argument('-name', type=str, required=True, help='目标成员日语全名，使用空格分隔姓与名，并包括在双引号里，如(-name "大岛 优子")')
    batchVoteParser.add_argument('-file', type=str, required=True, help='序列码列表文件，每条序列码占用一行，使用空格分隔序列码前后的两部分，每部分各八位共十六位')
    batchVoteParser.add_argument('-delay', type=int, nargs=3, default=[1000, 500, 10],
                                 help='主动延迟,如（2000 500 10）表示投出十票后暂停两秒，每票投出后主动暂停0.5秒')
    batchVoteParser.add_argument('-pnum', type=int, nargs=2, default=[1, 1024],
                                 help='运行的进程数，最大值为cpu核心数的两倍，多进程时分隔的文件大小')
    batchVoteParser.set_defaults(func=batchVoteMultiProcessing)

    stepVoteParser = voteSubParser.add_parser('step', help='根据提示一步步接续投票')
    stepVoteParser.add_argument('-name', type=str, required=True, help='目标成员日语全名，使用空格分隔姓与名，并包括在双引号里，如(-name "大岛 优子")')
    stepVoteParser.add_argument('-out', action='store_true', help='投票信息是否记录到文件')
    stepVoteParser.set_defaults(func=stepVote)

    return parser.parse_args()


def stepVote(arg):
    bot = botInit(arg)
    INFO(bot.voteOneByOne(arg.name, arg.out))
    bot.close()


def oneVote(arg):
    if arg.serial and None in _serialCheck(arg.serial[0], arg.serial[1]):
        ERROR('(%s,%s)错误的序列号格式' % (arg.serial[0], arg.serial[1]))
    else:
        bot = botInit(arg)
        INFO(bot.vote(arg.serial[0], arg.serial[1], arg.name))
        bot.close()


def func(args, fname):
    bot = botInit(args)
    nname, ename, url = bot.find_link_by_name(args.name)
    if url:
        threading.current_thread().setName(os.path.basename(fname))
        INFO(bot.voteBatchNoSafeCheck(fname, url, args.name, args.delay))
    else:
        INFO('(%s)不是有效的成员姓名,请检查你的输入' % name)
    bot.close()


def batchVoteMultiProcessing(args):
    if args.file and not os.path.exists(args.file):
        ERROR('(%s)文件未找到' % args.file)
        return

    s = RAWINPUT("确认要投票给(%s),请再次输入成员姓名:" % args.name)
    if s != args.name:
        ERROR('输入(%s)与预期不符,退出程序' % s)
        return

    bot = botInit(args)
    INFO("验证成员姓名(%s)合法性" % args.name)
    nname, ename, url = bot.find_link_by_name(args.name)
    if not url:
        ERROR('(%s)不是有效的成员姓名,请检查你的输入' % args.name)
        return

    INFO('验证成功，倒计时13s后开始投票给(%s),如果有任何疑问，您可以使用(ctrl + c)主动退出程序' % args.name)

    def ext(signum, frame):
        print('')
        ERROR('您使用(ctrl + c)主动退出了程序')
        exit(0)

    signal.signal(signal.SIGINT, ext)
    signal.signal(signal.SIGTERM, ext)

    countdown(13)
    INFO('投票开始(%s)' % args.name)

    if args.pnum[0] <= 1:
        INFO(bot.voteBatchNoSafeCheck(args.file, url, args.name, args.delay))
        bot.close()
    else:
        bot.close()
        dirname = '%s-%s' % (args.name, args.file)
        tempFileCount = ft.split(args.file, dirname,
                                 args.pnum[1] if args.pnum[1] > 0 else 1024)
        p = Pool(cpu_count() * 2 if (args.pnum[0] > cpu_count() * 2) else args.pnum[0])
        for partnum in range(tempFileCount):
            fname = os.path.join(dirname, 'part%04d' % partnum)
            p.apply_async(func, (args, fname))
        p.close()
        p.join()
        fname = os.path.join(dirname, args.file + ".log")
        INFO('合并文件到(%s)'%fname)
        ft.merge(dirname, fname)


def botInit(args):
    try:
        bot = VoteBot(args.headless,args.noimages)
        bot.initVoteInfo()
        return bot
    except Exception as e:
        ERROR(e)
        sys.exit(0)

if __name__ == "__main__":
    args = _argparse()
    DEBUG(args)
    args.func(args)
