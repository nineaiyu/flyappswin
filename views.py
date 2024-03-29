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

from cli import FLYCliSer, AppInfo
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
        self.root.geometry('%dx%d' % (800, 130))
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
            Entry(self.root, textvariable=getattr(self, key), width=120).grid(row=index, column=1, stick=E)
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
            width = 980
            if column == 'name':
                width = 300
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
        self.button_cancel = None
        self.tree = None
        self.button = None
        self.button_delete = None
        self.button_clean = None
        self.count = 0
        self.uploading = 0
        self.pools = None
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
        if self.button_cancel:
            self.button_cancel.destroy()

    def pack(self, *args, **kwargs):
        super().pack(*args, **kwargs)

        # 树状标签
        columns = ("idx", "name", "file_path", "bundleid", "version", "status")
        self.tree = ttk.Treeview(self, show="headings", columns=columns, selectmode=BROWSE, padding=5)
        self.tree['height'] = 20
        self.tree.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.tree.column("idx", anchor="w", width=50)  # 设置表格文字靠左
        self.tree.column("name", anchor="w", width=100)
        self.tree.column("file_path", anchor="w", width=350)
        self.tree.column("bundleid", anchor="w", width=250)
        self.tree.column("version", anchor="w", width=100)
        self.tree.column("status", anchor="w", width=430)

        self.tree.heading("idx", text="序号")  # 设置表格头部标题
        self.tree.heading("name", text="匹配配置名称")
        self.tree.heading("file_path", text="文件地址")
        self.tree.heading("bundleid", text="包名")
        self.tree.heading("version", text="版本")
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
        self.button_cancel = Button(text="取消上传", command=self.upload_cancel, padx=5, pady=5)
        self.button_cancel.pack()

        self.button_delete = Button(text="选中删除", command=self.delete_node, padx=5, pady=5)
        self.button_delete.pack()
        self.button_clean = Button(text="清空", command=self.clean, padx=5, pady=5)
        self.button_clean.pack()
        self.button.place(relx=0.6, rely=0.9)
        self.button_cancel.place(relx=0.7, rely=0.9)
        self.button_clean.place(relx=0.5, rely=0.9)
        self.button_delete.place(relx=0.4, rely=0.9)
        self.master.protocol('WM_DELETE_WINDOW', self.destroy_func)

    def destroy_func(self):
        self.upload_cancel()
        self.master.destroy()

    def upload_cancel(self):
        for item in self.result.values():
            if item[2].startswith("上传成功"):
                continue
            try:
                item[-1] = True
                if item[-2].cancel():
                    self.result[item[0]][2] = '取消成功'
                else:
                    self.result[item[0]][2] = '取消成功'
            except:
                pass
        if self.pools:
            self.pools.shutdown(wait=False)
        self.uploading = 0
        self.format_data()

    def loop(self, force=False):
        if self.uploading and force:
            return
        self.format_data()
        if self.uploading or force:
            self.tree.after(500, self.loop)

    def open_url(self, *args, **kwargs):
        item = self.tree.focus()  # 获取当前选中项
        values = self.tree.item(item)['values']  # 获取该项的值列表
        urlx = values[3]
        url = urlx.split('下载地址：')[-1]
        if url and url.startswith('http'):
            webbrowser.open(url)

    def get_config_name(self, file_name: str):
        for name, token in config.result.items():
            if file_name.startswith(name):
                return name, token
        return None, None

    def get_app_info(self, item):
        file_path = item[1]
        appobj = AppInfo(file_path)
        item[3] = appobj
        item[4] = appobj.get_app_data()
        if item[2] == '解析中':
            item[2] = '可上传'
        self.format_data()

    def dragged_files(self, files):
        for file_path in files:
            file_path = file_path.decode('gbk')
            file_name = os.path.basename(file_path)
            # name = ".".join(os.path.basename(file_path).split('.')[:-1])
            name, token = self.get_config_name(file_name)
            status = "解析中"
            if not token:
                name = ""
                status = "不可上传"
            # appobj = AppInfo(file_path)
            # appinfo = appobj.get_app_data()
            inster_value = [name, file_path, status, None, {}, None, False]
            self.result[name] = inster_value
            # files_show.insert('', index=self.count, values=inster_value)
        self.format_data()
        self.pools = ThreadPoolExecutor(3)

        for item in self.result.values():
            self.pools.submit(self.get_app_info, item)

    # @throttle
    def format_data(self):
        try:
            for item in self.tree.get_children():
                self.tree.delete(item)
            index = 1
            for key, item in self.result.items():
                app_info = item[-3]
                self.tree.insert("", index, values=[index, *item[0:2], app_info.get('bundle_id'),
                                                    f"{app_info.get('version')}  {app_info.get('versioncode')}",
                                                    item[2]])
                index += 1
        except Exception as e:
            pass

    def upload_task(self, filepath, token, row):
        if os.path.isfile(filepath) and filepath.split('.')[-1].lower() in ['ipa', 'apk']:
            self.uploading += 1
            fly_obj = FLYCliSer("https://app.hehejoy.cn/", token, self.progress_callback, row)
            self.result[row[0]][2] = f"应用分析中..."
            # self.format_data()
            appobj = self.result[row[0]][3]
            appinfo = self.result[row[0]][4]
            result_info = fly_obj.upload_app(filepath, appobj, appinfo, None, None, None)
            master_release = result_info.get('master_release', {})
            self.result[row[0]][
                2] = f"上传成功，版本：{master_release.get('app_version')}  {master_release.get('build_version')}，下载地址：{result_info.get('preview_url')}"
            # self.format_data()
            self.uploading -= 1

    def upload(self):
        if self.uploading != 0:
            return
        self.pools = ThreadPoolExecutor(3)
        # try:
        for row in self.tree.master.result.values():
            # for item in self.tree.get_children():
            #     values = self.tree.item(item)['values']  # 获取该项的值列表
            # row : ['熟客麻将', 'C:\\Users\\ly_13\\Downloads\\熟客麻将-1.0.4-achz.apk', '可上传']
            if len(row) != 7:
                continue
            if row[2].startswith('上传成功') or row[2] not in ['取消成功', '可上传']:
                continue
            row[-1] = False
            filepath = row[1]
            name, token = self.get_config_name(os.path.basename(filepath))
            if not name:
                continue
            self.loop(True)
            self.result[row[0]][-2] = self.pools.submit(self.upload_task, filepath, token, row)
            print(name, filepath, token)

    def progress_callback(self, fly_obj, offset, total_size):
        def progress_callback(upload_size, now_part_size):
            percent = (offset + upload_size) / total_size  # 接收的比例
            # print(fly_obj.values)
            # print(11, self.result[fly_obj.values[1]], fly_obj.values)
            self.result[fly_obj.values[0]][2] = f"{percent * 100:.3f}%"
            if fly_obj.values[-1]:
                self.result[fly_obj.values[0]][2] = '取消成功'
            # self.format_data(self.result[fly_obj.values[1]])

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
