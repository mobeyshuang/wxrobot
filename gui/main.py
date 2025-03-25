import sys
import os
import time
from PyQt5.QtWidgets import QApplication, QMessageBox
from .main_window import MainWindow
from robot import Robot
from configuration import Config
from wcferry import Wcf
from constants import ChatType

def main():
    """主程序入口"""
    try:
        # 创建配置实例
        config = Config()
        
        # 创建wcferry实例
        wcf = Wcf(debug=True)
        
        # 等待微信连接
        retry_count = 0
        max_retries = 3
        while not wcf.is_login() and retry_count < max_retries:
            print(f"等待微信登录...({retry_count + 1}/{max_retries})")
            time.sleep(2)
            retry_count += 1
        
        if not wcf.is_login():
            print("微信登录超时，请确保微信已登录")
            app = QApplication(sys.argv)
            QMessageBox.warning(None, "错误", "微信登录超时，请确保微信已登录")
            return
        
        # 创建聊天类型，使用DEEPSEEK作为默认值
        chat_type = ChatType.DEEPSEEK
        
        # 创建机器人实例
        robot = Robot(config, wcf, chat_type)
        
        # 创建应用
        app = QApplication(sys.argv)
        
        # 创建主窗口
        window = MainWindow(robot)
        window.show()
        
        # 运行应用
        sys.exit(app.exec_())
    except Exception as e:
        print(f"程序启动失败: {e}")
        app = QApplication(sys.argv)
        QMessageBox.critical(None, "错误", f"程序启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 