# -*- coding:utf-8 -*-
import configparser
import hashlib
import os

from conf import settings
from core.logger import set_logger

manager_logger = set_logger('manager')


class UserHandle():
    def __init__(self,username):
        self.username = username
        self.config = configparser.ConfigParser()
        self.config.read(settings.ACCOUNTS_FILE)

    @property
    def password(self):
        """生成用户的 默认密码 123"""
        return hashlib.md5('123'.encode('utf-8')).hexdigest()

    @property
    def quota(self):
        """生成每个用户的 磁盘配额"""
        quota = input('quota>>>:').strip()
        if quota.isdigit():
            return quota
        else:
            exit('\033[1;31m磁盘配额须是整数\033[0m')

    def add_user(self):
        """创建用户,存到accounts.ini"""
        if not self.config.has_section(self.username):
            print('creating username is : ', self.username)
            self.config.add_section(self.username)
            self.config.set(self.username,'password',self.password)
            self.config.set(self.username,'homedir','home/'+self.username)
            self.config.set(self.username,'quota',self.quota)
            with open(settings.ACCOUNTS_FILE,'w') as f:
                self.config.write(f)
            os.mkdir(os.path.join(settings.BASE_DIR, 'home', self.username))   # 创建用户的home文件夹
            print('\033[1;32m创建用户成功\033[0m')
            manager_logger.info('添加用户: %s'%(self.username))
        else:
            print('\033[1;31m用户已存在\033[0m')

    def judge_user(self):
        """判断用户是否存在"""
        if self.config.has_section(self.username):
            return self.config.items(self.username)