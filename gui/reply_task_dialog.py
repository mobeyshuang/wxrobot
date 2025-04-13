from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QComboBox, QPushButton, QCheckBox,
                           QGroupBox, QRadioButton, QTextEdit, QWidget, QCompleter,
                           QFormLayout, QDialogButtonBox, QFileDialog)
from PyQt5.QtCore import Qt
from typing import Dict, Optional
from PyQt5.QtGui import QFont

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
        """重写鼠标点击事件，点击时显示下拉菜单"""
        super().mousePressEvent(event)
        self.showPopup()
        
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

class ReplyTaskDialog(QDialog):
    def __init__(self, parent=None, task_config: Optional[Dict] = None):
        """初始化对话框"""
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
            
        # 加载配置
        self.load_config()
        
        # 连接信号
        self.source_type_group_radio.toggled.connect(self.on_source_type_changed)
        self.source_type_friend_radio.toggled.connect(self.on_source_type_changed)
        self.source_combo.currentTextChanged.connect(self.on_source_changed)
        
        # 初始化界面状态
        self.on_source_type_changed(True)
        
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("自动回复任务")
        self.setMinimumSize(600, 400)
        
        # 创建主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # 任务名称
        self.name_edit = QLineEdit()
        form_layout.addRow("任务名称:", self.name_edit)
        
        # 来源类型选择
        source_type_layout = QHBoxLayout()
        self.source_type_group_radio = QRadioButton("群聊")
        self.source_type_group_radio.setChecked(True)
        self.source_type_friend_radio = QRadioButton("好友")
        source_type_layout.addWidget(self.source_type_group_radio)
        source_type_layout.addWidget(self.source_type_friend_radio)
        form_layout.addRow("来源类型:", source_type_layout)
        
        # 来源选择
        self.source_combo = SearchableComboBox()
        form_layout.addRow("来源:", self.source_combo)
        
        # 成员选择
        self.member_combo = QComboBox()
        self.member_combo.addItem("全部")
        form_layout.addRow("成员:", self.member_combo)
        
        # 匹配内容
        self.match_content_edit = QTextEdit()
        self.match_content_edit.setMinimumHeight(100)
        form_layout.addRow("匹配内容:", self.match_content_edit)
        
        # 回复内容
        self.reply_content_edit = QTextEdit()
        self.reply_content_edit.setMinimumHeight(100)
        form_layout.addRow("回复内容:", self.reply_content_edit)
        
        # 是否被@
        self.require_at_checkbox = QCheckBox("只在被@时回复")
        form_layout.addRow("", self.require_at_checkbox)
        
        # 添加表单布局到主布局
        layout.addLayout(form_layout)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
    def load_config(self):
        """加载配置"""
        if not self.task_config:
            return
            
        # 设置基本信息
        self.name_edit.setText(self.task_config.get("name", ""))
        
        # 设置来源类型
        source_type = self.task_config.get("source_type", "群聊")
        self.source_type_group_radio.setChecked(source_type == "群聊")
        self.source_type_friend_radio.setChecked(source_type == "好友")
        
        # 设置来源
        source = self.task_config.get("source", "")
        if source:
            # 如果是群聊，需要将群ID转换为群名称
            if source_type == "群聊" and isinstance(self.groups, dict):
                for wxid, name in self.groups.items():
                    if wxid == source:
                        source = name
                        break
            self.source_combo.setCurrentText(source)
            # 当来源是群聊时，触发更新成员列表
            if source_type == "群聊":
                self.update_member_list(source)
                # 设置选中的成员
                member = self.task_config.get("member", "全部")
                index = self.member_combo.findText(member)
                if index >= 0:
                    self.member_combo.setCurrentIndex(index)
                    
        # 设置匹配内容
        self.match_content_edit.setPlainText(self.task_config.get("match_content", ""))
        
        # 设置回复内容
        self.reply_content_edit.setPlainText(self.task_config.get("reply_content", ""))
        
        # 设置是否被@
        self.require_at_checkbox.setChecked(self.task_config.get("require_at", False))
        
    def get_config(self) -> dict:
        """获取配置"""
        config = {
            "name": self.name_edit.text(),
            "type": "reply",
            "match_content": self.match_content_edit.toPlainText(),
            "reply_content": self.reply_content_edit.toPlainText(),
            "require_at": self.require_at_checkbox.isChecked(),
            "source_type": "group" if self.source_type_group_radio.isChecked() else "friend",
            "source": self.source_combo.currentText(),
            "member": self.member_combo.currentText()
        }
        return config
        
    def update_contact_lists(self, groups: dict = None, contacts: list = None):
        """更新联系人列表"""
        # 如果提供了参数，则更新内部数据
        if groups is not None:
            self.groups = groups
        if contacts is not None:
            self.contacts = contacts
            
        self.source_combo.clear()
        if self.source_type_group_radio.isChecked():
            # 群聊列表
            if isinstance(self.groups, dict):
                group_names = sorted(self.groups.values())
                self.source_combo.add_items(group_names)
        else:
            # 好友列表
            if isinstance(self.contacts, list):
                friend_names = []
                for contact in self.contacts:
                    if isinstance(contact, dict):
                        name = contact.get("remark") or contact.get("name") or contact.get("wxid")
                        if name:
                            friend_names.append(name)
                friend_names.sort()
                self.source_combo.add_items(friend_names)
                
        # 如果之前的选择是有效的，恢复选择
        if self.task_config and "source" in self.task_config:
            current_source = self.task_config["source"]
            index = self.source_combo.findText(current_source)
            if index >= 0:
                self.source_combo.setCurrentIndex(index)
        
    def on_source_type_changed(self, checked):
        """来源类型改变时的处理"""
        is_group = self.source_type_group_radio.isChecked()
        self.member_combo.setEnabled(is_group)
        self.update_contact_lists()
        
    def on_source_changed(self, text):
        """来源改变时的处理"""
        if self.source_type_group_radio.isChecked():
            self.update_member_list(text)
            
    def update_member_list(self, group_name):
        """更新成员列表"""
        self.member_combo.clear()
        self.member_combo.addItem("全部")
        
        if not group_name or not isinstance(self.groups, dict):
            return
            
        # 获取群ID
        group_id = None
        for wxid, name in self.groups.items():
            if name == group_name:
                group_id = wxid
                break
                
        if not group_id:
            return
            
        try:
            # 获取群成员
            members = self.parent().robot.wcf.get_chatroom_members(group_id)
            if not members:
                return
                
            # 添加成员到下拉框
            for member_wxid in members:
                try:
                    # 获取群成员昵称
                    member_name = self.parent().robot.wcf.get_alias_in_chatroom(member_wxid, group_id)
                    if member_name:
                        self.member_combo.addItem(member_name)
                    else:
                        self.member_combo.addItem(member_wxid)
                except Exception as e:
                    print(f"获取成员 {member_wxid} 的昵称失败: {e}")
                    self.member_combo.addItem(member_wxid)
        except Exception as e:
            print(f"获取群成员失败: {e}")
            self.statusBar().showMessage("获取群成员失败，请点击更新群成员按钮手动更新") 