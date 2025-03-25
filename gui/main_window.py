import sys
import os
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QStatusBar, 
                           QToolBar, QAction, QMessageBox, QFileDialog, QScrollArea, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon
from typing import Dict, List

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from robot import Robot
from configuration import Config
from wcferry import Wcf
from constants import ChatType

# 使用相对导入
from .task_card import TaskCard
from .task_dialog import TaskDialog
from .config_manager import ConfigManager
from .task_executor import TaskExecutor
from .command_handler import CommandHandler
from .ai_settings import AISettings

class MainWindow(QMainWindow):
    def __init__(self, robot):
        super().__init__()
        self.robot = robot
        self.setWindowTitle("微信机器人控制中心")
        self.setMinimumSize(800, 600)
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        
        # 初始化AI设置
        self.ai_settings = AISettings()
        
        # 初始化命令处理器并传递给Robot
        self.command_handler = CommandHandler(self.robot, self.ai_settings)
        self.robot.command_handler = self.command_handler  # 将命令处理器传递给Robot
        
        # 初始化任务执行器
        self.task_executor = TaskExecutor(self.robot)
        
        # 连接任务执行器的信号
        self.task_executor.status_changed.connect(self.on_task_status_changed)
        self.task_executor.stats_updated.connect(self.on_task_stats_updated)
        
        # 初始化联系人列表
        self.groups = {}
        self.friends = {}
        
        # 创建主窗口部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建任务卡片区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        
        # 创建任务卡片容器
        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.addStretch()
        
        self.scroll_area.setWidget(self.task_container)
        self.main_layout.addWidget(self.scroll_area)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 创建定时器用于更新状态
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # 5秒更新一次
        
        # 创建定时器用于运行机器人待处理的任务
        self.robot_job_timer = QTimer()
        self.robot_job_timer.timeout.connect(self.run_robot_jobs)
        self.robot_job_timer.start(1000)  # 每秒执行一次
        
        # 存储任务卡片的字典
        self.task_cards = {}
        
        # 加载任务
        self.load_tasks()
        
        # 自动更新联系人列表
        QTimer.singleShot(1000, self.update_contact_lists)
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # 添加任务按钮
        add_action = QAction("添加任务", self)
        add_action.triggered.connect(self.add_task)
        toolbar.addAction(add_action)
        
        # 导入配置按钮
        import_action = QAction("导入配置", self)
        import_action.triggered.connect(self.import_config)
        toolbar.addAction(import_action)
        
        # 导出配置按钮
        export_action = QAction("导出配置", self)
        export_action.triggered.connect(self.export_config)
        toolbar.addAction(export_action)
        
        # 刷新按钮
        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self.refresh_tasks)
        toolbar.addAction(refresh_action)
        
        # 更新联系人按钮
        update_contacts_action = QAction("更新联系人", self)
        update_contacts_action.triggered.connect(self.update_contact_lists)
        toolbar.addAction(update_contacts_action)
        
        # AI设置按钮
        ai_settings_action = QAction("AI设置", self)
        ai_settings_action.triggered.connect(self.show_ai_settings)
        toolbar.addAction(ai_settings_action)
        
        # 添加分隔线
        toolbar.addSeparator()
        
        # 诊断按钮
        diagnose_action = QAction("诊断", self)
        diagnose_action.triggered.connect(self.diagnose_system)
        toolbar.addAction(diagnose_action)
        
    def update_contact_lists(self):
        """更新群组和好友列表"""
        try:
            # 获取群组列表
            self.groups = {}
            for group_wxid, group_name in self.robot.allGroups.items():
                self.groups[group_name] = group_wxid
            
            # 获取好友列表
            friends = self.robot.wcf.get_friends()
            self.friends = {friend["name"]: friend["wxid"] for friend in friends}
            
            # 更新所有任务对话框中的下拉列表
            for dialog in self.findChildren(TaskDialog):
                dialog.update_contact_lists(self.groups, self.friends)
                
            self.status_bar.showMessage("联系人列表更新成功")
        except Exception as e:
            self.status_bar.showMessage(f"更新联系人列表失败: {str(e)}")
            
    def add_task(self):
        """添加新任务"""
        dialog = TaskDialog(self)
        dialog.update_contact_lists(self.groups, self.friends)
        if dialog.exec_():
            task_config = dialog.get_config()
            if self.config_manager.add_task(task_config):
                self.refresh_tasks()
            else:
                QMessageBox.warning(self, "错误", "添加任务失败")
            
    def import_config(self):
        """导入配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择配置文件", "", "JSON Files (*.json)")
        if file_path:
            if self.config_manager.import_config(file_path):
                self.refresh_tasks()
                QMessageBox.information(self, "成功", "配置导入成功")
            else:
                QMessageBox.warning(self, "错误", "配置导入失败")
        
    def export_config(self):
        """导出配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存配置文件", "", "JSON Files (*.json)")
        if file_path:
            if self.config_manager.export_config(file_path):
                QMessageBox.information(self, "成功", "配置导出成功")
            else:
                QMessageBox.warning(self, "错误", "配置导出失败")
        
    def refresh_tasks(self):
        """刷新任务列表"""
        # 清除现有任务卡片
        for card in self.task_cards.values():
            self.task_layout.removeWidget(card)
            card.deleteLater()
        self.task_cards.clear()
                
        # 加载任务
        self.load_tasks()
        
    def load_tasks(self):
        """加载任务列表"""
        tasks = self.config_manager.get_all_tasks()
        for task in tasks:
            self.add_task_card(task)
            
    def add_task_card(self, task_config: Dict):
        """添加任务卡片"""
        # 创建任务卡片
        card = TaskCard(task_config, self)
        
        # 连接信号
        card.start_task_signal.connect(self.start_task)
        card.stop_task_signal.connect(self.stop_task)
        card.edit_task_signal.connect(self.edit_task)
        card.clone_task_signal.connect(self.clone_task)
        
        # 添加到布局
        self.task_layout.insertWidget(self.task_layout.count() - 1, card)
        self.task_cards[task_config["name"]] = card
        
    def start_task(self, task_name):
        """启动任务"""
        task_config = self.config_manager.get_task(task_name)
        if task_config:
            if self.task_executor.start_task(task_config):
                task_config["status"] = "running"
                self.config_manager.update_task(task_name, task_config)
                self.refresh_tasks()
            else:
                QMessageBox.warning(self, "错误", "启动任务失败")
                
    def stop_task(self, task_name):
        """停止任务"""
        task_config = self.config_manager.get_task(task_name)
        if task_config:
            if self.task_executor.stop_task(task_name):
                task_config["status"] = "stopped"
                self.config_manager.update_task(task_name, task_config)
                self.refresh_tasks()
            else:
                QMessageBox.warning(self, "错误", "停止任务失败")
                
    def edit_task(self, task_name):
        """编辑任务"""
        task_config = self.config_manager.get_task(task_name)
        if task_config:
            dialog = TaskDialog(self)
            dialog.load_config(task_config)
            dialog.update_contact_lists(self.groups, self.friends)
            if dialog.exec_():
                new_config = dialog.get_config()
                if self.config_manager.update_task(task_name, new_config):
                    self.refresh_tasks()
                else:
                    QMessageBox.warning(self, "错误", "更新任务失败")
                    
    def clone_task(self, task_name):
        """克隆任务"""
        task_config = self.config_manager.get_task(task_name)
        if task_config:
            new_config = task_config.copy()
            new_config["name"] = f"{task_config['name']}_副本"
            new_config["status"] = "stopped"
            if self.config_manager.add_task(new_config):
                self.refresh_tasks()
            else:
                QMessageBox.warning(self, "错误", "克隆任务失败")
                
    def on_task_status_changed(self, task_name: str, status: str):
        """任务状态变化处理"""
        if task_name in self.task_cards:
            self.task_cards[task_name].update_status(status)
            
    def on_task_stats_updated(self, task_name: str, stats: Dict):
        """任务统计数据更新处理"""
        if task_name in self.task_cards:
            self.task_cards[task_name].update_stats(stats)
            
    def update_status(self):
        """更新状态栏"""
        try:
            # 获取微信连接状态
            is_logged_in = self.robot.wcf.is_login()
            status_text = f"微信状态: {'已登录' if is_logged_in else '未登录'}"
            
            # 获取任务状态
            running_tasks = sum(1 for task in self.task_cards.values() if task.is_running())
            status_text += f" | 运行中任务: {running_tasks}/{len(self.task_cards)}"
            
            # 获取AI状态
            ai_status = "已开启" if self.ai_settings.is_ai_enabled() else "已关闭"
            status_text += f" | AI功能: {ai_status}"
            
            self.status_bar.showMessage(status_text)
        except Exception as e:
            self.status_bar.showMessage(f"更新状态失败: {str(e)}")
            
    def show_ai_settings(self):
        """显示AI设置界面"""
        # 这里可以实现一个AI设置对话框
        # 暂时用消息框代替
        ai_status = "开启" if self.ai_settings.is_ai_enabled() else "关闭"
        allowed_users = len(self.ai_settings.get_users())
        allowed_groups = len(self.ai_settings.get_groups())
        
        message = f"""
        AI设置状态:
        
        AI功能: {ai_status}
        允许的用户数: {allowed_users}
        允许的群组数: {allowed_groups}
        
        您可以通过发送"^设置"命令来配置AI功能。
        """
        
        QMessageBox.information(self, "AI设置", message)
    
    def run_robot_jobs(self):
        """运行机器人待处理的任务，替代keepRunningAndBlockProcess()"""
        try:
            # 调用机器人的runPendingJobs方法执行定时任务
            self.robot.runPendingJobs()
        except Exception as e:
            print(f"运行机器人任务失败: {e}")
            import traceback
            traceback.print_exc()
    
    def diagnose_system(self):
        """诊断系统状态"""
        try:
            print("开始系统诊断...")
            results = []
            
            # 检查1: 微信登录状态
            is_logged_in = self.robot.wcf.is_login()
            results.append(f"微信登录状态: {'已登录' if is_logged_in else '未登录'}")
            
            # 检查2: 消息接收状态
            is_receiving = self.robot.wcf.is_receiving_msg()
            results.append(f"消息接收状态: {'已启用' if is_receiving else '未启用'}")
            
            # 检查3: 尝试获取wxid
            try:
                wxid = self.robot.wxid
                results.append(f"当前登录的wxid: {wxid}")
            except Exception as e:
                results.append(f"获取wxid失败: {str(e)}")
            
            # 检查4: 尝试查询微信版本
            try:
                version = self.robot.wcf.get_wechat_version()
                results.append(f"微信版本: {version}")
            except Exception as e:
                results.append(f"查询微信版本失败: {str(e)}")
            
            # 检查5: 尝试发送简单消息
            try:
                test_msg = "诊断测试消息 " + time.strftime("%Y-%m-%d %H:%M:%S")
                test_result = self.robot.wcf.send_text(test_msg, "filehelper")
                results.append(f"测试消息发送API返回: {'成功' if test_result else '失败'}")
                results.append("提示: 即使API返回失败，实际消息可能仍已发送成功。请检查文件传输助手。")
            except Exception as e:
                results.append(f"测试消息发送异常: {str(e)}")
            
            # 显示诊断结果
            diagnosis_text = "\n".join(results)
            print(diagnosis_text)
            
            # 如果检测到问题，提供解决建议
            suggestions = []
            has_problem = False
            
            if not is_logged_in:
                has_problem = True
                suggestions.append("请确保微信已登录")
            
            if not is_receiving:
                has_problem = True
                suggestions.append("消息接收未启用，尝试重启应用")
                # 尝试重新启用消息接收
                try:
                    self.robot.enableReceivingMsg()
                    suggestions.append("已尝试重新启用消息接收")
                except Exception as e:
                    suggestions.append(f"重启消息接收失败: {str(e)}")
            
            # 添加建议：检查消息接收是否正常
            reply = QMessageBox.question(
                self,
                "消息接收测试",
                "为验证消息接收功能是否正常，请尝试在手机微信中向自己发送一条消息。\n\n您是否收到了自己发送的消息？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                has_problem = True
                suggestions.append("消息接收测试失败，建议尝试重启消息接收功能")
                suggestions.append("如果问题仍然存在，请尝试重新连接微信")
            else:
                results.append("消息接收测试通过: 成功收到消息")
                
            # 更新诊断文本
            diagnosis_text = "\n".join(results)
            
            if suggestions:
                suggestions_text = "\n".join(suggestions)
                diagnosis_text += f"\n\n建议操作:\n{suggestions_text}"
            
            if not has_problem:
                diagnosis_text += "\n\n未检测到明显问题，但消息处理可能仍有异常。建议重启应用后重试。"
                
            QMessageBox.information(self, "系统诊断结果", diagnosis_text)
        except Exception as e:
            error_msg = f"诊断过程出错: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "诊断失败", error_msg)
            
    def closeEvent(self, event):
        """关闭窗口时的处理"""
        # 停止所有任务
        self.task_executor.stop()
        
        # 停止定时器
        self.status_timer.stop()
        self.robot_job_timer.stop()
        
        # 记录日志
        print("微信机器人控制中心已关闭")
        
        event.accept() 