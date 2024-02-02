#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : scorems
# filename : pages
# author : ly_13
# date : 2022/10/13
from tkinter import Menu

from views import ListFrame, UploadFrame


class MainPage(object):
    def __init__(self, master=None):
        self.root = master
        self.list_page = ListFrame(self.root)
        self.upload_page = UploadFrame(self.root)
        self.init_page()
        self.current = 'upload_page'

    def init_page(self):
        self.upload_page.pack()  # 默认显示数据录入界面
        menubar = Menu(self.root)
        menubar.add_command(label='上传应用', command=self.change_page('upload_page'))
        menubar.add_command(label='子平台配置信息', command=self.change_page('list_page'))
        self.root['menu'] = menubar  # 设置菜单栏

    def change_page(self, active='upload_page'):
        def change():
            if self.current == active:
                return change

            current_obj = getattr(self, self.current)
            if getattr(current_obj, 'uploading') != 0:
                return change

            getattr(self, active).pack()
            pages = ['list_page', 'upload_page']
            for page in set(pages) - {active}:
                getattr(self, page).pack_forget()
            self.current = active

        return change
