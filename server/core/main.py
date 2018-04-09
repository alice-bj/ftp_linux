# -*- coding:utf-8 -*-
from core.user_handle import UserHandle
from core.server import FTPServer


class Manager():
    def __init__(self):
        pass

    def start_ftp(self):
        """启动ftp_server端"""
        server = FTPServer()
        server.run()

    def create_user(self):
        """创建用户"""
        username = input('username>>>:').strip()
        UserHandle(username).add_user()

    def quit_func(self):
        quit('bye bye ...')

    def run(self):
        msg = '''
        1.启动ftp服务器
        2.创建用户
        3.退出
        '''
        msg_dic = {'1': 'start_ftp', '2': 'create_user', '3': 'quit_func'}
        while True:
            print(msg)
            num = input('num>>>:').strip()
            if num in msg_dic:
                getattr(self,msg_dic[num])()
            else:
                print('\033[1;31m请重新选择\033[0m')