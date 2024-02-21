# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
from tkinter import Tk
from pages import MainPage
if __name__ == '__main__':
    root = Tk()
    root.title('子平台apk批量上传')
    # 桌面长宽
    win_w = root.winfo_screenwidth()
    win_h = root.winfo_screenheight()

    # 窗口长宽
    width = 1300
    height = 500

    # 设置窗口位置和长宽
    root.geometry(f"{width}x{height}+{(win_w - width) // 2}+{(win_h - height) // 2}")
    MainPage(root)
    root.mainloop()
