#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : scorems
# filename : views
# author : ly_13
# date : 2022/10/13
import os
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from tkinter import StringVar, Label, Entry, W, E, Button, messagebox, ttk, Tk, BROWSE
from tkinter.ttk import Frame

from windnd import hook_dropfiles

from cli import FLYCliSer
from models import config

columns = {
    'name': '应用名称',
    'api': 'Api Token',
}

drop = False


def throttle(func):
    last_time = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal last_time

        current_time = time.time()
        if not last_time or (current_time - last_time > 0.5):  # 设置每秒最多执行一次
            result = func(*args, **kwargs)
            last_time = current_time

            return result
        else:
            return None

    return wrapper


class AddConfig(object):
    def __init__(self, name='', api='', is_edit=False):
        self.is_edit = is_edit
        self.root = Tk()
        self.root.geometry('%dx%d' % (450, 130))
        self.name = StringVar(self.root, value=name)
        self.api = StringVar(self.root, value=api)
        self.show()

    def check(self):
        data = {
            'name': self.name.get().strip(),
            'api': self.api.get().strip(),
        }
        if data['name'] and data['api']:
            return data
        return {}

    def click(self):
        data = self.check()
        if data:
            if not self.is_edit:
                res = config.get(data['name'])
                if res:
                    messagebox.showinfo(title='结果', message="已存在应用配置！")
                    return
            config.add(data['name'], data['api'])
            if self.is_edit:
                messagebox.showinfo(title='结果', message="配置信息更新成功！")
            else:
                messagebox.showinfo(title='结果', message="配置信息添加成功！")
        else:
            messagebox.showinfo(title='提示', message="输入有误，请检查")

    def show(self):

        index = 0
        for key, label in columns.items():
            print(key, label, getattr(self, key))
            Label(self.root, text=f'{label}: ').grid(row=index, stick=W, pady=10)
            Entry(self.root, textvariable=getattr(self, key), width=60).grid(row=index, column=1, stick=E)
            index += 1

        Button(self.root, text='保存配置', command=self.click).grid(row=7, column=1, stick=E, pady=10)
        self.root.mainloop()


class ListFrame(Frame):

    def __init__(self, master=None):
        super().__init__(master)
        self.button_refresh = None
        self.ysb = None
        self.tree = None
        self.button_add = None
        self.button_edit = None
        self.button_delete = None
        self.uploading = 0

    def pack_forget(self) -> None:
        if self.tree:
            self.tree.destroy()
        if self.ysb:
            self.ysb.destroy()
        if self.button_add:
            self.button_add.destroy()
        if self.button_edit:
            self.button_edit.destroy()
        if self.button_delete:
            self.button_delete.destroy()
        if self.button_refresh:
            self.button_refresh.destroy()
        super().pack_forget()

    def format_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        index = 1
        for key, val in config.result.items():
            self.tree.insert("", index, values=[key, val])
            index += 1

    def pack(self, *args, **kwargs):
        super().pack(*args, **kwargs)
        self.tree = ttk.Treeview(self, show="headings", columns=list(columns.keys()), selectmode=BROWSE, padding=5)
        self.tree.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.tree['height'] = 20
        # xsb = Scrollbar(self, orient="horizontal", command=self.tree.xview())  # x滚动条
        # self.ysb = Scrollbar(self, orient="vertical", command=self.tree.yview())  # y滚动条
        # self.tree.configure(yscrollcommand=self.ysb.set, xscrollcommand=xsb.set)  # y滚动条关联
        # self.ysb.pack(side="right", fill="y")
        for column, label in columns.items():
            width = 600
            if column == 'name':
                width = 200
            self.tree.column(column, width=width)
            self.tree.heading(column, text=label)

        self.format_data()

        self.button_add = Button(text="添加", command=AddConfig, padx=5, pady=5)
        self.button_add.pack()
        self.button_refresh = Button(text="刷新", command=self.format_data, padx=5, pady=5)
        self.button_refresh.pack()
        self.button_edit = Button(text="选中编辑", command=self.edit_config, padx=5, pady=5)
        self.button_edit.pack()
        self.button_delete = Button(text="选中删除", command=self.delete_node, padx=5, pady=5)
        self.button_delete.pack()
        self.button_add.place(relx=0.37, rely=0.9)
        self.button_refresh.place(relx=0.43, rely=0.9)
        self.button_edit.place(relx=0.5, rely=0.9)
        self.button_delete.place(relx=0.6, rely=0.9)

        self.tree.bind("<Double-Button-1>", self.edit_config)

        self.tree.pack()

    def edit_config(self, *args, **kwargs):
        item = self.tree.focus()  # 获取当前选中项
        values = self.tree.item(item)['values']  # 获取该项的值列表
        AddConfig(values[0], values[1], True)

    def delete_node(self):
        # 获取选中的节点
        item = self.tree.focus()
        values = self.tree.item(item)['values']  # 获取该项的值列表
        if item != "":
            # 从Treeview中移除该节点及其子节点
            self.tree.delete(item)
            config.delete(values[0])


