运行环境如下 
Python3.6+版本
https://www.python.org/downloads/
selenium模块
pip install selenium
Chrome浏览器
https://www.google.cn/chrome/
浏览器对应版本的chromedriver,最新版本2.39
http://npm.taobao.org/mirrors/chromedriver/
添加path环境变量指向chromedriver文件所在目录，或者复制chromedriver到C:\Windows


打开终端(cmd)建议使用管理员权限运行，或者确保你在当前目录有相应权限
切换到脚本所在目录，如 
cd D:\
单票验证键入命令，如
python vote.py vote one  -n "田中 美久" -s 12345678 87654321

首次运行时由于要收集成员列表信息所以较慢，之后会重复利用已经收集过的内容。
得到反馈信息
[2018-06-06 16:33:00] [INFO] 浏览器初始化完成
[2018-06-06 16:33:05] [INFO] 成功获取成员列表成功
[2018-06-06 16:33:08] [INFO] '12345678', '87654321', '田中 美久', 'https://akb48-sousenkyo.jp/akb/vote?id=231', '投票エ ラー', '入力されたシリアルナンバーは無効であるか既に投票済みです。確認の上、再入力してください。
证明此票为废票

根据提示一张张手动验证
键入命令，如
python vote.py vote step -n "田中 美久"
得到反馈信息
[2018-06-08 00:07:04] [INFO] 浏览器初始化完成
[2018-06-08 00:07:08] [INFO] 成功获取成员列表成功
请输入序列号(输入exit退出):
输入投票码，将验证一票之后重复显示
请输入序列号(输入exit退出):
如果想退出根据提示键入exit


批量验证
准备文本文件vote.txt,内容如下,每一行包括一个序列号 可以用一个空格分隔序列号的前后两部分
safsdfas dfghdcxz
safsdfasdfghdcxz
66zvmux9 p5kh8r9z
fuzvmux9 ptkh8r9
单进程情况下键入命令，如
python vote.py -headless  vote batch -n "田中 美久"  -f vote.txt
得到反馈信息
[2018-06-06 16:36:54] [INFO] 浏览器初始化完成
[2018-06-06 16:36:57] [INFO] 成功获取成员列表成功
确认要投票给(田中 美久),请再次输入成员姓名:
输入成员姓名二次确认,你可以输入任意错误的信息来退出脚本
得到反馈信息
[2018-06-06 16:37:18] [INFO] 验证成功，倒计时13s后开始投票给(田中 美久),如果有任何疑问，您可以使用(ctrl + c)主动退出脚本
等待13秒后脚本自动启动，漏投的序列号将自动投入给你所选择的用户，倒计时开始后你可以使用(ctrl + c)强制退出，但已投出的选票将无法反悔，为了保险起见只建议你用此脚本验票。造成的任何损失请自行承担
13秒后验票开始，下方序列号皆为虚构。
[2018-06-06 16:37:42] [INFO] 1, 'safsdfas', 'dfghdcxz', '田中 美久', 'https://akb48-sousenkyo.jp/akb/vote?id=231', '投票エラー', '入力されたシリアルナンバーは無効であるか既 に投票済みです。確認の上、再入力してください。'
[2018-06-06 16:37:45] [INFO] 2, '66zvmux9', 'p5kh8r9z', '田中 美久', 'https://akb48-sousenkyo.jp/akb/vote?id=231', '投票エラー', '入力したシリアルナンバーは既に投票済みです 。', '投票日時:2018/05/30 08:22:08'
[2018-06-06 16:37:45] [INFO] 3, '66zvmux9 p5khtr9', '', '田中 美久', 'https://akb48-sousenkyo.jp/akb/vote?id=231', '投票エラー', '注册码格式错误'
在当前目录将会产生文件名类似vote-000000.txt的文本文件记录结果,你可以导入Excel进行统计分析，
使用python vote.py -h 获得更多帮助信息

多进程情况下键入命令，如
python vote.py -headless  vote batch -n "田中 美久"  -f vote.txt -pnum 12 80
pnum选项的首个参数参数指定了进程池的深度，第二个参数是序列号文件被分割的大小。
headless选项让浏览器进入无头模式，您将不会看到跳出的浏览器。

项目地址
https://github.com/Sainka/2018vote