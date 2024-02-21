# flyappswin

基于Python的图形化tkinte的fly分发平台批量上传flyappswin

### 生成exe客户端
```shell
pip install pyinstaller
```

```shell
pyinstaller -F -w main.py -n '应用批量上传v6' --add-data="static:static"
```
### 带有命令框的，用与调试
```shell
pyinstaller -F -w -d all -n '应用批量上传v6' -c main.py --add-data="static:static"
```

