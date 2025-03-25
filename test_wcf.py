#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试wcferry连接
"""

import os
import sys
import time
import traceback
from wcferry import Wcf

def check_dll_files():
    """检查wcferry相关的DLL文件"""
    wcf_dir = os.path.expanduser("~/.wcf")
    print(f"\nWCF目录状态: {os.path.exists(wcf_dir)}")
    if os.path.exists(wcf_dir):
        print(f"WCF目录内容:")
        for root, dirs, files in os.walk(wcf_dir):
            for file in files:
                print(f" - {os.path.join(root, file)}")
    else:
        print("WCF目录不存在，可能需要重新安装wcferry")
    
    # 检查Python包目录中的DLL
    try:
        import wcferry
        wcf_pkg_dir = os.path.dirname(wcferry.__file__)
        print(f"\nwcferry包目录: {wcf_pkg_dir}")
        if os.path.exists(wcf_pkg_dir):
            print("wcferry包目录内容:")
            for root, dirs, files in os.walk(wcf_pkg_dir):
                for file in files:
                    if file.endswith('.dll'):
                        print(f" - {os.path.join(root, file)}")
    except Exception as e:
        print(f"检查wcferry包目录时出错: {e}")

print("正在初始化wcferry...")
try:
    # 获取并显示wcferry版本
    import wcferry
    print(f"wcferry版本: {wcferry.__version__}")
    
    # 尝试使用debug模式初始化
    print("尝试初始化Wcf对象...")
    try:
        wcf = Wcf(debug=True)
        print("Wcf对象初始化成功！")
    except Exception as init_error:
        print(f"Wcf对象初始化失败: {init_error}")
        check_dll_files()
        raise init_error
    
    # 测试基本功能
    print("尝试获取自身wxid...")
    try:
        self_wxid = wcf.get_self_wxid()
        print(f"机器人ID: {self_wxid}")
    except Exception as e:
        print(f"获取自身wxid失败: {e}")
        raise
    
    try:
        alias = wcf.get_alias()
        print(f"机器人名称: {alias}")
    except Exception as e:
        print(f"获取别名失败: {e}")
    
    # 获取通讯录信息
    try:
        print("\n获取联系人列表...")
        contacts = wcf.get_contacts()
        print(f"总联系人数: {len(contacts)}")
    except Exception as e:
        print(f"获取联系人失败: {e}")
    
    # 获取群聊列表
    try:
        print("\n获取群聊列表...")
        chatrooms = wcf.get_chatrooms()
        print(f"总群聊数: {len(chatrooms)}")
    except Exception as e:
        print(f"获取群聊列表失败: {e}")
    
    # 尝试一个基本API
    try:
        print("\n尝试发送一条消息到文件传输助手...")
        result = wcf.send_text("这是一条测试消息 - " + time.strftime("%Y-%m-%d %H:%M:%S"), "filehelper")
        print(f"消息发送结果: {'成功' if result else '失败'}")
    except Exception as e:
        print(f"发送消息失败: {e}")
    
except Exception as e:
    print("初始化失败！")
    print(f"错误类型: {type(e).__name__}")
    print(f"错误信息: {e}")
    print("\n详细错误堆栈:")
    traceback.print_exc()
    check_dll_files()

if __name__ == "__main__":
    pass 