#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : scorems
# filename : models
# author : ly_13
# date : 2022/10/13
import json
import os

home_dir = os.path.expanduser("~")
print(home_dir)


class AppConfigDB(object):
    def __init__(self):
        self.db = os.path.join(os.path.expanduser("~"), ".flyapps.appconfig")
        self.result = {}
        self.load()

    def load(self):
        if os.path.exists(self.db):
            self.result = json.load(open(self.db, 'r', encoding='utf-8'))

    def save(self):
        json.dump(self.result, open(self.db, 'w', encoding='utf-8'))

    def add(self, name, api):
        self.result[name] = api
        self.save()

    def delete(self, name):
        try:
            self.result.pop(name)
            self.save()
        except KeyError:
            print("Key not found")

    def get(self, name):
        return self.result.get(name)


config = AppConfigDB()