class UploadFrame(Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.tree = None
        self.button = None
        self.button_delete = None
        self.button_clean = None
        self.count = 0
        self.uploading = 0
        self.result = {}

    def pack_forget(self) -> None:
        super().pack_forget()
        if self.tree:
            self.tree.destroy()
        if self.button:
            self.button.destroy()
        if self.button_delete:
            self.button_delete.destroy()
        if self.button_clean:
            self.button_clean.destroy()

    def pack(self, *args, **kwargs):
        super().pack(*args, **kwargs)

        # 树状标签
        columns = ("idx", "name", "file_path", "status")
        self.tree = ttk.Treeview(self, show="headings", columns=columns, selectmode=BROWSE, padding=5)
        self.tree['height'] = 20
        self.tree.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.tree.column("idx", anchor="w", width=50)  # 设置表格文字靠左
        self.tree.column("name", anchor="w", width=100)
        self.tree.column("file_path", anchor="w", width=400)
        self.tree.column("status", anchor="w", width=250)

        self.tree.heading("idx", text="序号")  # 设置表格头部标题
        self.tree.heading("name", text="匹配配置名称")
        self.tree.heading("file_path", text="文件地址")
        self.tree.heading("status", text="状态")
        self.tree.bind("<Double-Button-1>", self.open_url)
        global drop
        if not drop:
            hook_dropfiles(self, func=lambda paths: self.dragged_files(paths))
            drop = True
        else:
            self.format_data()
        self.tree.pack()
        self.button = Button(text="批量上传", command=self.upload, padx=5, pady=5)
        self.button.pack()
        self.button_delete = Button(text="选中删除", command=self.delete_node, padx=5, pady=5)
        self.button_delete.pack()
        self.button_clean = Button(text="清空", command=self.clean, padx=5, pady=5)
        self.button_clean.pack()
        self.button.place(relx=0.6, rely=0.9)
        self.button_clean.place(relx=0.5, rely=0.9)
        self.button_delete.place(relx=0.4, rely=0.9)

    def open_url(self, *args, **kwargs):
        item = self.tree.focus()  # 获取当前选中项
        values = self.tree.item(item)['values']  # 获取该项的值列表
        urlx = values[3]
        url = urlx.split('上传成功，下载地址：')[-1]
        if url:
            webbrowser.open(url)

    def get_config_name(self, file_name: str):
        for name, token in config.result.items():
            if file_name.startswith(name):
                return name, token
        return None, None

    def dragged_files(self, files):
        for file_path in files:
            file_path = file_path.decode('gbk')
            file_name = os.path.basename(file_path)
            # name = ".".join(os.path.basename(file_path).split('.')[:-1])
            name, token = self.get_config_name(file_name)
            status = "可上传"
            if not token:
                name = ""
                status = "不可上传"

            inster_value = [name, file_path, status]
            self.result[name] = inster_value
            # files_show.insert('', index=self.count, values=inster_value)
            self.format_data()

    @throttle
    def format_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        index = 1
        for key, item in self.result.items():
            self.tree.insert("", index, values=[index, *item])
            index += 1

    def upload_task(self, filepath, token, values):
        if os.path.isfile(filepath) and filepath.split('.')[-1].lower() in ['ipa', 'apk']:
            self.uploading += 1
            fly_obj = FLYCliSer("https://app.hehejoy.cn/", token, self.progress_callback, values)
            self.result[fly_obj.values[1]][2] = f"应用分析中..."
            self.format_data()
            download_url = fly_obj.upload_app(filepath, None, None, None)
            self.result[fly_obj.values[1]][2] = f"上传成功，下载地址：{download_url}"
            self.format_data()
            self.uploading -= 1

    def upload(self):
        if self.uploading != 0:
            return
        pools = ThreadPoolExecutor(1)
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']  # 获取该项的值列表
            filepath = values[2]
            name, token = self.get_config_name(os.path.basename(filepath))
            if not name:
                continue
            pools.submit(self.upload_task, filepath, token, values)
            # if os.path.isfile(filepath) and filepath.split('.')[-1].lower() in ['ipa', 'apk']:
            #     fly_obj = FLYCliSer("https://app.hehejoy.cn/", token, self.progress_callback, values)
            #     fly_obj.upload_app(filepath, None, None, None)
            print(name, filepath, token)
        # pools.shutdown(wait=True)

    def progress_callback(self, fly_obj, offset, total_size):
        def progress_callback(upload_size, now_part_size):
            percent = (offset + upload_size) / total_size  # 接收的比例
            # print(fly_obj.values)
            # print(11, self.result[fly_obj.values[1]], fly_obj.values)
            self.result[fly_obj.values[1]][2] = f"{percent * 100}%"
            self.format_data()

        return progress_callback

    def clean(self):
        if self.uploading != 0:
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.result = {}

    def delete_node(self):
        # 获取选中的节点
        if self.uploading != 0:
            return
        item = self.tree.focus()
        if item != "":
            # 从Treeview中移除该节点及其子节点
            values = self.tree.item(item)['values']  # 获取该项的值列表
            del self.result[values[1]]
            self.tree.delete(item)
