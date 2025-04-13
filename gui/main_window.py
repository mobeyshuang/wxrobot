import sys
import os
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QStatusBar, 
                           QToolBar, QAction, QMessageBox, QFileDialog, QScrollArea, QFrame, QMenu, QDialog, QGroupBox, QRadioButton, QDialogButtonBox, QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QListWidgetItem, QAbstractItemView)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, pyqtSlot
from PyQt5.QtGui import QIcon, QFont, QColor, QBrush
from typing import Dict, List
import json

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from robot import Robot, __version__
from configuration import Config
from wcferry import Wcf
from constants import ChatType

# 使用相对导入
from .task_card import TaskCard
from .task_dialog import TaskDialog
from .config_manager import ConfigManager
from .task_executor import TaskExecutor
from .transfer_task_dialog import TransferTaskDialog
from .reply_task_dialog import ReplyTaskDialog
from .scheduled_task_dialog import ScheduledTaskDialog
# from .weather_task_dialog import WeatherTaskDialog

class MainWindow(QMainWindow):
    def __init__(self, robot):
        """初始化主窗口"""
        super().__init__()
        self.robot = robot
        self.wcf = robot.wcf
        self.groups = robot.allGroups
        self.contacts = robot.contacts  # 直接使用robot中的联系人数据
        self.tasks = []
        self.config_manager = ConfigManager()
        self.group_members_cache = getattr(robot, 'group_members', {})  # 使用robot中的群成员缓存
        self.task_manager = self  # 将自身作为任务管理器
        
        # 初始化微信文件目录设置
        self.wechat_file_dir = None
        if hasattr(self.robot, 'config') and hasattr(self.robot.config, 'get'):
            self.wechat_file_dir = self.robot.config.get("WECHAT_FILES_DIR", "")
        
        # 设置窗口标题和大小
        self.setWindowTitle(f"WeChatRobot【{__version__}】")
        self.setMinimumSize(800, 600)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        self.main_layout = QVBoxLayout(central_widget)
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建任务列表
        self.create_task_list()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建定时器
        self.create_timers()
        
        # 创建是否更新联系人的标记
        self.is_updating_contacts = False
        
        # 初始化任务执行器
        self._init_task_executor()
        
        # 设置应用样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QStatusBar {
                background-color: #f0f0f0;
                border-top: 1px solid #e0e0e0;
                color: #555;
                padding: 3px;
            }
            QLabel {
                color: #444;
                font-family: 'Microsoft YaHei', Arial, sans-serif;
            }
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
            QPushButton:pressed {
                background-color: #2a66c8;
            }
            QTableView {
                border: 1px solid #ddd;
                border-radius: 4px;
                selection-background-color: #e0e8f5;
                selection-color: #333;
                alternate-background-color: #f9f9f9;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 6px;
                border: 1px solid #ddd;
                border-left: none;
                font-weight: bold;
                color: #555;
            }
        """)
        
        # 设置全局字体大小
        font = QFont()
        font.setPointSize(10)
        QApplication.setFont(font)
        
        # 启动定时器检查任务状态
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_task_status)
        self.timer.start(5000)  # 每5秒更新一次任务状态
        
        # 创建定时器用于运行机器人待处理的任务
        self.robot_job_timer = QTimer()
        self.robot_job_timer.timeout.connect(self.run_robot_jobs)
        self.robot_job_timer.start(1000)  # 每秒执行一次
        
        # 在 task_executor 初始化后加载配置
        QTimer.singleShot(100, self.load_config)
        
        # 添加延迟检查微信文件目录的逻辑
        QTimer.singleShot(1000, self.check_wechat_file_dir)
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = self.addToolBar("工具栏")
        toolbar.setMovable(False)
        
        # 更新联系人按钮
        self.update_contacts_action = QAction("更新联系人", self)
        self.update_contacts_action.triggered.connect(self.update_contacts)
        toolbar.addAction(self.update_contacts_action)
        
        # 更新群成员按钮
        self.update_members_action = QAction("更新群成员", self)
        self.update_members_action.triggered.connect(self.update_all_group_members)
        toolbar.addAction(self.update_members_action)
        
        # 诊断按钮
        diagnose_action = QAction("系统诊断", self)
        diagnose_action.triggered.connect(self.diagnose_system)
        toolbar.addAction(diagnose_action)
        
    def show_add_menu(self):
        """显示添加任务选择对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("选择任务类型")
        dialog.setMinimumWidth(600)
        
        # 创建水平布局
        layout = QHBoxLayout(dialog)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建三个大按钮
        # 1. 消息转发任务按钮
        transfer_btn = QPushButton("消息转发任务")
        transfer_btn.setMinimumHeight(100)
        transfer_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a86e8;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
        """)
        transfer_btn.clicked.connect(lambda: self.show_task_dialog("transfer", dialog))
        layout.addWidget(transfer_btn)
        
        # 2. 自动回复任务按钮
        reply_btn = QPushButton("自动回复任务")
        reply_btn.setMinimumHeight(100)
        reply_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #3c9f40;
            }
        """)
        reply_btn.clicked.connect(lambda: self.show_task_dialog("reply", dialog))
        layout.addWidget(reply_btn)
        
        # 3. 定时发送任务按钮
        schedule_btn = QPushButton("定时发送任务")
        schedule_btn.setMinimumHeight(100)
        schedule_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #e68a00;
            }
        """)
        schedule_btn.clicked.connect(lambda: self.show_task_dialog("schedule", dialog))
        layout.addWidget(schedule_btn)
        
        dialog.exec_()
        
    def show_task_dialog(self, task_type, parent_dialog=None):
        """显示任务对话框"""
        if parent_dialog:
            parent_dialog.close()
            
        if task_type == "transfer":
            self.add_transfer_task()
        elif task_type == "reply":
            self.add_reply_task()
        elif task_type == "schedule":
            self.add_scheduled_task()
        
    def add_transfer_task(self):
        """添加消息转发任务"""
        # 检查微信文件保存目录是否已设置
        if not self.wechat_file_dir or not os.path.exists(self.wechat_file_dir):
            # 显示警告并询问是否设置目录
            reply = QMessageBox.warning(
                self,
                "未设置微信文件目录",
                "转发任务需要处理微信文件，但微信文件目录未设置或不存在！\n\n"
                "必须先设置微信文件目录以启用文件转发功能。\n\n"
                "是否立即打开设置界面？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            # 如果用户选择设置目录
            if reply == QMessageBox.Yes:
                self.show_wechat_file_settings()
                return  # 不继续创建任务，等待用户设置完目录后再添加
            else:
                return  # 用户选择不设置，不继续创建任务
                
        # 继续创建转发任务
        dialog = TransferTaskDialog(self)
        dialog.update_contact_lists(self.groups, self.contacts)
        if dialog.exec_():
            task_config = dialog.get_config()
            try:
                # 直接添加到任务列表
                self.tasks.append(task_config)
                # 保存配置
                self.save_config()
                # 刷新任务列表
                self.refresh_task_list()
                self.statusBar().showMessage(f"已添加任务: {task_config['name']}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"添加任务失败: {str(e)}")
                
    def add_reply_task(self):
        """添加消息回复任务"""
        dialog = ReplyTaskDialog(self)
        dialog.update_contact_lists(self.groups, self.contacts)
        if dialog.exec_():
            task_config = dialog.get_config()
            try:
                # 直接添加到任务列表
                self.tasks.append(task_config)
                # 保存配置
                self.save_config()
                # 刷新任务列表
                self.refresh_task_list()
                self.statusBar().showMessage(f"已添加任务: {task_config['name']}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"添加任务失败: {str(e)}")
                
    def add_scheduled_task(self):
        """添加定时任务"""
        from gui.scheduled_task_dialog import ScheduledTaskDialog
        dialog = ScheduledTaskDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            config = dialog.get_config()
            self.task_manager.add_task(config)
            self.refresh_task_list()
        
    def update_contacts(self):
        """更新联系人和群组信息"""
        if self.is_updating_contacts:
            QMessageBox.warning(self, "警告", "正在更新联系人，请稍候...")
            return
        
        self.is_updating_contacts = True
        self.update_contacts_action.setEnabled(False)
        self.statusBar().showMessage("正在更新联系人和群组信息...")
        
        # 创建线程执行更新操作
        import threading
        update_thread = threading.Thread(target=self._update_contacts_thread)
        update_thread.daemon = True
        update_thread.start()
        
    def _update_contacts_thread(self):
        """线程中执行联系人更新操作"""
        try:
            # 调用robot的更新方法
            success = self.robot.update_contacts_and_groups()
            
            # 在主线程中更新UI
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            if success:
                # 更新完成后，同步本地数据
                self.groups = self.robot.allGroups
                self.contacts = self.robot.contacts
                
                # 使用正确的方式调用槽函数
                QMetaObject.invokeMethod(self, "_update_contacts_complete", 
                                       Qt.QueuedConnection)
            else:
                # 使用正确的方式调用带参数的槽函数
                QMetaObject.invokeMethod(self, "_update_contacts_failed",
                                      Qt.QueuedConnection,
                                      Q_ARG(str, "从微信获取联系人失败"))
        except Exception as e:
            print(f"更新联系人线程出错: {e}")
            import traceback
            traceback.print_exc()
            
            # 发送失败信号，使用正确的方式调用带参数的槽函数
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(self, "_update_contacts_failed",
                                  Qt.QueuedConnection,
                                  Q_ARG(str, str(e)))
        finally:
            # 确保标志被重置
            self.is_updating_contacts = False

    @pyqtSlot()
    def _update_contacts_complete(self):
        """联系人更新完成后的UI操作"""
        self.statusBar().showMessage("联系人和群组信息更新完成")
        self.update_contacts_action.setEnabled(True)
        self.is_updating_contacts = False
        
        # 弹出提示
        QMessageBox.information(self, "提示", f"联系人和群组信息更新完成\n共 {len(self.contacts)} 个联系人，{len(self.groups)} 个群组")

    @pyqtSlot(str)
    def _update_contacts_failed(self, error_msg):
        """联系人更新失败处理"""
        self.statusBar().showMessage(f"更新联系人和群组信息失败: {error_msg}")
        self.update_contacts_action.setEnabled(True)
        self.is_updating_contacts = False
        
        # 弹出错误提示
        QMessageBox.warning(self, "错误", f"更新联系人和群组信息失败:\n{error_msg}")

    def update_all_group_members(self):
        """更新所有群的成员列表"""
        if self.is_updating_contacts:
            QMessageBox.warning(self, "警告", "正在更新联系人，请稍候...")
            return
        
        self.is_updating_contacts = True
        self.update_members_action.setEnabled(False)
        self.statusBar().showMessage("正在更新群成员列表...")
        
        # 创建线程执行更新操作
        import threading
        update_thread = threading.Thread(target=self._update_members_thread)
        update_thread.daemon = True
        update_thread.start()
        
    def _update_members_thread(self):
        """线程中执行群成员更新操作"""
        try:
            # 调用robot的更新方法
            success = self.robot.update_group_members()
            
            # 在主线程中更新UI
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            if success:
                # 更新完成后，同步本地缓存
                self.group_members_cache = getattr(self.robot, 'group_members', {})
                
                # 使用正确的方式调用槽函数
                QMetaObject.invokeMethod(self, "_update_members_complete", 
                                       Qt.QueuedConnection)
            else:
                # 使用正确的方式调用带参数的槽函数
                QMetaObject.invokeMethod(self, "_update_members_failed",
                                      Qt.QueuedConnection,
                                      Q_ARG(str, "从微信获取群成员失败"))
        except Exception as e:
            print(f"更新群成员线程出错: {e}")
            import traceback
            traceback.print_exc()
            
            # 发送失败信号，使用正确的方式调用带参数的槽函数
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(self, "_update_members_failed",
                                  Qt.QueuedConnection,
                                  Q_ARG(str, str(e)))
        finally:
            # 确保标志被重置
            self.is_updating_contacts = False

    @pyqtSlot()
    def _update_members_complete(self):
        """群成员更新完成后的UI操作"""
        self.statusBar().showMessage("群成员列表更新完成")
        self.update_members_action.setEnabled(True)
        self.is_updating_contacts = False
        
        # 弹出提示
        total_groups = len(self.group_members_cache)
        QMessageBox.information(self, "提示", f"群成员列表更新完成\n已更新 {total_groups} 个群的成员信息")

    @pyqtSlot(str)
    def _update_members_failed(self, error_msg):
        """群成员更新失败处理"""
        self.statusBar().showMessage(f"更新群成员列表失败: {error_msg}")
        self.update_members_action.setEnabled(True)
        self.is_updating_contacts = False
        
        # 弹出错误提示
        QMessageBox.warning(self, "错误", f"更新群成员列表失败:\n{error_msg}")
        
    def import_config(self):
        """导入配置"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择配置文件", "", "JSON Files (*.json)")
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.tasks = json.load(f)
                self.save_config()
                self.refresh_task_list()
                self.statusBar().showMessage("配置导入成功")
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"导入配置失败: {str(e)}")
        
    def export_config(self):
        """导出配置"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存配置文件", "", "JSON Files (*.json)")
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.tasks, f, ensure_ascii=False, indent=2)
                self.statusBar().showMessage("配置导出成功")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"导出配置失败: {str(e)}")
        
    def refresh_task_list(self):
        """刷新任务列表"""
        try:
            # 清空任务列表
            self.task_list.setRowCount(0)
            
            # 添加任务到表格中
            for i, task in enumerate(self.tasks):
                self.task_list.insertRow(i)
                
                # 获取任务属性
                task_name = task.get("name", "未命名任务")
                task_type = task.get("type", "未知类型")
                source = task.get("source", "")
                target = task.get("target", "")
                time_str = task.get("time", "")
                task_status = task.get("status", "stopped")
                status_text = "运行中" if task_status == "running" else "已停止"
                
                # 设置单元格内容
                self.task_list.setItem(i, 0, QTableWidgetItem(task_name))
                self.task_list.setItem(i, 1, QTableWidgetItem(task_type))
                self.task_list.setItem(i, 2, QTableWidgetItem(source))
                self.task_list.setItem(i, 3, QTableWidgetItem(target))
                self.task_list.setItem(i, 4, QTableWidgetItem(time_str))
                self.task_list.setItem(i, 5, QTableWidgetItem(status_text))
                self.task_list.setItem(i, 6, QTableWidgetItem(""))
                
                # 设置操作按钮
                widget = QWidget()
                layout = QHBoxLayout(widget)
                layout.setContentsMargins(2, 2, 2, 2)
                
                toggle_btn = QPushButton("启动" if task_status != "running" else "停止")
                toggle_btn.clicked.connect(lambda _, task_name=task_name: self.toggle_task(task_name))
                
                edit_btn = QPushButton("编辑")
                edit_btn.clicked.connect(lambda _, task=task: self.edit_task(task))
                
                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda _, task=task: self.delete_task(task))
                
                layout.addWidget(toggle_btn)
                layout.addWidget(edit_btn)
                layout.addWidget(delete_btn)
                
                self.task_list.setCellWidget(i, 7, widget)
                
            # 确保根据任务状态刷新任务执行器中的任务
            if hasattr(self, 'task_executor'):
                self._sync_tasks_to_executor()
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"刷新任务列表失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _sync_tasks_to_executor(self):
        """同步任务到执行器，确保执行器中的任务状态与界面一致"""
        try:
            # 遍历所有任务
            for task in self.tasks:
                task_name = task.get("name", "")
                if not task_name:
                    continue
                    
                task_status = task.get("status", "stopped")
                
                # 如果任务应该运行但在执行器中不存在或已停止，则启动它
                if task_status == "running":
                    if hasattr(self.task_executor, 'is_task_running') and not self.task_executor.is_task_running(task_name):
                        print(f"任务 {task_name} 应该运行但未在执行器中运行，现在启动")
                        self.task_executor.start_task(task)
                # 如果任务应该停止但在执行器中运行，则停止它
                elif task_status == "stopped":
                    if hasattr(self.task_executor, 'is_task_running') and self.task_executor.is_task_running(task_name):
                        print(f"任务 {task_name} 应该停止但仍在执行器中运行，现在停止")
                        self.task_executor.stop_task(task_name)
        except Exception as e:
            print(f"同步任务到执行器时出错: {str(e)}")
            import traceback
            traceback.print_exc()
        
    def toggle_task(self, task_name):
        """启动或停止任务"""
        for task in self.tasks:
            if task["name"] == task_name:
                current_status = task.get("status", "stopped")
                new_status = "stopped" if current_status == "running" else "running"
                task["status"] = new_status
                is_running = new_status == "running"
                
                # 更新任务执行器中的任务状态
                if hasattr(self, 'task_executor'):
                    if task_name in self.task_executor.tasks:
                        # 使用toggle_task_status方法来切换任务状态
                        self.task_executor.toggle_task_status(task_name, is_running)
                    elif is_running:
                        # 如果任务不在task_executor中并且要启动，先启动它
                        self.task_executor.start_task(task)
                        
                # 保存配置
                self.save_config()
                
                # 刷新任务列表
                self.refresh_task_list()
                
                return True
        return False
        
    def edit_task(self, task):
        """编辑任务"""
        try:
            # 获取任务配置
            task_name = task["name"]
            task_config = None
            for t in self.tasks:
                if t["name"] == task_name:
                    task_config = t
                    break
                
            if not task_config:
                QMessageBox.warning(self, "警告", "任务不存在")
                return
            
            # 根据任务类型创建对应的对话框
            dialog = None
            if task_config.get("type") == "transfer":
                dialog = TransferTaskDialog(self, task_config)
            elif task_config.get("type") == "reply":
                dialog = ReplyTaskDialog(self, task_config)
            elif task_config.get("type") == "schedule":
                from gui.scheduled_task_dialog import ScheduledTaskDialog
                dialog = ScheduledTaskDialog(self, task_config)
                # 确保正确更新联系人列表
                dialog.update_contact_lists(self.groups, self.contacts)
            else:
                QMessageBox.warning(self, "警告", "不支持的任务类型")
                return
            
            # 显示对话框
            if dialog.exec_() == QDialog.Accepted:
                # 获取新的配置
                new_config = dialog.get_config()
                print(f"编辑任务 '{task_name}' 获取到新配置: {new_config}")
                # 更新任务
                self.update_task(task_name, new_config)
        except Exception as e:
            print(f"编辑任务失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"编辑任务失败: {str(e)}")
        
    def delete_task(self, task):
        """删除任务"""
        try:
            task_name = task["name"]
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除任务 '{task_name}' 吗？\n此操作将永久删除该任务。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 先停止任务（如果正在运行）
                if task.get("status") == "running" and hasattr(self, 'task_executor'):
                    try:
                        self.task_executor.stop_task(task_name)
                        print(f"已停止任务: {task_name}")
                    except Exception as e:
                        print(f"停止任务出错: {e}")
                        
                # 尝试从task_executor中删除任务（但不依赖其返回值）
                if hasattr(self, 'task_executor'):
                    try:
                        self.task_executor.delete_task(task_name)
                        print(f"已从task_executor中删除任务: {task_name}")
                    except Exception as e:
                        print(f"从task_executor删除任务出错: {e}")
                
                # 直接从任务列表中删除
                original_count = len(self.tasks)
                self.tasks = [t for t in self.tasks if t.get("name") != task_name]
                deleted_count = original_count - len(self.tasks)
                
                if deleted_count > 0:
                    print(f"从任务列表中删除了 {deleted_count} 个任务")
                    
                    # 保存配置文件
                    self.save_config()
                    
                    # 同步任务群组到配置
                    if hasattr(self, 'task_executor'):
                        self.task_executor.sync_task_groups_to_config()
                        print("已同步任务群组到配置")
                    
                    # 刷新界面
                    self.refresh_task_list()
                    
                    self.statusBar().showMessage(f"任务 '{task_name}' 已永久删除")
                else:
                    print(f"未找到要删除的任务: {task_name}")
                    QMessageBox.warning(self, "删除失败", f"未找到任务 '{task_name}'")
                
        except Exception as e:
            print(f"删除任务失败: {str(e)}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "操作失败", f"删除任务失败: {str(e)}")
        
    def save_config(self):
        """保存配置到文件"""
        try:
            # 获取当前所有任务的配置
            tasks_config = []
            
            # 首先添加任务列表中的任务
            for task in self.tasks:
                task_name = task.get("name")
                if task_name:  # 确保任务有名称
                    task_config = task.copy()
                    
                    # 确保last_state被正确设置
                    if "status" in task_config:
                        task_config["last_state"] = task_config.get("status") == "running"
                    
                    tasks_config.append(task_config)
            
            # 保存到文件
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "tasks.json")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(tasks_config, f, ensure_ascii=False, indent=2)
                
            print(f"配置已保存到: {config_path}")
            print(f"保存了 {len(tasks_config)} 个任务")
            
        except Exception as e:
            print(f"保存配置失败: {e}")
            import traceback
            print(traceback.format_exc())
        
    def normalize_tasks(self, tasks_list):
        """标准化任务配置，将使用群ID的转发任务转换为使用群名"""
        if not tasks_list:
            return []
        
        normalized_tasks = []
        conversion_count = 0
        
        for task in tasks_list:
            task_type = task.get("type")
            
            # 处理转发任务
            if task_type == "transfer":
                # 检查source是否为群ID
                source = task.get("source", "")
                source_type = task.get("source_type", "群聊")
                
                if source_type == "群聊" and "@chatroom" in source:
                    # 将群ID转换为群名
                    if source in self.robot.allGroups:
                        print(f"将来源群ID {source} 转换为群名: {self.robot.allGroups[source]}")
                        task["source"] = self.robot.allGroups[source]
                        conversion_count += 1
                    else:
                        print(f"警告: 找不到群ID {source} 对应的群名")
                
                # 检查target是否为群ID
                target = task.get("target", "")
                target_type = task.get("target_type", "群聊")
                
                if target_type == "群聊" and "@chatroom" in target:
                    # 将群ID转换为群名
                    if target in self.robot.allGroups:
                        print(f"将目标群ID {target} 转换为群名: {self.robot.allGroups[target]}")
                        task["target"] = self.robot.allGroups[target]
                        conversion_count += 1
                    else:
                        print(f"警告: 找不到群ID {target} 对应的群名")
            
            normalized_tasks.append(task)
        
        if conversion_count > 0:
            print(f"已规范化 {conversion_count} 个任务配置项")
            # 立即保存更新后的配置
            self.save_config()
        
        return normalized_tasks
    
    def load_config(self):
        """从配置文件加载任务"""
        try:
            # 获取配置文件路径
            config_path = os.path.join("config", "tasks.json")
            
            # 检查配置文件是否存在
            if not os.path.exists(config_path):
                # 创建空配置文件
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                self.statusBar().showMessage("创建新配置文件")
                self.tasks = []
                return
                
            # 加载配置文件
            with open(config_path, "r", encoding="utf-8") as f:
                self.tasks = json.load(f)
                
            # 标准化任务配置
            self.tasks = self.normalize_tasks(self.tasks)
            
            # 刷新任务列表
            self.refresh_task_list()
            
            # 启动所有运行中的任务
            if hasattr(self, 'task_executor'):
                for task in self.tasks:
                    if task.get("status") == "running":
                        self.task_executor.start_task(task)
                        
            print(f"从配置文件加载了 {len(self.tasks)} 个任务")
            self.statusBar().showMessage(f"已加载 {len(self.tasks)} 个任务")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载配置失败: {str(e)}")
            print(f"加载配置失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def create_timers(self):
        """创建定时器"""
        # 创建任务状态更新定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_task_list)
        self.timer.start(5000)  # 每5秒更新一次
        
        # 创建机器人任务执行定时器
        self.robot_job_timer = QTimer()
        self.robot_job_timer.timeout.connect(self.run_robot_jobs)
        self.robot_job_timer.start(1000)  # 每秒执行一次
        
    def create_menu(self):
        """创建菜单栏"""
        # 创建菜单栏
        menu_bar = self.menuBar()
        
        # 添加任务菜单（之前的文件菜单）
        task_menu = menu_bar.addMenu("添加任务")
        
        # 添加任务
        add_action = QAction("添加任务", self)
        add_action.triggered.connect(self.show_add_menu)
        task_menu.addAction(add_action)
        
        # 导入任务
        import_action = QAction("导入任务", self)
        import_action.triggered.connect(self.import_config)
        task_menu.addAction(import_action)
        
        # 导出任务
        export_action = QAction("导出任务", self)
        export_action.triggered.connect(self.export_config)
        task_menu.addAction(export_action)
        
        # 添加分隔线
        task_menu.addSeparator()
        
        # 微信文件设置（独立菜单项，直接添加到菜单栏）
        wechat_file_settings_action = QAction("文件目录设置", self)
        wechat_file_settings_action.triggered.connect(self.show_wechat_file_settings)
        menu_bar.addAction(wechat_file_settings_action)
        
        # 设置菜单（保留但移除AI设置）
        settings_menu = menu_bar.addMenu("设置")
        
        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        
        # 关于
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于",
            "微信机器人控制面板\n\n"
            "版本: 1.0.0\n"
            "作者: Your Name\n"
            "联系方式: your.email@example.com")
        
    def create_task_list(self):
        """创建任务列表"""
        # 创建表格
        self.task_list = QTableWidget(0, 8)  # 8列：任务名称、类型、源、目标、时间、状态、统计、操作
        self.task_list.setHorizontalHeaderLabels(["任务名称", "任务类型", "源", "目标", "时间", "状态", "统计", "操作"])
        self.task_list.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 5px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
        """)
        
        # 设置列宽
        header = self.task_list.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)  # 任务名称列自适应
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 任务类型列
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 源信息列
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 目标列
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 执行时间列
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 状态列
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 统计信息列
        header.setSectionResizeMode(7, QHeaderView.Fixed)  # 操作列
        header.resizeSection(7, 200)
        
        # 添加到主布局
        self.main_layout.addWidget(self.task_list)
        
    def on_task_started(self, task_name: str):
        """任务启动处理"""
        print(f"任务 '{task_name}' 已启动")
        self.statusBar().showMessage(f"任务 '{task_name}' 已启动")
        
    def on_task_stopped(self, task_name: str):
        """任务停止处理"""
        print(f"任务 '{task_name}' 已停止")
        self.statusBar().showMessage(f"任务 '{task_name}' 已停止")
        
    def on_task_error(self, task_name: str, error: str):
        """任务错误处理"""
        print(f"任务 '{task_name}' 发生错误: {error}")
        self.statusBar().showMessage(f"任务 '{task_name}' 发生错误: {error}")
        
    def on_task_status_changed(self, task_name: str, status: bool):
        """任务状态变化处理"""
        # 更新表格中的任务状态
        for row in range(self.task_list.rowCount()):
            if self.task_list.item(row, 0) and self.task_list.item(row, 0).text() == task_name:
                status_text = "运行中" if status else "已停止"
                if self.task_list.item(row, 5):
                    self.task_list.item(row, 5).setText(status_text)
                break
            
    def on_task_stats_updated(self, task_name: str, stats: Dict):
        """任务统计数据更新处理"""
        # 更新表格中的任务统计
        for row in range(self.task_list.rowCount()):
            if self.task_list.item(row, 0) and self.task_list.item(row, 0).text() == task_name:
                # 更新统计信息
                if "succeeded" in stats and self.task_list.item(row, 6):
                    self.task_list.item(row, 6).setText(f"成功: {stats['succeeded']}")
                break
            
    def update_task_status(self):
        """更新任务状态"""
        try:
            # 获取微信连接状态
            is_logged_in = self.robot.wcf.is_login()
            status_text = f"微信状态: {'已登录' if is_logged_in else '未登录'}"
            
            # 获取任务状态
            running_tasks = sum(1 for task in self.tasks if task.get("status", "stopped") == "running")
            status_text += f" | 运行中任务: {running_tasks}/{len(self.tasks)}"
            
            self.statusBar().showMessage(status_text)
        except Exception as e:
            self.statusBar().showMessage(f"更新任务状态失败: {str(e)}")
            print(f"更新任务状态失败: {str(e)}")
            
    def show_wechat_file_settings(self):
        """显示微信文件设置界面"""
        try:
            # 导入设置对话框
            from gui.wechat_file_settings import WeChatFileSettingsDialog
            
            # 创建并显示设置对话框
            dialog = WeChatFileSettingsDialog(self, self.wechat_file_dir)
            
            # 连接设置更新信号
            dialog.settings_updated.connect(self.update_wechat_file_dir)
            
            # 显示对话框
            dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开设置对话框失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def update_wechat_file_dir(self, new_dir):
        """更新微信文件目录"""
        try:
            self.wechat_file_dir = new_dir
            self.statusBar().showMessage(f"微信文件目录已更新为: {new_dir}")
            print(f"正在更新微信文件目录: {new_dir}")
            
            # 保存到配置
            if hasattr(self.robot, 'config'):
                print("找到robot.config对象")
                if not hasattr(self.robot.config, 'set'):
                    print("警告: robot.config没有set方法，尝试直接设置属性")
                    self.robot.config.WECHAT_FILES_DIR = new_dir
                else:
                    print("使用robot.config.set方法设置WECHAT_FILES_DIR")
                    success = self.robot.config.set("WECHAT_FILES_DIR", new_dir)
                    print(f"设置结果: {'成功' if success else '失败'}")
                
                if hasattr(self.robot.config, 'save'):
                    print("使用robot.config.save方法保存配置")
                    self.robot.config.save()
                else:
                    print("警告: robot.config没有save方法")
                
                # 如果robot.config有message_transfer属性，更新它
                if hasattr(self.robot, 'message_transfer'):
                    print("更新robot.message_transfer.wechat_files_dir")
                    self.robot.message_transfer.wechat_files_dir = new_dir
                    
                # 更新任务执行器的message_transfer
                if hasattr(self, 'task_executor') and hasattr(self.task_executor, 'message_transfer'):
                    print("更新task_executor.message_transfer.wechat_files_dir")
                    self.task_executor.message_transfer.wechat_files_dir = new_dir
                
                QMessageBox.information(self, "成功", f"微信文件目录已设置为:\n{new_dir}")
            else:
                print("错误: robot.config不可用")
                QMessageBox.warning(self, "警告", "无法保存配置，robot.config不可用")
        except Exception as e:
            print(f"更新微信文件目录失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "错误", f"更新微信文件目录失败: {str(e)}")
    
    @pyqtSlot()
    def show_wechat_file_settings_required(self):
        """当需要进行微信文件处理但目录未设置时调用此方法"""
        from PyQt5.QtWidgets import QMessageBox
        
        # 显示警告消息框
        reply = QMessageBox.warning(
            self,
            "需要设置微信文件目录",
            "检测到任务需要处理微信文件，但微信文件目录未设置或不存在！\n\n"
            "请先设置微信文件目录以启用文件转发功能。\n\n"
            "是否立即打开设置界面？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        # 如果用户点击了"是"，则打开微信文件设置
        if reply == QMessageBox.Yes:
            self.show_wechat_file_settings() 

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
        try:
            print("正在关闭程序...")
            self.statusBar().showMessage("正在关闭程序...")
            
            # 停止所有定时器
            print("正在停止定时器...")
            if hasattr(self, 'timer') and self.timer:
                self.timer.stop()
            if hasattr(self, 'robot_job_timer') and self.robot_job_timer:
                self.robot_job_timer.stop()
            
            # 停止所有任务
            print("正在停止所有任务...")
            if hasattr(self, 'task_executor') and self.task_executor:
                try:
                    self.task_executor.stop_all_tasks()
                except Exception as e:
                    print(f"停止任务时出错: {e}")
            
            # 保存配置
            print("正在保存配置...")
            self.statusBar().showMessage("正在保存配置...")
            try:
                self.save_config()
            except Exception as e:
                print(f"保存配置时出错: {e}")
            
            # 使用Robot的统一清理方法进行资源清理
            print("正在清理机器人资源...")
            if hasattr(self, 'robot') and hasattr(self.robot, 'cleanup'):
                self.statusBar().showMessage("正在清理机器人资源...")
                try:
                    # 在线程中执行cleanup，设置超时
                    import threading
                    import time
                    
                    cleanup_done = threading.Event()
                    def do_cleanup():
                        try:
                            self.robot.cleanup()
                            cleanup_done.set()
                        except Exception as e:
                            print(f"机器人资源清理出错: {e}")
                            cleanup_done.set()
                    
                    # 启动清理线程
                    cleanup_thread = threading.Thread(target=do_cleanup)
                    cleanup_thread.daemon = True
                    cleanup_thread.start()
                    
                    # 等待清理完成，最多等待1.5秒
                    start_time = time.time()
                    if not cleanup_done.wait(1.5):
                        print("警告: 机器人资源清理超时，继续关闭流程")
                    else:
                        print(f"机器人资源清理完成，耗时: {time.time() - start_time:.2f}秒")
                except Exception as e:
                    print(f"调用机器人清理方法时出错: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("警告: 找不到robot.cleanup()方法")
            
            # 确保垃圾回收执行
            print("正在执行垃圾回收...")
            import gc
            gc.collect()
            
            print("程序已完成所有清理工作，即将退出")
            event.accept()
        except Exception as e:
            print(f"关闭窗口时出错: {e}")
            import traceback
            traceback.print_exc()
            
            # 即使出错也接受关闭事件
            print("由于错误强制退出")
            event.accept()  # 即使出错也强制接受关闭事件

    def run_robot_jobs(self):
        """运行机器人待处理的任务，替代keepRunningAndBlockProcess()"""
        try:
            # 注释掉对robot.runPendingJobs的调用，因为MessageScheduler已经有一个专门的线程在执行定时任务
            # 两者同时调用会导致任务被执行两次
            # self.robot.runPendingJobs()
            
            # 使用缓存保存上次的统计信息，避免重复输出
            if not hasattr(self, '_last_task_stats'):
                self._last_task_stats = {}
                
            # 定期检查任务统计信息是否正确
            if hasattr(self, 'task_executor') and hasattr(self.task_executor, 'tasks'):
                for task_name in self.task_executor.tasks:
                    stats = self.task_executor.get_task_stats(task_name)
                    if stats and stats.get('succeeded', 0) > 0:
                        # 只在统计信息发生变化时输出
                        last_stats = self._last_task_stats.get(task_name, {})
                        if (stats.get('processed', 0) != last_stats.get('processed', 0) or 
                            stats.get('succeeded', 0) != last_stats.get('succeeded', 0) or 
                            stats.get('failed', 0) != last_stats.get('failed', 0)):
                            print(f"任务 {task_name} 统计信息: {stats}")
                            # 更新缓存
                            self._last_task_stats[task_name] = stats.copy()
                        
            pass  # 保留方法，但不执行任何操作
        except Exception as e:
            print(f"运行机器人任务失败: {e}")
            import traceback
            traceback.print_exc()

    def get_task_config(self, task_id: str) -> dict:
        """获取任务配置"""
        for task in self.tasks:
            if task.get("name") == task_id:
                return task.copy()
        return None

    def update_task(self, task_name, updated_task):
        """更新任务配置"""
        try:
            # 查找任务索引
            task_index = None
            for i, task in enumerate(self.tasks):
                if task.get("name") == task_name:
                    task_index = i
                    break
            
            if task_index is not None:
                # 更新任务配置
                self.tasks[task_index] = updated_task
                
                # 保存配置
                self.save_config()
                
                # 同步任务群组到配置
                if hasattr(self, 'task_executor'):
                    self.task_executor.sync_task_groups_to_config()
                    print("已同步任务群组到配置")
                
                # 刷新任务列表
                self.refresh_task_list()
                
                # 如果存在任务执行器，更新相应任务
                if hasattr(self, 'task_executor'):
                    try:
                        self.task_executor.update_task(task_name, updated_task)
                        print(f"已更新任务执行器中的任务: {task_name}")
                    except Exception as e:
                        print(f"更新任务执行器中的任务出错: {e}")
                
                return True
            else:
                print(f"未找到要更新的任务: {task_name}")
                return False
                
        except Exception as e:
            print(f"更新任务配置失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def update_group_list(self):
        """更新群聊列表"""
        try:
            # 获取群聊列表
            groups = self.wcf.get_chatroom_list()
            # 更新群聊字典
            self.groups = {}
            for group_id in groups:
                try:
                    group_name = self.wcf.get_chatroom_name(group_id)
                    if group_name:
                        self.groups[group_name] = group_id
                except Exception as e:
                    print(f"获取群名称失败: {str(e)}")
                    
            # 更新任务执行器的群聊列表
            if hasattr(self, 'task_executor'):
                self.task_executor.update_groups(self.groups)
                
            return True
        except Exception as e:
            print(f"更新群聊列表失败: {str(e)}")
            return False 

    def add_task(self, config):
        """添加任务到任务列表并保存配置
        
        Args:
            config: 任务配置字典
            
        Returns:
            bool: 是否成功添加任务
        """
        try:
            # 添加到任务列表
            self.tasks.append(config)
            
            # 保存配置
            self.save_config()
            
            # 同步任务群组到配置
            if hasattr(self, 'task_executor'):
                self.task_executor.sync_task_groups_to_config()
                
            # 如果任务状态为运行，则启动任务
            if config.get("status") == "running":
                self.task_executor.start_task(config)
                
            # 刷新任务列表
            self.refresh_task_list()
            
            self.statusBar().showMessage(f"已添加任务: {config['name']}")
            return True
        except Exception as e:
            QMessageBox.warning(self, "错误", f"添加任务失败: {str(e)}")
            return False 

    def update_task_group_members(self, task):
        """更新指定任务的群成员列表，保留方法兼容旧代码"""
        try:
            group_name = task.get("source", "")
            if not group_name:
                return
            
            # 找到群ID
            group_id = None
            for wxid, name in self.robot.allGroups.items():
                if name == group_name:
                    group_id = wxid
                    break
                
            if not group_id:
                self.statusBar().showMessage(f"未找到群 '{group_name}' 的ID")
                return
            
            # 调用robot的方法更新指定群的成员
            self.statusBar().showMessage(f"正在更新群 '{group_name}' 的成员列表...")
            
            # 使用线程执行更新
            import threading
            update_thread = threading.Thread(
                target=lambda: self._update_single_group_thread(group_id, group_name))
            update_thread.daemon = True
            update_thread.start()
        except Exception as e:
            self.statusBar().showMessage(f"更新群成员列表失败: {str(e)}")
            print(f"更新群成员列表失败: {str(e)}")
        
    def _update_single_group_thread(self, group_id, group_name):
        """线程中执行单个群成员更新操作"""
        try:
            # 调用robot的更新方法
            success = self.robot.update_group_members(group_id)
            
            # 在主线程中更新UI
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            if success:
                # 更新完成后，同步本地缓存
                self.group_members_cache = getattr(self.robot, 'group_members', {})
                
                # 使用正确的方式调用槽函数
                QMetaObject.invokeMethod(self, "_update_single_group_complete", 
                                       Qt.QueuedConnection,
                                       Q_ARG(str, group_name))
            else:
                # 使用正确的方式调用带参数的槽函数
                QMetaObject.invokeMethod(self, "_update_single_group_failed",
                                      Qt.QueuedConnection,
                                      Q_ARG(str, f"更新群 '{group_name}' 成员失败"))
        except Exception as e:
            print(f"更新群 '{group_name}' 成员线程出错: {e}")
            import traceback
            traceback.print_exc()
            
            # 发送失败信号，使用正确的方式调用带参数的槽函数
            from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
            QMetaObject.invokeMethod(self, "_update_single_group_failed",
                                  Qt.QueuedConnection,
                                  Q_ARG(str, str(e)))
        finally:
            # 确保标志被重置
            self.is_updating_contacts = False

    @pyqtSlot(str)
    def _update_single_group_complete(self, group_name):
        """单个群成员更新完成后的UI操作"""
        self.statusBar().showMessage(f"群 '{group_name}' 的成员列表更新完成")
        
    @pyqtSlot(str)
    def _update_single_group_failed(self, error_msg):
        """单个群成员更新失败处理"""
        self.statusBar().showMessage(f"更新群成员列表失败: {error_msg}")
        
    def update_member_list(self, group_name):
        """更新群成员下拉列表 - 兼容方法"""
        # 此方法仅为兼容旧代码，现在应该由任务对话框直接从robot.group_members获取数据
        print("update_member_list方法已弃用，任务对话框应直接从robot.group_members获取数据") 

    def _init_task_executor(self):
        """初始化任务执行器"""
        try:
            # 创建任务执行器
            self.task_executor = TaskExecutor(self.robot)
            
            # 将任务执行器设置为robot的属性，确保robot.processMsg可以使用它
            self.robot.task_executor = self.task_executor
            
            # 连接信号
            self.task_executor.task_started.connect(self.on_task_started)
            self.task_executor.task_stopped.connect(self.on_task_stopped)
            self.task_executor.task_error.connect(self.on_task_error)
            self.task_executor.status_changed.connect(self.on_task_status_changed)
            self.task_executor.stats_updated.connect(self.on_task_stats_updated)
            
            # 设置task_executor的parent为当前窗口
            self.task_executor.setParent(self)
            
            # 同步微信文件目录到message_transfer
            if hasattr(self, 'wechat_file_dir') and self.wechat_file_dir and hasattr(self.task_executor, 'message_transfer'):
                self.task_executor.message_transfer.wechat_files_dir = self.wechat_file_dir
            
            # 加载已保存的任务
            self.task_executor.load_tasks()
            
            # 同步任务群组到配置
            self.task_executor.sync_task_groups_to_config()
            
            # 同步任务到执行器
            self._sync_tasks_to_executor()
            
            print("任务执行器初始化成功，已设置为robot的属性")
            
            return True
        except Exception as e:
            QMessageBox.critical(self, "错误", f"初始化任务执行器失败: {str(e)}")
            print(f"初始化任务执行器失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def check_wechat_file_dir(self):
        """检查微信文件目录是否已设置，如未设置则提示用户"""
        if not self.wechat_file_dir or not os.path.exists(self.wechat_file_dir):
            print("检测到微信文件目录未设置，将显示设置对话框")
            self.show_wechat_file_settings_required() 