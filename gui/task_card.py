from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QFrame, QMenu, QApplication, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QMimeData, QPoint
from PyQt5.QtGui import QColor, QDrag, QFont
from typing import Dict
import os

class TaskCard(QFrame):
    # 定义信号
    start_task_signal = pyqtSignal(str)  # task_name
    stop_task_signal = pyqtSignal(str)   # task_name
    edit_task_signal = pyqtSignal(str)   # task_name
    delete_task_signal = pyqtSignal(str) # task_name
    move_task_signal = pyqtSignal(str, int)  # task_name, new_index
    
    def __init__(self, task_config: Dict, parent=None):
        super().__init__(parent)
        self.task_config = task_config
        self.task_name = task_config["name"]
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        
        # 设置样式
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #d0d0d0;
                padding: 5px;
            }
            QLabel {
                font-size: 12px;
            }
            QPushButton {
                font-size: 12px;
                padding: 5px 10px;
                border-radius: 4px;
                border: 1px solid #c0c0c0;
                background-color: #f0f0f0;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        
        # 允许拖放
        self.setAcceptDrops(True)
        
        # 设置鼠标样式
        self.setCursor(Qt.OpenHandCursor)
        
        # 设置UI
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI布局"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题和状态
        header_layout = QHBoxLayout()
        
        # 任务名称
        self.name_label = QLabel(self.task_name)
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        self.name_label.setFont(font)
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        header_layout.addWidget(self.name_label)
        
        # 状态标签
        self.status_label = QLabel("状态: " + self.task_config.get("status", "停止"))
        self.status_label.setStyleSheet("""
            font-size: 12px;
            padding: 2px 8px;
            border-radius: 10px;
            background-color: #f2f2f2;
        """)
        header_layout.addWidget(self.status_label)
        
        main_layout.addLayout(header_layout)
        
        # 任务信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        
        # 任务类型
        task_type = self.task_config.get("type", "")
        type_text = ""
        
        if task_type == "transfer":
            type_text = "消息转发任务"
            source = self.task_config.get("source", "")
            target = self.task_config.get("target", "")
            info_text = f"转发来源: {source} ➔ 转发目标: {target}"
        elif task_type == "reply":
            type_text = "消息回复任务"
            source = self.task_config.get("reply_group", "")
            info_text = f"监听群组: {source}"
        elif task_type == "schedule":
            type_text = "定时消息任务"
            time = self.task_config.get("send_time", "")
            target = self.task_config.get("target", "")
            repeat = self.task_config.get("repeat_type", "一次")
            info_text = f"发送时间: {time} | 重复: {repeat} | 目标: {target}"
        else:
            info_text = "未知任务类型"
            
        # 任务类型标签
        self.type_label = QLabel(type_text)
        self.type_label.setStyleSheet("""
            font-size: 12px;
            font-weight: bold;
            color: #505050;
            margin-top: 5px;
        """)
        info_layout.addWidget(self.type_label)
        
        # 任务详情
        self.info_label = QLabel(info_text)
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-size: 12px; color: #606060;")
        info_layout.addWidget(self.info_label)
        
        # 添加统计信息
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        self.processed_label = QLabel("处理消息: 0")
        self.processed_label.setStyleSheet("font-size: 12px; color: #606060;")
        stats_layout.addWidget(self.processed_label)
        
        self.succeeded_label = QLabel("成功: 0")
        self.succeeded_label.setStyleSheet("font-size: 12px; color: #008000;")
        stats_layout.addWidget(self.succeeded_label)
        
        self.failed_label = QLabel("失败: 0")
        self.failed_label.setStyleSheet("font-size: 12px; color: #D00000;")
        stats_layout.addWidget(self.failed_label)
        
        stats_layout.addStretch()
        info_layout.addLayout(stats_layout)
        
        main_layout.addLayout(info_layout)
        
        # 按钮组
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 启动/停止按钮
        self.toggle_button = QPushButton("启动")
        self.toggle_button.clicked.connect(self.toggle_task)
        button_layout.addWidget(self.toggle_button)
        
        # 编辑按钮
        self.edit_button = QPushButton("编辑")
        self.edit_button.clicked.connect(self.edit_task)
        button_layout.addWidget(self.edit_button)
        
        # 删除按钮
        self.delete_button = QPushButton("删除")
        self.delete_button.clicked.connect(self.delete_task)
        button_layout.addWidget(self.delete_button)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # 更新状态
        self.update_status(self.task_config.get("status", "stopped"))
        
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if not (event.buttons() & Qt.LeftButton):
            return
            
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        # 创建拖拽数据
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.task_name)
        drag.setMimeData(mime_data)
        
        # 执行拖拽
        drag.exec_(Qt.MoveAction)
        
    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        """拖拽放下事件"""
        source_name = event.mimeData().text()
        target_name = self.task_name
        
        if source_name != target_name:
            # 获取当前索引
            current_index = self.parent().task_layout.indexOf(self)
            
            # 发送移动信号
            self.move_task_signal.emit(source_name, current_index)
            
        event.acceptProposedAction()
        
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self.setCursor(Qt.OpenHandCursor)
        
    def toggle_task(self):
        """切换任务状态"""
        status = self.task_config.get("status", "stopped")
        if status == "running":
            self.stop_task_signal.emit(self.task_name)
        else:
            self.start_task_signal.emit(self.task_name)
            
    def edit_task(self):
        """编辑任务"""
        self.edit_task_signal.emit(self.task_name)
        
    def delete_task(self):
        """删除任务"""
        self.delete_task_signal.emit(self.task_name)
        
    def update_status(self, status: str):
        """更新任务状态"""
        self.task_config["status"] = status
        
        if status == "running":
            self.status_label.setText("状态: 运行中")
            self.status_label.setStyleSheet("""
                font-size: 12px;
                padding: 2px 8px;
                border-radius: 10px;
                background-color: #d4edda;
                color: #155724;
            """)
            self.toggle_button.setText("停止")
        else:
            self.status_label.setText("状态: 已停止")
            self.status_label.setStyleSheet("""
                font-size: 12px;
                padding: 2px 8px;
                border-radius: 10px;
                background-color: #f8d7da;
                color: #721c24;
            """)
            self.toggle_button.setText("启动")
        
    def update_stats(self, stats: Dict):
        """更新统计信息"""
        processed = stats.get("processed", 0)
        succeeded = stats.get("succeeded", 0)
        failed = stats.get("failed", 0)
        
        self.processed_label.setText(f"处理消息: {processed}")
        self.succeeded_label.setText(f"成功: {succeeded}")
        self.failed_label.setText(f"失败: {failed}")
        
    def is_running(self) -> bool:
        """检查任务是否在运行中"""
        return self.task_config.get("status", "stopped") == "running"

    def update_contact_lists(self, groups: dict, friends: dict):
        """更新联系人列表"""
        # 更新详情显示
        if self.task_config["type"] == "消息转发任务":
            if self.task_config["source_group"] not in groups:
                self.task_config["source_group"] = "未知群聊"
            if self.task_config["target"] not in groups and self.task_config["target"] not in friends:
                self.task_config["target"] = "未知目标"
            if self.task_config["member"] != "全部" and self.task_config["member"] not in friends:
                self.task_config["member"] = "未知成员"
                
        elif self.task_config["type"] == "消息回复任务":
            if self.task_config["reply_group"] not in groups:
                self.task_config["reply_group"] = "未知群聊"
            if self.task_config["reply_member"] != "全部" and self.task_config["reply_member"] not in friends:
                self.task_config["reply_member"] = "未知成员"
                
        elif self.task_config["type"] == "定时消息任务":
            if self.task_config["timer_target"] not in groups and self.task_config["timer_target"] not in friends:
                self.task_config["timer_target"] = "未知目标"
                
        # 重新设置界面
        self.setup_ui() 