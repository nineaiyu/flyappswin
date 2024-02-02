# scorems

基于Python的图形化tkinte的fly分发平台批量上传flyappswin

### 生成exe客户端

```shell
pip install pyinstaller
 pyinstaller -F -w main.py  --add-data="static:static"
```
### 带有命令框的，用与调试
```shell
pyinstaller -F -w -d all -c main.py --add-data="static:static"
```

