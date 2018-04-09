# -*- coding:utf-8 -*-
import sys
import optparse

def fun():
    print('hello world')
    print(sys.argv)

fun()

"""
终端执行：
    python test_argument.py alice lily
        hello world
        ['test_argument.py', 'alice', 'lily'] 
"""

def opt():
    parser = optparse.OptionParser()
    parser.add_option("-s", "--server", dest="server", help="ftp server ip_addr")
    parser.add_option("-o", "--port", type="int", dest="port", help="ftp server port")
    parser.add_option("-u", "--username", dest="username", help="username info")
    parser.add_option("-p", "--password", dest="password", help="password info")

    options, args = parser.parse_args()
    print(options,args)
    print(options.server,options.port,options.username,options.password)

opt()

"""
终端执行：
    python test_argument.py -s 127.0.0.1 -o 8080 -u alice -p 123
        {'server': '127.0.0.1', 'port': 8080, 'username': 'alice', 'password': '123'} []
        127.0.0.1 8080 alice 123
        
    python test_argument.py -help
        Usage: test_argument.py [options]
        Options:
          -h, --help            show this help message and exit
          -s SERVER, --server=SERVER
                                ftp server ip_addr
          -o PORT, --port=PORT  ftp server port
          -u USERNAME, --username=USERNAME
                                username info
          -p PASSWORD, --password=PASSWORD
                                password info
"""

"""
参考：https://www.cnblogs.com/captain_jack/archive/2011/01/11/1933366.html
     https://docs.python.org/3/library/optparse.html
     http://www.jb51.net/article/59296.htm
"""

