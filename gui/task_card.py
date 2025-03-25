from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor
from typing import Dict
import os

class TaskCard(QFrame):
    # 定义信号
    start_task_signal = pyqtSignal(str)  # task_name
    stop_task_signal = pyqtSignal(str)   # task_name
    edit_task_signal = pyqtSignal(str)   # task_name
    clone_task_signal = pyqtSignal(str)  # task_name
    
    def __init__(self, task_config: Dict, parent=None):
        super().__init__(parent)
        self.task_config = task_config
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI布局"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(1)
        
        layout = QVBoxLayout(self)
        
        # 任务名称和状态
        header_layout = QHBoxLayout()
        self.name_label = QLabel(self.task_config["name"])
        self.name_label.setStyleSheet("font-weight: bold;")
        self.status_label = QLabel(self.task_config.get("status", "stopped"))
        self.status_label.setStyleSheet("color: red;" if self.status_label.text() == "stopped" else "color: green;")
        header_layout.addWidget(self.name_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        layout.addLayout(header_layout)
        
        # 任务类型
        type_label = QLabel(f"类型: {self.task_config['type']}")
        layout.addWidget(type_label)
        
        # 任务配置信息
        info_layout = QVBoxLayout()
        task_type = self.task_config["type"]
        
        if task_type == "消息转发任务":
            info_layout.addWidget(QLabel(f"源群组: {self.task_config.get('source_group', '')}"))
            if self.task_config.get('member', '') != '全部':
                info_layout.addWidget(QLabel(f"成员: {self.task_config.get('member', '全部')}"))
            
            match_type = self.task_config.get('match_type', '')
            match_content = self.task_config.get('match_content', '')
            if match_type == "文件类型":
                info_layout.addWidget(QLabel(f"文件类型: {self.task_config.get('file_type', '')}"))
            else:
                info_layout.addWidget(QLabel(f"匹配条件: {match_type} {match_content}"))
                
            info_layout.addWidget(QLabel(f"转发目标: {self.task_config.get('target', '')}"))
            
        elif task_type == "消息回复任务":
            info_layout.addWidget(QLabel(f"群组: {self.task_config.get('reply_group', '')}"))
            if self.task_config.get('reply_member', '') != '全部':
                info_layout.addWidget(QLabel(f"成员: {self.task_config.get('reply_member', '全部')}"))
                
            reply_match_type = self.task_config.get('reply_match_type', '')
            reply_match_content = self.task_config.get('reply_match_content', '')
            info_layout.addWidget(QLabel(f"匹配条件: {reply_match_type} {reply_match_content}"))
            
            reply_content = self.task_config.get('reply_content', '')
            if len(reply_content) > 20:
                reply_content = reply_content[:20] + "..."
            info_layout.addWidget(QLabel(f"回复内容: {reply_content}"))
            info_layout.addWidget(QLabel(f"回复方式: {self.task_config.get('reply_type', '文本')}"))
            
        elif task_type == "定时消息任务":
            info_layout.addWidget(QLabel(f"发送时间: {self.task_config.get('send_time', '')}"))
            info_layout.addWidget(QLabel(f"重复方式: {self.task_config.get('repeat_type', '')}"))
            info_layout.addWidget(QLabel(f"发送目标: {self.task_config.get('timer_target', '')}"))
            
            content = self.task_config.get('content', '')
            if len(content) > 20:
                content = content[:20] + "..."
            info_layout.addWidget(QLabel(f"消息内容: {content}"))
            info_layout.addWidget(QLabel(f"消息类型: {self.task_config.get('content_type', '文本')}"))
            
            attachment = self.task_config.get('attachment', '')
            if attachment:
                attachment_short = os.path.basename(attachment)
                info_layout.addWidget(QLabel(f"附件: {attachment_short}"))
        
        layout.addLayout(info_layout)
        
        # 统计信息
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("处理: 0 | 成功: 0 | 失败: 0")
        stats_layout.addWidget(self.stats_label)
        layout.addLayout(stats_layout)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        # 启动/停止按钮
        self.start_stop_btn = QPushButton("启动" if self.status_label.text() == "stopped" else "停止")
        self.start_stop_btn.clicked.connect(self.toggle_task)
        button_layout.addWidget(self.start_stop_btn)
        
        # 编辑按钮
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(lambda: self.edit_task_signal.emit(self.task_config["name"]))
        button_layout.addWidget(edit_btn)
        
        # 克隆按钮
        clone_btn = QPushButton("克隆")
        clone_btn.clicked.connect(lambda: self.clone_task_signal.emit(self.task_config["name"]))
        button_layout.addWidget(clone_btn)
        
        layout.addLayout(button_layout)
        
    def toggle_task(self):
        """切换任务状态"""
        if self.status_label.text() == "stopped":
            self.start_task_signal.emit(self.task_config["name"])
        else:
            self.stop_task_signal.emit(self.task_config["name"])
            
    def update_status(self, status: str):
        """更新任务状态"""
        self.status_label.setText(status)
        self.status_label.setStyleSheet("color: red;" if status == "stopped" else "color: green;")
        self.start_stop_btn.setText("启动" if status == "stopped" else "停止")
        
    def update_stats(self, stats: Dict):
        """更新统计信息"""
        self.stats_label.setText(
            f"处理: {stats.get('processed', 0)} | "
            f"成功: {stats.get('succeeded', 0)} | "
            f"失败: {stats.get('failed', 0)}"
        )
        
    def is_running(self) -> bool:
        """检查任务是否在运行中"""
        return self.status_label.text() != "stopped"

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