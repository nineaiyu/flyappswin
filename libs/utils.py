#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : scorems
# filename : utils
# author : ly_13
# date : 2/2/2024
import os
import sys


def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)
