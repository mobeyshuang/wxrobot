from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QComboBox, QPushButton, QCheckBox,
                           QGroupBox, QRadioButton, QWidget, QDialogButtonBox,
                           QFormLayout, QApplication, QCompleter, QSpinBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QFont
from typing import Dict, Optional
import time

class SearchableComboBox(QComboBox):
    """可搜索的下拉选择框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setMaxVisibleItems(15)  # 增加显示条目数
        
        # 存储原始项目列表
        self.original_items = []
        
        # 设置自动补全
        self.completer = QCompleter(self)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)  # 包含匹配而不是开头匹配
        self.setCompleter(self.completer)
        
        # 应用筛选样式
        self.setStyleSheet("""
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px;
                background-color: white;
            }
            QComboBox:focus {
                border: 1px solid #4a86e8;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #ccc;
            }
        """)
        
        # 连接信号
        self.lineEdit().textEdited.connect(self.filter_items)
        self.lineEdit().selectionChanged.connect(self.on_selection_changed)
        
        # 标记是否应该显示弹出菜单
        self.should_show_popup = False
        
    def add_items(self, items):
        """添加项目并保存原始列表"""
        if not items:
            return
            
        # 确保 items 是列表
        if not isinstance(items, list):
            if hasattr(items, '__iter__'):
                items = list(items)
            else:
                items = [str(items)]
                
        # 处理列表中的字典元素
        processed_items = []
        for item in items:
            if isinstance(item, dict):
                # 如果是字典，优先使用带备注的名称
                if "remark" in item and item["remark"]:
                    processed_items.append(item["remark"])
                # 其次使用name字段
                elif "name" in item and item["name"]:
                    processed_items.append(item["name"])
                # 最后使用wxid
                elif "wxid" in item:
                    processed_items.append(item["wxid"])
            elif item:  # 确保非空
                processed_items.append(str(item))
                
        # 过滤掉空值并排序
        processed_items = [item for item in processed_items if item]
        processed_items.sort()  # 对名称进行排序，便于查找
                
        self.original_items = processed_items
        super().addItems(processed_items)
        
    def filter_items(self, text):
        """根据输入文本筛选项目"""
        self.clear()
        # 如果输入为空，不显示下拉列表，只清空并设置原始项目列表
        if not text:
            self.should_show_popup = False
            self.setCurrentIndex(-1)
            return
        
        # 筛选匹配项
        filtered_items = [item for item in self.original_items if text.lower() in item.lower()]
        super().addItems(filtered_items)
        self.setCurrentIndex(-1)
        self.lineEdit().setText(text)
        
        # 只有当主动键入时才弹出
        if len(text) > 0 and len(filtered_items) > 0:
            self.should_show_popup = True
            self.showPopup()
        
    def showPopup(self):
        """显示弹出列表时的处理"""
        # 如果没有文本或不应显示弹出菜单，则不显示
        if not self.currentText() or not self.should_show_popup:
            return
            
        # 如果有文本但内容为空，显示所有项目
        if self.count() == 0:
            super().addItems(self.original_items)
            
        super().showPopup()
        
    def hidePopup(self):
        """隐藏弹出列表时的处理"""
        current_text = self.currentText()
        super().hidePopup()
        
        # 保持文本框内容
        if self.findText(current_text) == -1:
            self.lineEdit().setText(current_text)
    
    def on_selection_changed(self):
        """当文本选择改变时的处理"""
        # 不处理，让默认选择保持
        pass
    
    def mousePressEvent(self, event):
        """重写鼠标点击事件，点击时全选文本"""
        super().mousePressEvent(event)
        if self.lineEdit().text():
            self.lineEdit().selectAll()
        self.should_show_popup = True  # 点击时应该显示弹出菜单
        
    def clear(self):
        """清除项目时不清除原始项目列表"""
        super().clear()
        
    def addItem(self, text, userData=None):
        """添加项目时也更新原始项目列表"""
        super().addItem(text, userData)
        if text not in self.original_items:
            self.original_items.append(text)
            
    def addItems(self, texts):
        """添加多个项目时也更新原始项目列表"""
        super().addItems(texts)
        for text in texts:
            if text not in self.original_items:
                self.original_items.append(text)

class TransferTaskDialog(QDialog):
    def __init__(self, parent=None, task_config: Optional[Dict] = None):
        super().__init__(parent)
        self.task_config = task_config or {}
        # 初始化为空字典和空列表
        self.groups = {}
        self.contacts = []
        
        # 设置界面
        self.setup_ui()
        
        # 如果父窗口存在robot属性，则自动获取联系人信息
        if parent and hasattr(parent, 'robot'):
            # 获取群组和联系人信息
            groups = getattr(parent.robot, 'allGroups', {})
            contacts = getattr(parent.robot, 'contacts', [])
            self.update_contact_lists(groups, contacts)
        
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("消息转发任务配置")
        self.setMinimumSize(550, 450)  # 进一步减小对话框大小
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)  # 进一步减小布局间距
        main_layout.setContentsMargins(10, 10, 10, 10)  # 减小边距
        
        # 标题
        title_label = QLabel("配置消息转发任务")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # 设置全局字体
        font = QFont()
        font.setFamily("Microsoft YaHei")  # 使用微软雅黑作为默认字体
        font.setPointSize(10)
        self.setFont(font)
        
        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)
        basic_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        basic_layout.setContentsMargins(15, 15, 15, 15)
        basic_layout.setSpacing(10)
        
        # 任务名称
        self.name_edit = QLineEdit(self.task_config.get("name", ""))
        self.name_edit.setPlaceholderText("给这个任务起个名字，例如：工作群消息转发")
        self.name_edit.setMinimumHeight(30)
        basic_layout.addRow("任务名称:", self.name_edit)
        
        main_layout.addWidget(basic_group)
        
        # 监听来源组
        source_group = QGroupBox("消息来源")
        source_layout = QVBoxLayout(source_group)
        source_layout.setContentsMargins(15, 15, 15, 15)
        source_layout.setSpacing(10)
        
        # 来源类型
        source_type_form = QFormLayout()
        source_type_widget = QWidget()
        source_type_hbox = QHBoxLayout(source_type_widget)
        source_type_hbox.setContentsMargins(0, 0, 0, 0)
        
        self.source_type_group_radio = QRadioButton("群聊")
        self.source_type_friend_radio = QRadioButton("好友")
        self.source_type_group_radio.setChecked(True)
        source_type_hbox.addWidget(self.source_type_group_radio)
        source_type_hbox.addWidget(self.source_type_friend_radio)
        source_type_hbox.addStretch()
        
        source_type_form.addRow("来源类型:", source_type_widget)
        source_layout.addLayout(source_type_form)
        
        # 来源选择
        source_select_form = QFormLayout()
        self.source_combo = SearchableComboBox()
        self.source_combo.setMinimumHeight(30)
        source_select_form.addRow("选择来源:", self.source_combo)
        source_layout.addLayout(source_select_form)
        
        # 成员选择（仅当来源为群聊时可用）
        member_form = QFormLayout()
        self.member_combo = SearchableComboBox()
        self.member_combo.addItem("全部")
        self.member_combo.setMinimumHeight(30)
        member_form.addRow("群成员:", self.member_combo)
        source_layout.addLayout(member_form)
        
        main_layout.addWidget(source_group)
        
        # 转发类型选择
        forward_type_group = QGroupBox("转发类型")
        forward_type_layout = QVBoxLayout(forward_type_group)
        forward_type_layout.setContentsMargins(15, 15, 15, 15)
        forward_type_layout.setSpacing(10)
        
        forward_type_widget = QWidget()
        forward_type_hbox = QHBoxLayout(forward_type_widget)
        forward_type_hbox.setContentsMargins(0, 0, 0, 0)
        
        self.forward_type_text_radio = QRadioButton("消息转发")
        self.forward_type_file_radio = QRadioButton("文件转发")
        self.forward_type_text_radio.setChecked(True)
        forward_type_hbox.addWidget(self.forward_type_text_radio)
        forward_type_hbox.addWidget(self.forward_type_file_radio)
        forward_type_hbox.addStretch()
        
        forward_type_layout.addWidget(forward_type_widget)
        main_layout.addWidget(forward_type_group)
        
        # 消息匹配组
        self.message_match_group = QGroupBox("消息匹配")
        message_match_layout = QVBoxLayout(self.message_match_group)
        message_match_layout.setContentsMargins(15, 15, 15, 15)
        message_match_layout.setSpacing(10)
        
        # 匹配类型
        match_type_form = QFormLayout()
        self.match_type_combo = QComboBox()
        self.match_type_combo.addItems(["包含", "等于", "正则"])
        self.match_type_combo.setMinimumHeight(30)
        match_type_form.addRow("匹配类型:", self.match_type_combo)
        message_match_layout.addLayout(match_type_form)
        
        # 匹配内容
        match_content_form = QFormLayout()
        self.match_content_edit = QLineEdit()
        self.match_content_edit.setPlaceholderText("请输入要匹配的内容")
        self.match_content_edit.setMinimumHeight(30)
        match_content_form.addRow("匹配内容:", self.match_content_edit)
        message_match_layout.addLayout(match_content_form)
        
        main_layout.addWidget(self.message_match_group)
        
        # 文件匹配组
        self.file_match_group = QGroupBox("文件匹配")
        file_match_layout = QVBoxLayout(self.file_match_group)
        file_match_layout.setContentsMargins(15, 15, 15, 15)
        file_match_layout.setSpacing(10)
        
        # 文件类型
        file_type_form = QFormLayout()
        self.file_type_combo = QComboBox()
        self.file_type_combo.addItems(["文档", "图片", "视频"])
        self.file_type_combo.setMinimumHeight(30)
        file_type_form.addRow("文件类型:", self.file_type_combo)
        file_match_layout.addLayout(file_type_form)
        
        # 文件匹配类型
        file_match_type_form = QFormLayout()
        self.file_match_type_combo = QComboBox()
        self.file_match_type_combo.addItems(["包含", "等于", "正则"])
        self.file_match_type_combo.setMinimumHeight(30)
        file_match_type_form.addRow("匹配类型:", self.file_match_type_combo)
        file_match_layout.addLayout(file_match_type_form)
        
        # 文件匹配内容
        file_match_content_form = QFormLayout()
        self.file_match_content_edit = QLineEdit()
        self.file_match_content_edit.setPlaceholderText("请输入要匹配的文件名关键词，多个关键词用逗号分隔")
        self.file_match_content_edit.setMinimumHeight(30)
        file_match_content_form.addRow("匹配内容:", self.file_match_content_edit)
        file_match_layout.addLayout(file_match_content_form)
        
        # 文件大小限制
        file_size_form = QFormLayout()
        self.file_size_spin = QSpinBox()
        self.file_size_spin.setRange(1, 1000)  # 1MB到1000MB
        self.file_size_spin.setValue(50)  # 默认50MB
        self.file_size_spin.setSuffix(" MB")
        self.file_size_spin.setMinimumHeight(30)
        file_size_form.addRow("文件大小限制:", self.file_size_spin)
        file_match_layout.addLayout(file_size_form)
        
        main_layout.addWidget(self.file_match_group)
        
        # 目标选择组
        target_group = QGroupBox("转发目标")
        target_layout = QVBoxLayout(target_group)
        target_layout.setContentsMargins(15, 15, 15, 15)
        target_layout.setSpacing(10)
        
        # 目标类型
        target_type_form = QFormLayout()
        target_type_widget = QWidget()
        target_type_hbox = QHBoxLayout(target_type_widget)
        target_type_hbox.setContentsMargins(0, 0, 0, 0)
        
        self.target_type_group_radio = QRadioButton("群聊")
        self.target_type_friend_radio = QRadioButton("好友")
        self.target_type_group_radio.setChecked(True)
        target_type_hbox.addWidget(self.target_type_group_radio)
        target_type_hbox.addWidget(self.target_type_friend_radio)
        target_type_hbox.addStretch()
        
        target_type_form.addRow("目标类型:", target_type_widget)
        target_layout.addLayout(target_type_form)
        
        # 目标选择
        target_select_form = QFormLayout()
        self.target_combo = SearchableComboBox()
        self.target_combo.setMinimumHeight(30)
        target_select_form.addRow("选择目标:", self.target_combo)
        target_layout.addLayout(target_select_form)
        
        main_layout.addWidget(target_group)
        
        # 按钮组
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("保存")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        main_layout.addWidget(button_box)
        
        # 连接信号
        self.source_type_group_radio.toggled.connect(self.on_source_type_changed)
        self.source_type_friend_radio.toggled.connect(self.on_source_type_changed)
        self.target_type_group_radio.toggled.connect(self.on_target_type_changed)
        self.target_type_friend_radio.toggled.connect(self.on_target_type_changed)
        self.forward_type_text_radio.toggled.connect(self.on_forward_type_changed)
        self.forward_type_file_radio.toggled.connect(self.on_forward_type_changed)
        self.source_combo.currentTextChanged.connect(self.update_member_list)
        
        # 初始化UI状态
        self.on_source_type_changed()
        self.on_target_type_changed()
        self.on_forward_type_changed()
        
    def on_source_type_changed(self):
        """来源类型改变时的处理"""
        # 使用单选按钮的状态来判断来源类型
        is_group = self.source_type_group_radio.isChecked()
        self.source_combo.clear()
        
        if is_group:
            # 群聊列表
            if isinstance(self.groups, dict):
                for name in sorted(self.groups.values()):
                    self.source_combo.addItem(name)
            # 如果之前的选择是有效的，恢复选择
            if self.task_config and "source" in self.task_config:
                current_source = self.task_config["source"]
                index = self.source_combo.findText(current_source)
                if index >= 0:
                    self.source_combo.setCurrentIndex(index)
        else:
            # 好友列表
            if isinstance(self.contacts, list):
                for contact in self.contacts:
                    if isinstance(contact, dict):
                        name = contact.get("remark") or contact.get("name") or contact.get("wxid")
                        if name:
                            self.source_combo.addItem(name)
            # 如果之前的选择是有效的，恢复选择
            if self.task_config and "source" in self.task_config:
                current_source = self.task_config["source"]
                index = self.source_combo.findText(current_source)
                if index >= 0:
                    self.source_combo.setCurrentIndex(index)
        
        # 更新成员选择框的状态
        self.member_combo.setEnabled(is_group)
        
    def on_target_type_changed(self):
        """目标类型改变时的处理"""
        # 使用单选按钮的状态来判断目标类型
        is_group = self.target_type_group_radio.isChecked()
        self.target_combo.clear()
        
        if is_group:
            # 群聊列表
            if isinstance(self.groups, dict):
                for name in sorted(self.groups.values()):
                    self.target_combo.addItem(name)
            # 如果之前的选择是有效的，恢复选择
            if self.task_config and "target" in self.task_config:
                current_target = self.task_config["target"]
                index = self.target_combo.findText(current_target)
                if index >= 0:
                    self.target_combo.setCurrentIndex(index)
        else:
            # 好友列表
            if isinstance(self.contacts, list):
                for contact in self.contacts:
                    if isinstance(contact, dict):
                        name = contact.get("remark") or contact.get("name") or contact.get("wxid")
                        if name:
                            self.target_combo.addItem(name)
            # 如果之前的选择是有效的，恢复选择
            if self.task_config and "target" in self.task_config:
                current_target = self.task_config["target"]
                index = self.target_combo.findText(current_target)
                if index >= 0:
                    self.target_combo.setCurrentIndex(index)
        
    def on_forward_type_changed(self):
        """转发类型变化处理"""
        is_text_forward = self.forward_type_text_radio.isChecked()
        self.message_match_group.setEnabled(is_text_forward)
        self.file_match_group.setEnabled(not is_text_forward)
        
    def update_contact_lists(self, groups, contacts):
        """更新联系人列表"""
        # 处理群组数据，确保是字典格式
        if isinstance(groups, dict):
            # 只保留群聊数据
            self.groups = {wxid: name for wxid, name in groups.items() 
                         if wxid and name and "@chatroom" in wxid}
        else:
            # 尝试从 robot 中获取群组数据
            self.groups = {}
            if hasattr(self.parent(), 'robot') and hasattr(self.parent().robot, 'allGroups'):
                self.groups = {wxid: name for wxid, name in self.parent().robot.allGroups.items() 
                             if wxid and name and "@chatroom" in wxid}
        
        # 处理联系人数据，确保是列表格式
        if isinstance(contacts, list):
            self.contacts = contacts
        else:
            # 尝试从 robot 中获取联系人数据
            self.contacts = []
            if hasattr(self.parent(), 'robot') and hasattr(self.parent().robot, 'contacts'):
                self.contacts = self.parent().robot.contacts
        
        # 根据当前选择的来源类型更新来源列表
        self.on_source_type_changed()
        
        # 根据当前选择的目标类型更新目标列表
        self.on_target_type_changed()
        
        # 如果有配置，重新加载配置，确保显示正确的选择
        if self.task_config:
            self.load_config(self.task_config)
        
    def get_config(self) -> Dict:
        """获取配置"""
        # 确定来源类型和目标类型
        source_type = "群聊" if self.source_type_group_radio.isChecked() else "好友"
        target_type = "群聊" if self.target_type_group_radio.isChecked() else "好友"
        
        # 确定转发类型
        is_text_forward = self.forward_type_text_radio.isChecked()
        
        # 获取来源和目标
        source = self.source_combo.currentText()
        target = self.target_combo.currentText()
        
        # 保存原始wxid以便调试
        source_wxid = None
        target_wxid = None
        
        # 记录群名和群ID的对应关系，但使用群名作为配置
        if source_type == "群聊":
            # 查找对应的群ID用于调试
            for wxid, name in self.groups.items():
                if name == source:
                    source_wxid = wxid
                    print(f"来源群 '{source}' 对应的wxid: {wxid}")
                    break
        
        if target_type == "群聊":
            # 查找对应的群ID用于调试
            for wxid, name in self.groups.items():
                if name == target:
                    target_wxid = wxid
                    print(f"目标群 '{target}' 对应的wxid: {wxid}")
                    break
        
        # 构建配置
        config = {
            "name": self.name_edit.text(),
            "type": "transfer",
            "status": self.task_config.get("status", "stopped"),  # 保留原状态
            "source_type": source_type,
            "source": source,
            "member": self.member_combo.currentText() if source_type == "群聊" else "",
            "forward_type": "text" if is_text_forward else "file",
            "target_type": target_type,
            "target": target
        }
        
        # 根据转发类型添加不同的匹配配置
        if is_text_forward:
            config.update({
                "match_type": self.match_type_combo.currentText(),
                "match_content": self.match_content_edit.text()
            })
        else:
            config.update({
                "file_type": self.file_type_combo.currentText(),
                "file_match_type": self.file_match_type_combo.currentText(),
                "file_match_content": self.file_match_content_edit.text(),
                "file_size_limit": self.file_size_spin.value()
            })
        
        # 保留last_state和其他特殊字段
        if self.task_config:
            for key in ["last_state"]:
                if key in self.task_config:
                    config[key] = self.task_config[key]
        
        print(f"转发任务配置: {config}")
        return config
        
    def load_config(self, config: Dict):
        """加载配置"""
        if not config:
            return
            
        print(f"加载转发任务配置: {config}")
        
        # 设置基本信息
        self.name_edit.setText(config.get("name", ""))
        
        # 设置来源类型和来源
        source_type = config.get("source_type", "群聊")
        if source_type == "群聊":
            self.source_type_group_radio.setChecked(True)
        else:
            self.source_type_friend_radio.setChecked(True)
            
        # 设置来源
        source = config.get("source", "")
        
        # 如果source是群ID（包含@chatroom），则尝试转换为群名
        if source_type == "群聊" and "@chatroom" in source:
            print(f"尝试将来源群ID {source} 转换为群名")
            # 查找对应的群名
            if source in self.groups:
                source = self.groups[source]
                print(f"转换后的来源群名: {source}")
        
        # 设置来源选择框
        self.on_source_type_changed()  # 确保列表已更新
        if source:
            index = self.source_combo.findText(source)
            if index >= 0:
                self.source_combo.setCurrentIndex(index)
                print(f"设置来源: {source}")
            else:
                print(f"找不到来源 {source} 在下拉列表中")
            
        # 设置群成员
        if source_type == "群聊":
            member = config.get("member", "全部")
            index = self.member_combo.findText(member)
            if index >= 0:
                self.member_combo.setCurrentIndex(index)
            
        # 设置转发类型
        forward_type = config.get("forward_type", "text")
        if forward_type == "text":
            self.forward_type_text_radio.setChecked(True)
            # 设置消息匹配
            match_type = config.get("match_type", "包含")
            index = self.match_type_combo.findText(match_type)
            if index >= 0:
                self.match_type_combo.setCurrentIndex(index)
            self.match_content_edit.setText(config.get("match_content", ""))
        else:
            self.forward_type_file_radio.setChecked(True)
            # 设置文件匹配
            file_type = config.get("file_type", "文档")
            index = self.file_type_combo.findText(file_type)
            if index >= 0:
                self.file_type_combo.setCurrentIndex(index)
                
            file_match_type = config.get("file_match_type", "包含")
            index = self.file_match_type_combo.findText(file_match_type)
            if index >= 0:
                self.file_match_type_combo.setCurrentIndex(index)
                
            self.file_match_content_edit.setText(config.get("file_match_content", ""))
            
            # 设置文件大小限制
            file_size_limit = config.get("file_size_limit", 50)
            self.file_size_spin.setValue(file_size_limit)
            
        # 设置目标类型和目标
        target_type = config.get("target_type", "群聊")
        if target_type == "群聊":
            self.target_type_group_radio.setChecked(True)
        else:
            self.target_type_friend_radio.setChecked(True)
        
        # 设置目标
        target = config.get("target", "")
        
        # 如果target是群ID（包含@chatroom），则尝试转换为群名
        if target_type == "群聊" and "@chatroom" in target:
            print(f"尝试将目标群ID {target} 转换为群名")
            # 查找对应的群名
            if target in self.groups:
                target = self.groups[target]
                print(f"转换后的目标群名: {target}")
        
        # 设置目标选择框
        self.on_target_type_changed()  # 确保列表已更新
        if target:
            index = self.target_combo.findText(target)
            if index >= 0:
                self.target_combo.setCurrentIndex(index)
                print(f"设置目标: {target}")
            else:
                print(f"找不到目标 {target} 在下拉列表中")
        
    def update_member_list(self, group_name):
        """当选择的群变化时更新成员列表"""
        if not self.source_type_group_radio.isChecked() or not group_name:
            return
            
        # 清空成员列表
        self.member_combo.clear()
        self.member_combo.addItem("全部")
        
        try:
            # 获取群ID
            group_id = None
            
            # 根据groups的类型获取群ID
            if isinstance(self.groups, dict) and group_name in self.groups:
                group_id = self.groups[group_name]
            elif hasattr(self.parent(), 'robot') and hasattr(self.parent().robot, 'allGroups'):
                # 尝试从robot中获取
                for wxid, name in self.parent().robot.allGroups.items():
                    if name == group_name:
                        group_id = wxid
                        break
            
            if not group_id:
                print(f"无法找到群 '{group_name}' 的ID")
                return
                
            # 尝试调用parent().robot.wcf.get_chatroom_members
            if hasattr(self.parent(), 'robot'):
                # 获取群成员列表
                members = self.parent().robot.wcf.get_chatroom_members(group_id)
                
                if not members:
                    print(f"获取群 '{group_name}' 的成员列表为空")
                    return
                    
                # 添加成员到下拉框
                member_names = ["全部"]
                
                # 处理成员列表
                for member_wxid in members:
                    try:
                        # 获取群成员昵称
                        member_name = self.parent().robot.wcf.get_alias_in_chatroom(member_wxid, group_id)
                        if member_name:
                            member_names.append(member_name)
                        else:
                            member_names.append(member_wxid)
                    except Exception as e:
                        print(f"获取成员 {member_wxid} 的昵称失败: {e}")
                        member_names.append(member_wxid)
                
                # 去重并排序
                member_names = list(set(member_names))
                member_names.sort()
                
                # 更新下拉框
                self.member_combo.clear()
                self.member_combo.add_items(member_names)
        except Exception as e:
            print(f"获取群成员失败: {e}")
            # 出错时保持默认的"全部"选项 