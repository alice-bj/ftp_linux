# -*- coding:utf-8 -*-
import os
size = 0
def recursion_file(menu):
    res = os.listdir(menu)
    print(res)
    for i in res:
        path = '%s\%s'%(menu,i)
        if os.path.isdir(path):
            recursion_file(path)
        elif os.path.isfile(path):
            global size
            size += os.path.getsize(path)
            print(size)


path = '%s\%s\%s'%(os.getcwd(),'home','alice')
# print(path)
# recursion_file(path)
# print(size)   # 单位时字节
# print(round(size/1024/1024,1)) # 单位时 M

# video_size = os.path.getsize('%s\%s'%(path,'com.mp4'))
# print(video_size)
# print(round(video_size/1024/1024,1)) # 单位时 M

# os.remove('%s\%s'%(path,'test2')) # 删文件

# os.removedirs('%s\%s'%(path,'test5')) # 删空文件夹
print(path)
path1 = '%s\%s'%(path,'test5')
# res = os.path.getsize(path1)
# print(path1)
# print(res)
print(os.listdir(path1))