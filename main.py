#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import signal
import sys
import time
from argparse import ArgumentParser
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer

from base.func_report_reminder import ReportReminder
from base.func_time import get_time
from configuration import Config
from constants import ChatType
from robot import Robot, __version__, get_wxid_by_name
from wcferry import Wcf
from gui.main_window import MainWindow

def main(chat_type: int):
    try:
        # 创建QApplication实例
        app = QApplication(sys.argv)
        
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
            
        def handler(sig, frame):
            print("正在快速退出程序...")
            try:
                # 先调用Robot的清理方法，确保wcf资源被正确清理
                if 'robot' in globals() and hasattr(robot, 'cleanup'):
                    print("正在调用Robot清理方法...")
                    robot.cleanup()
                
                # 然后处理Qt应用
                print("正在退出Qt应用...")
                app.processEvents()  # 处理待处理的事件
                app.quit()  # 退出Qt应用
                print("已发送退出信号")
            except Exception as e:
                print(f"退出时出错: {e}")
                
                # 最后尝试强制退出
                try:
                    if 'robot' in globals() and hasattr(robot, 'wcf'):
                        robot.wcf.cleanup()
                except:
                    pass
                    
                # 强制退出
                import os
                os._exit(0)

        signal.signal(signal.SIGINT, handler)

        print("正在初始化机器人...")
        try:
            robot = Robot(config, wcf, chat_type, load_from_cache=True)  # 启用从缓存加载联系人
            robot.LOG.info(f"WeChatRobot【{__version__}】成功启动···")
        except Exception as e:
            print(f"机器人初始化失败: {str(e)}")
            raise

        # 机器人启动发送测试消息
        print("发送启动测试消息...")
        robot.sendTextMsg(f"机器人启动成功！\n{get_time()}", "filehelper")
        #   robot.newsReport("filehelper")     
        
        # 创建并显示主窗口
        print("创建主窗口...")
        main_window = MainWindow(robot)
        main_window.show()
        
        # 确保任务群组同步到配置
        print("同步任务群组到配置...")
        main_window.task_executor.sync_task_groups_to_config()
        
        # 启用消息接收 - 移到MainWindow创建之后执行，确保task_executor已设置
        print("启用消息接收...")
        robot.enableReceivingMsg()
        #robot.weatherReport(["filehelper"])  # 修改为列表形式

        # 创建定时器执行原有的定时任务
        #print("设置定时任务...")
        #timer = QTimer()
        #timer2 = QTimer()
        #timer2.timeout.connect(lambda: robot.newsReport()) 
        #timer2.timeout.connect(lambda: ReportReminder.remind(robot=robot)) 
        #timer2.timeout.connect(lambda: robot.weatherReport(["郭蕾"]))  # 修改为列表形式
        #timer2.start(24 * 60 * 60 * 1000)  # 每24小时检查一次
        
        #timer3 = QTimer()
        #timer3.timeout.connect(lambda: ReportReminder.remind(robot=robot))  # 日报提醒
        #timer3.start(24 * 60 * 60 * 1000)  # 每24小时检查一次
        
        print("启动完成！")
        # 运行Qt事件循环
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"程序启动失败: {e}")
        import traceback
        traceback.print_exc()
        app = QApplication(sys.argv)
        QMessageBox.critical(None, "错误", f"程序启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('-c', type=int, default=ChatType.DEEPSEEK, help=f'选择模型参数序号: {ChatType.help_hint()}')
    args = parser.parse_args().c
    main(args)
