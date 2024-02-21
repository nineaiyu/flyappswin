#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project: 1月 
# author: NinEveN
# date: 2021/1/9
import os
import plistlib
import random
import re
import sys
import tempfile
import zipfile

import oss2
import requests
from oss2 import determine_part_size, SizedFileAdapter
from oss2.models import PartInfo

from libs.androguard.core import apk

'''
pip install --upgrade pip
pip install setuptools-rust -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install oss2 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install requests-toolbelt -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install androguard -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install qiniu -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple
'''


def progress(percent, width=50):
    if percent >= 1:
        percent = 1
    show_str = ('[%%-%ds]' % width) % (int(width * percent) * '#')
    print('\r%s %d%% ' % (show_str, int(100 * percent)), file=sys.stdout, flush=True, end='')


def local_upload_callback(monitor):
    progress(monitor.bytes_read / monitor.len, width=100)


def qiniu_progress_callback(upload_size, total_size):
    progress(upload_size / total_size, width=100)


def alioss_progress_callback_fun(self, offset, total_size):
    def progress_callback(upload_size, now_part_size):
        percent = (offset + upload_size) / total_size  # 接收的比例
        progress(percent, width=100)

    return progress_callback


def upload_aliyunoss(self, access_key_id, access_key_secret, security_token, endpoint, bucket, local_file_full_path,
                     filename,
                     headers=None):
    stsauth = oss2.StsAuth(access_key_id, access_key_secret, security_token)
    bucket = oss2.Bucket(stsauth, endpoint, bucket)
    total_size = os.path.getsize(local_file_full_path)
    # determine_part_size方法用于确定分片大小。
    part_size = determine_part_size(total_size, preferred_size=1024 * 1024 * 10)
    upload_id = bucket.init_multipart_upload(filename, headers=headers).upload_id
    parts = []
    # 逐个上传分片。

    with open(local_file_full_path, 'rb') as f:
        part_number = 1
        offset = 0
        while offset < total_size:
            num_to_upload = min(part_size, total_size - offset)
            if len(self.values) == 5 and self.values[-1]:
                raise '停止上传'
            if self.progress_callback:
                progress_callback = self.progress_callback(self, offset, total_size)
            else:
                progress_callback = alioss_progress_callback_fun(self, offset, total_size)
            result = bucket.upload_part(filename, upload_id, part_number, SizedFileAdapter(f, num_to_upload),
                                        progress_callback=progress_callback)
            parts.append(PartInfo(part_number, result.etag))
            offset += num_to_upload
            part_number += 1
    bucket.complete_multipart_upload(filename, upload_id, parts)
    if not filename.endswith('.png.tmp'):
        print("\n数据上传存储成功.", end='')


class FLYCliSer(object):

    def __init__(self, fly_cli_domain, fly_cli_token, progress_callback, values):
        self.fly_cli_domain = fly_cli_domain
        self.values = values
        self.progress_callback = progress_callback
        self._header = {
            "User-Agent": "fly-cli",
            "accept": "application/json",
            "APIAUTHORIZATION": fly_cli_token
        }

    def get_upload_token(self, bundleid, type):
        url = '%s/api/v2/fir/server/analyse' % self.fly_cli_domain
        data = {"bundleid": bundleid, "type": type}
        req = requests.post(url, json=data, headers=self._header)
        if req.status_code == 200:
            if req.json()['code'] == 1000:
                return req.json()['data']
        raise AssertionError(req.text)

    def analyse(self, data):
        url = '%s/api/v2/fir/server/analyse' % self.fly_cli_domain
        req = requests.put(url, json=data, headers=self._header)
        if req.status_code == 200:
            if req.json()['code'] == 1000:
                master_download_url = req.json().get('data', {}).get('preview_url')
                print("应用 %s  %s 上传更新成功" % (data.get('appname'), data.get('bundleid')))
                print("当前应用下载连接：", master_download_url)
                print("当前版本下载连接：", master_download_url + '?release_id=' + data.get('upload_key').split('.')[0])
                return master_download_url
        raise AssertionError(req.text)

    def upload_app(self, app_path, r_short, r_name, r_change_log):
        appobj = AppInfo(app_path)
        appinfo = appobj.get_app_data()
        print("获取应用信息", appinfo)
        icon_path = appobj.make_app_png(icon_path=appinfo.get("icon_path", None))
        print("获取图标信息", icon_path)
        bundle_id = appinfo.get("bundle_id")
        upcretsdata = self.get_upload_token(bundle_id, appinfo.get("type"))
        print("获取上传授权", upcretsdata)
        if r_short:
            upcretsdata['short'] = r_short
        if r_name:
            appinfo['labelname'] = r_name
        if r_change_log:
            upcretsdata['changelog'] = r_change_log

        if appinfo.get('iOS', '') == 'iOS':
            f_type = '.ipa'
        else:
            f_type = '.apk'
        filename = "%s-%s-%s%s" % (appinfo.get('labelname'), appinfo.get('version'), upcretsdata.get('short'), f_type)
        headers = {
            'Content-Disposition': 'attachment; filename="%s"' % filename.encode(
                "utf-8").decode("latin1"),
            'Cache-Control': ''
        }

        if upcretsdata['storage'] == 2:
            # 阿里云存储
            png_auth = upcretsdata['png_token']

            upload_aliyunoss(self, png_auth['access_key_id'], png_auth['access_key_secret'], png_auth['security_token'],
                             png_auth['endpoint'], png_auth['bucket'], icon_path, upcretsdata['png_key'])

            file_auth = upcretsdata['upload_token']
            upload_aliyunoss(self, file_auth['access_key_id'], file_auth['access_key_secret'],
                             file_auth['security_token'],
                             file_auth['endpoint'], file_auth['bucket'], app_path, upcretsdata['upload_key'], headers)

        app_data = {
            "filename": os.path.basename(app_path),
            "filesize": os.path.getsize(app_path),
            "appname": appinfo['labelname'],
            "bundleid": appinfo['bundle_id'],
            "version": appinfo['version'],
            "buildversion": appinfo['versioncode'],
            "miniosversion": appinfo['miniosversion'],
            "release_type": appinfo.get('release_type', ''),
            "release_type_id": 2,
            "udid": appinfo.get('udid', []),
            "type": appinfo['type'],
        }
        return self.analyse({**app_data, **upcretsdata})


