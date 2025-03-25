#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
微信机器人GUI启动脚本
"""

import os
import sys
import logging
import time
from PyQt5.QtWidgets import QApplication
from wcferry import Wcf
import signal
from argparse import ArgumentParser

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from configuration import Config
from robot import Robot
from constants import ChatType
from gui.main_window import MainWindow
from base.func_time import get_time
from robot import Robot, __version__

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('wechat_robot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger("StartGui")

def main():
    
    # 设置日志级别为INFO，确保所有消息都能显示
    logging.getLogger().setLevel(logging.INFO)
    
    config = Config()
    wcf = Wcf(debug=True)

    def handler(sig, frame):
        wcf.cleanup()  # 退出前清理环境
        exit(0)

    signal.signal(signal.SIGINT, handler)

    print("\n----------------------------------------------")
    print("开始初始化微信机器人，所有微信消息将显示在终端窗口")
    print("----------------------------------------------\n")
    
    robot = Robot(config, wcf, ChatType.DEEPSEEK)
    robot.LOG.info(f"WeChatRobot【{__version__}】成功启动···")

    # 机器人启动发送测试消息
    robot.sendTextMsg(f"机器人启动成功！\n{get_time()}", "filehelper")
    
    # 启用接收消息
    try:
        robot.enableReceivingMsg()
        logger.info("消息接收功能已启用，所有收到的微信消息将显示在此窗口")
        print("\n>>> 微信消息监听中...\n")
    except Exception as e:
        logger.error(f"启用消息接收失败: {e}")  
    
    # 启动GUI
    app = QApplication(sys.argv)
    window = MainWindow(robot)
    
    # 先显示界面，再启用消息接收
    window.show()
    
    # 主窗口显示后，再次提示消息接收状态
    logger.info("GUI已显示，微信消息监听中")
    QApplication.processEvents()  # 处理待处理的事件
    
    # 执行应用
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main()) 