from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QPushButton, QTextEdit,
                             QGroupBox, QRadioButton, QFileDialog, QScrollArea,
                             QFrame, QWidget)
from PyQt5.QtCore import Qt
from typing import Dict, Optional

class TaskDialog(QDialog):
    def __init__(self, parent=None, task_config: Optional[Dict] = None):
        super().__init__(parent)
        self.task_config = task_config or {}
        self.setup_ui()
        
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("任务配置")
        self.setMinimumWidth(600)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        # 创建内容布局
        content_layout = QVBoxLayout()
        
        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QVBoxLayout()
        
        # 任务名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("任务名称:"))
        self.name_edit = QLineEdit(self.task_config.get("name", ""))
        name_layout.addWidget(self.name_edit)
        basic_layout.addLayout(name_layout)
        
        # 任务类型
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("任务类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["消息转发任务", "消息回复任务", "定时消息任务"])
        if "type" in self.task_config:
            self.type_combo.setCurrentText(self.task_config["type"])
        type_layout.addWidget(self.type_combo)
        basic_layout.addLayout(type_layout)
        
        basic_group.setLayout(basic_layout)
        content_layout.addWidget(basic_group)
        
        # 转发任务配置组
        self.forward_group = QGroupBox("转发配置")
        forward_layout = QVBoxLayout()
        
        # 源群聊
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("源群聊:"))
        self.source_combo = QComboBox()
        source_layout.addWidget(self.source_combo)
        forward_layout.addLayout(source_layout)
        
        # 成员
        member_layout = QHBoxLayout()
        member_layout.addWidget(QLabel("成员:"))
        self.member_combo = QComboBox()
        self.member_combo.addItem("全部")
        member_layout.addWidget(self.member_combo)
        forward_layout.addLayout(member_layout)
        
        # 消息匹配条件
        match_layout = QHBoxLayout()
        match_layout.addWidget(QLabel("匹配条件:"))
        self.match_type_combo = QComboBox()
        self.match_type_combo.addItems(["包含", "等于", "正则", "文件类型"])
        match_layout.addWidget(self.match_type_combo)
        self.match_content_edit = QLineEdit()
        match_layout.addWidget(self.match_content_edit)
        forward_layout.addLayout(match_layout)
        
        # 文件类型
        file_type_layout = QHBoxLayout()
        file_type_layout.addWidget(QLabel("文件类型:"))
        self.file_type_combo = QComboBox()
        self.file_type_combo.addItems(["图片", "文件", "视频"])
        file_type_layout.addWidget(self.file_type_combo)
        forward_layout.addLayout(file_type_layout)
        
        # 转发目标
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("转发目标:"))
        self.target_combo = QComboBox()
        target_layout.addWidget(self.target_combo)
        forward_layout.addLayout(target_layout)
        
        self.forward_group.setLayout(forward_layout)
        content_layout.addWidget(self.forward_group)
        
        # 回复任务配置组
        self.reply_group = QGroupBox("回复配置")
        reply_layout = QVBoxLayout()
        
        # 群聊
        reply_group_layout = QHBoxLayout()
        reply_group_layout.addWidget(QLabel("群聊:"))
        self.reply_group_combo = QComboBox()
        reply_group_layout.addWidget(self.reply_group_combo)
        reply_layout.addLayout(reply_group_layout)
        
        # 成员
        reply_member_layout = QHBoxLayout()
        reply_member_layout.addWidget(QLabel("成员:"))
        self.reply_member_combo = QComboBox()
        self.reply_member_combo.addItem("全部")
        reply_member_layout.addWidget(self.reply_member_combo)
        reply_layout.addLayout(reply_member_layout)
        
        # 消息匹配条件
        reply_match_layout = QHBoxLayout()
        reply_match_layout.addWidget(QLabel("匹配条件:"))
        self.reply_match_type_combo = QComboBox()
        self.reply_match_type_combo.addItems(["包含", "等于", "正则"])
        reply_match_layout.addWidget(self.reply_match_type_combo)
        self.reply_match_content_edit = QLineEdit()
        reply_match_layout.addWidget(self.reply_match_content_edit)
        reply_layout.addLayout(reply_match_layout)
        
        # 回复内容
        reply_content_layout = QHBoxLayout()
        reply_content_layout.addWidget(QLabel("回复内容:"))
        self.reply_content_edit = QTextEdit()
        self.reply_content_edit.setMaximumHeight(100)
        reply_content_layout.addWidget(self.reply_content_edit)
        reply_layout.addLayout(reply_content_layout)
        
        # 回复方式
        reply_type_layout = QHBoxLayout()
        reply_type_layout.addWidget(QLabel("回复方式:"))
        self.reply_type_combo = QComboBox()
        self.reply_type_combo.addItems(["文本", "图片"])
        reply_type_layout.addWidget(self.reply_type_combo)
        reply_layout.addLayout(reply_type_layout)
        
        self.reply_group.setLayout(reply_layout)
        content_layout.addWidget(self.reply_group)
        
        # 定时任务配置组
        self.timer_group = QGroupBox("定时配置")
        timer_layout = QVBoxLayout()
        
        # 发送时间
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("发送时间:"))
        self.time_edit = QLineEdit()
        self.time_edit.setPlaceholderText("HH:MM")
        time_layout.addWidget(self.time_edit)
        timer_layout.addLayout(time_layout)
        
        # 重复方式
        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(QLabel("重复方式:"))
        self.repeat_combo = QComboBox()
        self.repeat_combo.addItems(["每天", "每周", "每月", "仅一次"])
        repeat_layout.addWidget(self.repeat_combo)
        timer_layout.addLayout(repeat_layout)
        
        # 发送目标
        timer_target_layout = QHBoxLayout()
        timer_target_layout.addWidget(QLabel("发送目标:"))
        self.timer_target_combo = QComboBox()
        timer_target_layout.addWidget(self.timer_target_combo)
        timer_layout.addLayout(timer_target_layout)
        
        # 消息内容
        timer_content_layout = QHBoxLayout()
        timer_content_layout.addWidget(QLabel("消息内容:"))
        self.timer_content_edit = QTextEdit()
        self.timer_content_edit.setMaximumHeight(100)
        timer_content_layout.addWidget(self.timer_content_edit)
        timer_layout.addLayout(timer_content_layout)
        
        # 消息类型
        timer_type_layout = QHBoxLayout()
        timer_type_layout.addWidget(QLabel("消息类型:"))
        self.timer_type_combo = QComboBox()
        self.timer_type_combo.addItems(["文本", "图片", "文件"])
        timer_type_layout.addWidget(self.timer_type_combo)
        timer_layout.addLayout(timer_type_layout)
        
        # 附件选择
        attachment_layout = QHBoxLayout()
        self.attachment_btn = QPushButton("选择附件")
        self.attachment_btn.clicked.connect(self.select_attachment)
        attachment_layout.addWidget(self.attachment_btn)
        self.attachment_label = QLabel("")
        attachment_layout.addWidget(self.attachment_label)
        timer_layout.addLayout(attachment_layout)
        
        self.timer_group.setLayout(timer_layout)
        content_layout.addWidget(self.timer_group)
        
        # 设置滚动区域的内容
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 连接信号
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        
        # 初始化界面状态
        self.on_type_changed(self.type_combo.currentText())
        
        # 加载配置
        self.load_config()
        
    def load_config(self):
        """加载配置"""
        if not self.task_config:
            return
            
        # 基本信息
        self.name_edit.setText(self.task_config.get("name", ""))
        self.type_combo.setCurrentText(self.task_config.get("type", "消息转发任务"))
        
        # 转发任务配置
        if "source_group" in self.task_config:
            self.source_combo.setCurrentText(self.task_config["source_group"])
        if "member" in self.task_config:
            self.member_combo.setCurrentText(self.task_config["member"])
        if "match_type" in self.task_config:
            self.match_type_combo.setCurrentText(self.task_config["match_type"])
        if "match_content" in self.task_config:
            self.match_content_edit.setText(self.task_config["match_content"])
        if "file_type" in self.task_config:
            self.file_type_combo.setCurrentText(self.task_config["file_type"])
        if "target" in self.task_config:
            self.target_combo.setCurrentText(self.task_config["target"])
            
        # 回复任务配置
        if "reply_group" in self.task_config:
            self.reply_group_combo.setCurrentText(self.task_config["reply_group"])
        if "reply_member" in self.task_config:
            self.reply_member_combo.setCurrentText(self.task_config["reply_member"])
        if "reply_match_type" in self.task_config:
            self.reply_match_type_combo.setCurrentText(self.task_config["reply_match_type"])
        if "reply_match_content" in self.task_config:
            self.reply_match_content_edit.setText(self.task_config["reply_match_content"])
        if "reply_content" in self.task_config:
            self.reply_content_edit.setText(self.task_config["reply_content"])
        if "reply_type" in self.task_config:
            self.reply_type_combo.setCurrentText(self.task_config["reply_type"])
            
        # 定时任务配置
        if "send_time" in self.task_config:
            self.time_edit.setText(self.task_config["send_time"])
        if "repeat_type" in self.task_config:
            self.repeat_combo.setCurrentText(self.task_config["repeat_type"])
        if "timer_target" in self.task_config:
            self.timer_target_combo.setCurrentText(self.task_config["timer_target"])
        if "content" in self.task_config:
            self.timer_content_edit.setText(self.task_config["content"])
        if "content_type" in self.task_config:
            self.timer_type_combo.setCurrentText(self.task_config["content_type"])
        if "attachment" in self.task_config:
            self.attachment_label.setText(self.task_config["attachment"])
            
    def on_type_changed(self, task_type: str):
        """任务类型改变时的处理"""
        # 隐藏所有配置组
        self.forward_group.hide()
        self.reply_group.hide()
        self.timer_group.hide()
        
        # 显示对应的配置组
        if task_type == "消息转发任务":
            self.forward_group.show()
        elif task_type == "消息回复任务":
            self.reply_group.show()
        elif task_type == "定时消息任务":
            self.timer_group.show()
            
    def select_attachment(self):
        """选择附件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择附件",
            "",
            "所有文件 (*.*)"
        )
        if file_path:
            self.attachment_label.setText(file_path)
            
    def get_config(self) -> Dict:
        """获取配置"""
        config = {
            "name": self.name_edit.text(),
            "type": self.type_combo.currentText()
        }
        
        # 转发任务配置
        if config["type"] == "消息转发任务":
            config.update({
                "source_group": self.source_combo.currentText(),
                "member": self.member_combo.currentText(),
                "match_type": self.match_type_combo.currentText(),
                "match_content": self.match_content_edit.text(),
                "file_type": self.file_type_combo.currentText(),
                "target": self.target_combo.currentText()
            })
            
        # 回复任务配置
        elif config["type"] == "消息回复任务":
            config.update({
                "reply_group": self.reply_group_combo.currentText(),
                "reply_member": self.reply_member_combo.currentText(),
                "reply_match_type": self.reply_match_type_combo.currentText(),
                "reply_match_content": self.reply_match_content_edit.text(),
                "reply_content": self.reply_content_edit.toPlainText(),
                "reply_type": self.reply_type_combo.currentText()
            })
            
        # 定时任务配置
        elif config["type"] == "定时消息任务":
            config.update({
                "send_time": self.time_edit.text(),
                "repeat_type": self.repeat_combo.currentText(),
                "timer_target": self.timer_target_combo.currentText(),
                "content": self.timer_content_edit.toPlainText(),
                "content_type": self.timer_type_combo.currentText(),
                "attachment": self.attachment_label.text()
            })
            
        return config
        
    def validate_config(self) -> bool:
        """验证配置"""
        config = self.get_config()
        
        # 检查任务名称
        if not config["name"]:
            return False
            
        # 检查转发任务配置
        if config["type"] == "消息转发任务":
            if not config["source_group"] or not config["target"]:
                return False
            if config["match_type"] in ["包含", "等于", "正则"] and not config["match_content"]:
                return False
                
        # 检查回复任务配置
        elif config["type"] == "消息回复任务":
            if not config["reply_group"] or not config["reply_content"]:
                return False
            if not config["reply_match_content"]:
                return False
                
        # 检查定时任务配置
        elif config["type"] == "定时消息任务":
            if not config["send_time"] or not config["timer_target"] or not config["content"]:
                return False
            if config["content_type"] in ["图片", "文件"] and not config["attachment"]:
                return False
                
        return True
        
    def accept(self):
        """确认配置"""
        if not self.validate_config():
            return
        super().accept()
        
    def update_contact_lists(self, groups: dict, friends: dict):
        """更新联系人列表"""
        # 更新群聊列表
        self.source_combo.clear()
        self.reply_group_combo.clear()
        for group in sorted(groups.keys()):
            self.source_combo.addItem(group)
            self.reply_group_combo.addItem(group)
            
        # 更新目标列表
        self.target_combo.clear()
        self.timer_target_combo.clear()
        for group in sorted(groups.keys()):
            self.target_combo.addItem(group)
            self.timer_target_combo.addItem(group)
        for friend in sorted(friends.keys()):
            self.target_combo.addItem(friend)
            self.timer_target_combo.addItem(friend)
            
        # 更新成员列表
        self.member_combo.clear()
        self.reply_member_combo.clear()
        self.member_combo.addItem("全部")
        self.reply_member_combo.addItem("全部")
        for friend in sorted(friends.keys()):
            self.member_combo.addItem(friend)
            self.reply_member_combo.addItem(friend) 