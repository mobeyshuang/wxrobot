#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
微信机器人GUI启动脚本
"""

import os
import sys
import logging
import time
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from wcferry import Wcf
import signal
from argparse import ArgumentParser

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from configuration import Config
from robot import Robot, __version__
from constants import ChatType
from gui.main_window import MainWindow
from base.func_time import get_time

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
    """主程序入口"""
    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # 初始化配置和机器人
        print("正在初始化配置...")
        config = Config()
        
        print("正在初始化wcferry...")
        try:
            # 尝试创建 Wcf 实例，明确指定 host 为 None
            wcf = Wcf(host=None, debug=True, block=True)
            print("wcferry 初始化成功")
            
            # 检查登录状态
            if not wcf.is_login():
                print("警告: 微信未登录")
            else:
                print("微信已登录")
                
        except Exception as e:
            print(f"wcferry 初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"wcferry 初始化失败: {str(e)}")
        
        # 等待微信登录
        print("等待微信登录...")
        retry_count = 0
        max_retries = 3
        while not wcf.is_login() and retry_count < max_retries:
            print(f"等待微信登录...({retry_count + 1}/{max_retries})")
            time.sleep(2)
            retry_count += 1
            
        if not wcf.is_login():
            raise Exception("微信登录超时，请确保微信已登录")
            
        print("微信登录成功！")
        
        # 创建机器人实例
        chat_type = ChatType.DEEPSEEK
        robot = Robot(config, wcf, chat_type)
        
        # 创建主窗口
        window = MainWindow(robot)
        window.show()
        
        # 设置定时器，定期处理可能的信号
        def check_signals():
            app.processEvents()
            
        timer = QTimer()
        timer.timeout.connect(check_signals)
        timer.start(100)  # 每100毫秒处理一次事件
        
        # 运行应用
        print("WeChatRobot应用已启动，等待事件循环...")
        exit_code = app.exec_()
        
        # 正常退出时进行清理
        print("正在退出应用...")
        if robot:
            try:
                print("正在清理机器人资源...")
                # 设置超时，防止卡住
                import threading
                import time
                
                cleanup_done = threading.Event()
                def do_cleanup():
                    try:
                        robot.cleanup()
                        cleanup_done.set()
                    except Exception as e:
                        print(f"清理机器人资源失败: {e}")
                        cleanup_done.set()
                
                # 启动清理线程
                cleanup_thread = threading.Thread(target=do_cleanup)
                cleanup_thread.daemon = True
                cleanup_thread.start()
                
                # 等待清理完成，最多等待1.5秒
                start_time = time.time()
                if not cleanup_done.wait(1.5):
                    print("警告: 机器人资源清理超时，继续退出流程")
                else:
                    print(f"机器人资源清理完成，耗时: {time.time() - start_time:.2f}秒")
            except Exception as e:
                print(f"清理机器人资源失败: {e}")
        
        # 强制垃圾回收
        try:
            import gc
            gc.collect()
        except:
            pass
            
        print("应用已经退出")
        return exit_code
    except Exception as e:
        print(f"程序启动失败: {e}")
        app = QApplication(sys.argv)
        QMessageBox.critical(None, "错误", f"程序启动失败: {e}")
        return 1

def signal_handler(sig, frame):
    """处理Ctrl+C等信号"""
    print(f"捕获到信号 {sig}，正在安全退出程序...")
    # 获取当前应用程序实例
    app = QApplication.instance()
    if app:
        # 尝试获取主窗口
        for widget in app.topLevelWidgets():
            if isinstance(widget, MainWindow):
                main_window = widget
                try:
                    # 尝试调用robot.cleanup()
                    if hasattr(main_window, 'robot') and hasattr(main_window.robot, 'cleanup'):
                        print("通过信号处理器调用robot.cleanup...")
                        # 使用线程调用cleanup，避免阻塞
                        import threading
                        def cleanup_thread():
                            try:
                                main_window.robot.cleanup()
                                print("robot.cleanup调用完成")
                            except Exception as e:
                                print(f"信号处理器中清理资源失败: {e}")
                        
                        # 启动清理线程
                        t = threading.Thread(target=cleanup_thread)
                        t.daemon = True
                        t.start()
                        
                        # 最多等待1.5秒
                        t.join(1.5)
                        if t.is_alive():
                            print("robot.cleanup超时，继续退出流程")
                except Exception as e:
                    print(f"信号处理器中清理资源失败: {e}")
                break
    
    print("正在退出Qt应用...")
    QApplication.quit()
    print("已发送退出信号")
    
    # 如果3秒后进程仍未退出，则强制退出(减少时间从5秒改为3秒)
    def force_exit():
        print("程序未在预期时间内退出，正在强制终止...")
        import os
        os._exit(1)
    
    # 设置强制退出定时器
    import threading
    exit_timer = threading.Timer(3.0, force_exit)
    exit_timer.daemon = True
    exit_timer.start()

if __name__ == "__main__":
    exit_code = main()
    # 确保程序正常退出
    try:
        print("程序正常结束")
        sys.exit(exit_code)
    except:
        # 如果sys.exit出错，使用os._exit强制退出
        print("使用备选方式退出程序")
        import os
        os._exit(exit_code) 