class AppInfo(object):
    def __init__(self, app_path):
        self.app_path = app_path
        self.result = {}

    def make_app_png(self, icon_path):
        zf = zipfile.ZipFile(self.app_path)
        iconfile = ""
        if icon_path:
            size = len(zf.read(icon_path))
            iconfile = icon_path
        else:
            name_list = zf.namelist()
            if self.app_path.endswith("apk"):
                pattern = re.compile(r'res/drawable[^/]*/app_icon.png')
            elif self.app_path.endswith("ipa"):
                pattern = re.compile(r'Payload/[^/]*.app/AppIcon[^/]*[^(ipad)].png')
            else:
                raise Exception("File type error")

            size = 0
            for path in name_list:
                m = pattern.match(path)
                if m is not None:
                    filepath = m.group()
                    fsize = len(zf.read(filepath))
                    if size == 0:
                        iconfile = filepath
                    if size < fsize:
                        size = fsize
                        iconfile = filepath
        if size == 0:
            raise Exception("File size error")
        if iconfile == "":
            raise Exception("read File icon error")

        filename = ''.join(random.sample(
            ['z', 'y', 'x', 'w', 'v', 'u', 't', 's', 'r', 'q', 'p', 'o', 'n', 'm', 'l', 'k', 'j', 'i', 'h', 'g', 'f',
             'e', 'd', 'c', 'b', 'a'], 16))

        temp_dir = tempfile.gettempdir()
        if not os.path.isdir(os.path.join(temp_dir, "tmp", "icon")):
            os.makedirs(os.path.join(temp_dir, "tmp", "icon"))
        with open(os.path.join(temp_dir, "tmp", "icon", filename + '.png'), 'wb') as f:
            f.write(zf.read(iconfile))

        return os.path.join(temp_dir, "tmp", "icon", filename + '.png')

    def get_app_data(self):
        if self.app_path.endswith("apk"):
            return self.__get_android_data()
        elif self.app_path.endswith("ipa"):
            return self.__get_ios_data()
        else:
            raise Exception("File type error")

    def __get_ios_info_path(self, ipaobj):
        infopath_re = re.compile(r'Payload/[^/]*.app/Info.plist')
        for i in ipaobj.namelist():
            m = infopath_re.match(i)
            if m is not None:
                return m.group()

    def __get_android_data(self):
        try:
            apkobj = apk.APK(self.app_path)
        except Exception as err:
            print("解析应用失败", err)
            raise err
        else:
            if apkobj.is_valid_APK():
                versioncode = apkobj.get_androidversion_code()
                bundle_id = apkobj.get_package()
                labelname = apkobj.get_app_name()
                version = apkobj.get_androidversion_name()
                self.result = {
                    "labelname": labelname,
                    "bundle_id": bundle_id,
                    "versioncode": versioncode,
                    "version": version,
                    "type": "Android",
                    "miniosversion": apkobj.get_min_sdk_version(),
                    "icon_path": apkobj.get_app_icon()
                }
        return self.result

    def __get_ios_data(self):
        if zipfile.is_zipfile(self.app_path):
            ipaobj = zipfile.ZipFile(self.app_path)
            info_path = self.__get_ios_info_path(ipaobj)
            if info_path:
                plist_data = ipaobj.read(info_path)
                plist_root = plistlib.loads(plist_data)
                labelname = plist_root['CFBundleDisplayName']
                versioncode = plist_root['CFBundleVersion']
                bundle_id = plist_root['CFBundleIdentifier']
                version = plist_root['CFBundleShortVersionString']
                self.result = {
                    "labelname": labelname,
                    "bundle_id": bundle_id,
                    "versioncode": versioncode,
                    "version": version,
                    "type": "iOS",
                    "miniosversion": plist_root['MinimumOSVersion']
                }

            release_type_info = self.__get_ios_release_type(ipaobj)
            if info_path:
                plist_data = ipaobj.read(release_type_info)
                if b"ProvisionedDevices" in plist_data:
                    b = re.findall(rb'<key>ProvisionedDevices</key><array>(.*)</array><key>TeamIdentifier</key>',
                                   plist_data.replace(b'\n', b'').replace(b'\r', b'').replace(b"\t", b""))[0]
                    clist = re.split(rb'<string>|</string>', b)
                    nudidlist = []
                    for x in clist:
                        if x:
                            nudidlist.append(x.decode('utf-8'))
                    self.result["release_type"] = "Adhoc"
                    self.result['udid'] = nudidlist
                else:
                    self.result["release_type"] = "Inhouse"
                    self.result["udid"] = []
        return self.result

    def __get_ios_release_type(self, ipaobj):
        infopath_re = re.compile(r'Payload/[^/]*.app/embedded.mobileprovision')
        for i in ipaobj.namelist():
            m = infopath_re.match(i)
            if m is not None:
                return m.group()
