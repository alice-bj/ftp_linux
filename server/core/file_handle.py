# -*- coding:utf-8 -*-
import os
import hashlib
import struct


class FileHandle():
    def __init__(self,max_recv_size,message):
        self.MAX_RECV_SIZE = max_recv_size
        self.message = message

    def readfile(self,filepath):
        """读取文件,得到文件内容的bytes型"""
        with open(filepath,'rb') as f:
            filedata = f.read()
        return filedata

    def getfile_md5(self,filepath):
        """对文件内容md5"""
        return hashlib.md5(self.readfile(filepath)).hexdigest()

    def openfile_tosend(self,filepath,conn,exist_file_size=0):
        """下载时，将文件打开，send(data)"""
        with open(filepath, 'rb') as f:
            f.seek(exist_file_size)
            while True:
                data = f.read(1024)
                if data:
                    conn.send(data)
                else:
                    break

    def recursion_file(self, menu):
        """递归查询用户home/alice目录下的所有文件，算出文件的大小"""
        res = os.listdir(menu)
        for i in res:
            path = '%s/%s' % (menu, i)   # 注意这里,linux 是/  windows 是\
            if os.path.isdir(path):
                self.recursion_file(path)
            elif os.path.isfile(path):
                self.home_bytes_size += os.path.getsize(path)

    def current_home_size(self, home):
        """得到当前用户home/alice目录的大小，字节/M"""
        self.home_bytes_size = 0
        self.recursion_file(home)
        print('字节：', self.home_bytes_size)  # 单位是字节
        home_m_size = round(self.home_bytes_size / 1024 / 1024, 1)
        print('单位M:', home_m_size)  # 单位时 M
        return self.home_bytes_size

    def verification_filemd5(self,conn_obj, file_md5, conn):
        """验证文件内容的MD5值"""
        if self.getfile_md5(conn_obj['filepath']) == file_md5:
            conn.send(self.message['211'])  # 上传成功
        else:
            conn.send(self.message['212'])  # 上传失败

    def write_file(self, f, recv_size, file_size, conn):
        """上传文件时，将文件内容写入到文件中"""
        while recv_size < file_size:
            file_bytes = conn.recv(self.MAX_RECV_SIZE)
            # time.sleep(0.1)
            f.write(file_bytes)
            recv_size += len(file_bytes)
            conn.send(struct.pack('i', recv_size))  # 为了进度条的显示

    def put_situation(self, conn_obj, conn, file_md5, file_size, has_size=0):
        """上传文件的两种情况,是否超出用户配额,之前是否上传过,第一次上传"""
        if conn_obj['home_bytes_size'] + int(file_size - has_size) > conn_obj['quota_bytes']:
            print('超出了用户的配额')
            conn.send(struct.pack('i', 0))
        else:
            conn.send(struct.pack('i', 1))
            if has_size:
                conn.send(struct.pack('i', has_size))
                with open(conn_obj['filepath'], 'ab') as f:
                    f.seek(has_size)
                    self.write_file(f, has_size, file_size, conn)
            else:
                with open(conn_obj['filepath'], 'wb') as f:
                    self.write_file(f, has_size, file_size, conn)
            self.verification_filemd5(conn_obj,file_md5, conn)