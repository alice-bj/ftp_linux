# -*- coding:utf-8 -*-
import os
import socket
import struct
import pickle
import hashlib
import subprocess
import queue
from threading import Thread,Lock
import time

from conf import settings
from core.user_handle import UserHandle
from core.logger import set_logger
from core.file_handle import FileHandle

user_logger = set_logger('user')


class FTPServer():
    MAX_SOCKET_LISTEN = 5
    MAX_RECV_SIZE = 8192
    STATE_FLAG = {'200': '增加目录成功',
                  '201': '目录名已存在',
                  '202': '切换目录成功',
                  '203': '切换目录失败',
                  '204': '切换的目录不在该目录下',
                  '205': '删除成功',
                  '206': '文件夹非空，不能删除',
                  '207': '不是文件,也不是文件夹',
                  '208': '登录成功',
                  '209': '密码不对',
                  '210': '用户不存在',
                  '211': '上传成功',
                  '212': '上传失败'
                  }

    def __init__(self):
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.socket.bind((settings.HOST,settings.PORT))
        self.socket.listen(self.MAX_SOCKET_LISTEN)
        self.q_conn = queue.Queue(settings.MAX_CONCURRENT_COUNT)
        self.homedir_conn = {}
        self.message = self.state_bytes()
        self.file_handle = FileHandle(self.MAX_RECV_SIZE, self.message)

    def state_bytes(self):
        # 将STATE_FLAG的value值转化成 bytes 型
        return {k: bytes(v,'utf-8') for k,v in self.STATE_FLAG.items()}

    def server_accept(self):
        """等待client链接"""
        print('starting...')
        while True:
            conn,client_addr = self.socket.accept()
            print('客户端地址:',client_addr)
            try:
                t = Thread(target=self.server_handle,args=(conn,))
                self.q_conn.put(t)
                t.start()
            except Exception as e:
                print(e)
                conn.close()
                self.q_conn.get()

    def auth(self,conn):
        """处理用户的认证请求
        1.根据username读取accounts.ini文件,password相比,判断用户是否存在
        2.将用户的home,current_dir存在homedir_conn[conn],供后续conn使用
        3.给client返回用户的详细信息
        """
        while True:
            try:
                user_dic = pickle.loads(conn.recv(self.MAX_RECV_SIZE))
                name = user_dic.get('username')
                user_handle = UserHandle(name)
                # 判断用户是否存在 返回列表eg:[('password', '202cb962ac59075b964b07152d234b70'), ('homedir', 'home/alice'), ('quota', '100')]
                user_data = user_handle.judge_user()
                if user_data:
                    if user_data[0][1] == hashlib.md5(user_dic.get('password').encode('utf-8')).hexdigest():  # 密码也相同
                        username = name
                        homedir_path = '%s/%s/%s'%(settings.BASE_DIR,'home',username)
                        self.homedir_conn[conn] = {'username':username,'home':homedir_path,'current_dir':homedir_path}# 第一个表示用户的home目录,第二个表示用户切换的当前目录
                        self.homedir_conn[conn]['quota_bytes'] = int(user_data[2][1]) * 1024 * 1024  # 将用户配额的大小从M 改到字节
                        user_info_dic = {
                            'username': username,
                            'homedir': user_data[1][1],
                            'quota': user_data[2][1]
                        }
                        conn.send(self.message['208']+(';'+str(user_info_dic)).encode('utf-8'))
                        user_logger.info('user: %s 登录成功'%username)
                        return True
                    else:
                        conn.send(self.message['209'])  # 密码不对
                else:
                    conn.send(self.message['210'])  # 用户不存在
            except Exception as e:
                print(e)
                conn.close()
                self.q_conn.get()
                break

    def get(self,conn):
        """从server下载文件到client
        1.判断用户是否输入文件名
        2.判断文件是否存在
        3.接收client发来的文件大小
            3.1.exist_file_size != 0 表示之前已被下载过一部分
                3.1.1.发送文件的header_size header_bytes
                3.1.2.判断exist_file_size是否等于文件的真实大小
                    3.1.2.1.不等，文件以rb模式打开，f.seek(exist_file_size),接着再send(line)
                    3.1.2.2.相等，提示文件大小相等
            3.2.exist_file_size == 0 表示第一次下载
                3.2.1.发送文件的header_size header_bytes
                3.2.2.文件以rb模式打开，send(line)
        """
        if len(self.cmds) > 1:
            filename = self.cmds[1]
            filepath = os.path.join(self.homedir_conn[conn]['current_dir'],filename)
            if os.path.isfile(filepath):
                exist_file_size = struct.unpack('i', conn.recv(4))[0]
                self.homedir_conn[conn]['filepath']=filepath
                header_dic = {
                    'filename': filename,
                    'file_md5': self.file_handle.getfile_md5(filepath),
                    'file_size': os.path.getsize(filepath)
                }
                header_bytes = pickle.dumps(header_dic)
                conn.send(struct.pack('i', len(header_bytes)))
                conn.send(header_bytes)
                if exist_file_size:  # 表示之前被下载过 一部分
                    if exist_file_size != os.path.getsize(filepath):
                        self.file_handle.openfile_tosend(self.homedir_conn[conn]['filepath'], conn, exist_file_size)
                    else:
                        print('断点和文件本身大小一样')
                else:  # 文件第一次下载
                    self.file_handle.openfile_tosend(self.homedir_conn[conn]['filepath'], conn)
                    user_logger.info('user: %s,下载文件: %s' % (self.homedir_conn[conn]['username'],filename))
            else:  # 这里无论收到文件大小或者0 都不做处理，因为server根本不存在该文件了返回0
                print('当前目录下文件不存在')
                conn.send(struct.pack('i',0))
        else:
            print('用户没有输入文件名')

    def put(self,conn):
        """从client上传文件到server当前工作目录下
        1.判断用户是否输入文件名
        2.从client得知，待传的文件是否存在
            2.1.current_home_size(),得知用户home/alice大小，self.home_bytes_size
            2.2.接收文件header filename file_size file_md5
            2.3.上传文件在当前目录下,已经存在，断点续传：
                2.3.1.算出文件已经有的大小，has_size
                    2.3.1.1.发现 has_size == file_size,发送0，告诉client,文件已经存在
                    2.3.1.2.has_size != file_size,接着继续传，
                        2.3.1.2.1.self.home_bytes_size + int(file_size - has_size) > self.quota_bytes
                            算出接着要上传的大小是否超出了配额，超出配额就提示。
                        2.3.1.2.2.没有超出配额，就send(has_size),文件以ab模式打开，f.seek(has_size),f.write()
                            发送每次的has_size,同步，为了client显示进度条
                        2.3.1.2.3.验证文件内容的md5,是否上传成功！
            2.4.上传文件在当前目录下，不存在，第一次上传：
                2.4.1.self.home_bytes_size + int(file_size) > self.quota_bytes:
                    验证上传的文件是否超出了用户配额，超出就提示
                2.4.2.文件以wb模式打开，f.write(),发送每次得recv_size,同步，为了client显示进度条
                2.4.3.验证文件内容的md5,是否上传成功！
        """
        if len(self.cmds) > 1:
            state_size = struct.unpack('i', conn.recv(4))[0]
            if state_size:
                # 算出了home下已被占用的大小self.home_bytes_size
                self.homedir_conn[conn]['home_bytes_size'] = self.file_handle.current_home_size(self.homedir_conn[conn]['home'])
                header_bytes = conn.recv(struct.unpack('i', conn.recv(4))[0])
                header_dic = pickle.loads(header_bytes)
                print(header_dic)
                filename = header_dic.get('filename')
                file_size = header_dic.get('file_size')
                file_md5 = header_dic.get('file_md5')

                upload_filepath = os.path.join(self.homedir_conn[conn]['current_dir'], filename)
                self.homedir_conn[conn]['filepath'] = upload_filepath
                if os.path.exists(upload_filepath):  # 文件已经存在
                    conn.send(struct.pack('i', 1))
                    has_size = os.path.getsize(upload_filepath)
                    if has_size == file_size:
                        print('文件已经存在')
                        conn.send(struct.pack('i', 0))
                    else:  # 上次没有传完 接着继续传
                        conn.send(struct.pack('i', 1))
                        self.file_handle.put_situation(self.homedir_conn[conn], conn, file_md5, file_size, has_size)
                else:  # 第一次 上传
                    conn.send(struct.pack('i', 0))
                    self.file_handle.put_situation(self.homedir_conn[conn], conn, file_md5, file_size)
                    user_logger.info('user: %s,上传文件: %s' % (self.homedir_conn[conn]['username'], filename))
            else:
                print('待传的文件不存在')
        else:
            print('用户没有输入文件名')

    def ls(self,conn):
        """查询当前工作目录下,先返回文件列表的大小,在返回查询的结果"""
        os.chdir(self.homedir_conn[conn]['current_dir'])  # 切换到conn 当前目录
        if len(self.cmds) > 1:
            file_name = self.cmds[1]
            file_path = '%s/%s' % (self.homedir_conn[conn]['current_dir'], file_name)
            if os.path.isdir(file_path):
                subpro_obj = subprocess.Popen('ls '+ file_name, shell=True,
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE)
            else:
                subpro_obj = subprocess.Popen('ls', shell=True,  # 这里如果没有输入正确的目录名 就默认显示当前目录
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE)
        else:
            subpro_obj = subprocess.Popen('ls', shell=True,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
        stdout = subpro_obj.stdout.read()
        stderr = subpro_obj.stderr.read()

        conn.send(struct.pack('i', len(stdout + stderr)))
        conn.send(stdout)
        conn.send(stderr)

    def mkdir(self,conn):
        """在当前目录下,增加目录"""
        if len(self.cmds) > 1:
            mkdir_path = os.path.join(self.homedir_conn[conn]['current_dir'],self.cmds[1])
            if not os.path.exists(mkdir_path):
                os.mkdir(mkdir_path)
                conn.send(self.message['200'] + (',目录名为: %s'%self.cmds[1]).encode('utf-8'))  # 增加目录成功
            else:
                conn.send(self.message['201'])  # 目录名已存在
        else:
            print('用户没有输入目录名')

    def cd(self,conn):
        """切换目录
        1.查看是否是目录名
        2.拿到当前目录,拿到目标目录,
        3.判断conn的home是否在目标目录内,防止用户越过自己的home目录 eg: ../../....
        4.send(切换的状态)
        """
        if len(self.cmds) > 1:
            lock = Lock()
            lock.acquire()  # 这里要上把锁 在修改 os.chdir(dir_path)
            dir_path = os.path.join(self.homedir_conn[conn]['current_dir'], self.cmds[1])
            if os.path.isdir(dir_path):
                previous_path = self.homedir_conn[conn]['current_dir']
                os.chdir(dir_path)
                target_dir = os.getcwd()  # 写成这样为了防止 ../  否则会有ftp_2\server\home\lily\test5\../../ 这样的情况存在

                if self.homedir_conn[conn]['home'] in target_dir:
                    self.homedir_conn[conn]['current_dir'] = target_dir
                    conn.send(self.message['202'])  # 切换目录成功
                else:
                    os.chdir(previous_path)
                    conn.send(self.message['203'])  # 切换目录失败
            else:
                conn.send(self.message['204'])  # 切换的目录不在该目录下
            lock.release()
        else:
            print('没有传入切换的目录名')

    def rm(self,conn):
        """删除指定的文件,或者空文件夹"""
        if len(self.cmds) > 1:
            file_name = self.cmds[1]
            file_path = '%s/%s'%(self.homedir_conn[conn]['current_dir'],file_name)

            if os.path.isfile(file_path):
                os.remove(file_path)
                conn.send(self.message['205'])  # 删除成功
            elif os.path.isdir(file_path):      # 删除空目录
                if not len(os.listdir(file_path)):
                    os.removedirs(file_path)
                    conn.send(self.message['205'])  # 删除成功
                else:
                    conn.send(self.message['206'])  # 文件夹非空,不能删除
            else:
                conn.send(self.message['207'])  # 不是文件,也不是文件夹
        else:
            print('没有输入要删除的文件')

    def server_handle(self,conn):
        """处理与用户的交互指令
        1.下载 get a.txt
        2.上传 put a.txt
        3.查询当前目录下的文件列表 ls
        4.当前目录下增加目录 mkdir test
        5.切换目录 cd test
        6.删除文件或空文件夹 rm xxx
        """
        if self.auth(conn):
            print('用户登录成功')
            while True:
                try:  # try ...except 适合windows  client 断开
                    user_input = conn.recv(self.MAX_RECV_SIZE).decode('utf-8')
                    if not user_input:
                        conn.close()
                        self.q_conn.get()
                        break  # 这里适合 linux client 断开
                    self.cmds = user_input.split()
                    if hasattr(self,self.cmds[0]):
                        getattr(self,self.cmds[0])(conn)
                    else:
                        print('请用户重复输入')
                except Exception:
                    conn.close()
                    self.q_conn.get()
                    break

    def run(self):
        self.server_accept()

    def __del__(self):
        self.socket.close()