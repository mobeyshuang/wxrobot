from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QComboBox, QPushButton, QCheckBox,
                           QGroupBox, QRadioButton, QTextEdit, QWidget,
                           QFileDialog, QSpinBox, QCalendarWidget, QCompleter)
from PyQt5.QtCore import Qt, QDate
from typing import Dict, Optional
import os
import json

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
        
        # 应用筛选样式 - 简化样式，不使用图片资源，避免加载失败
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
        
        # 修复焦点和点击问题
        self.view().setTextElideMode(Qt.ElideNone)  # 防止长文本被省略
        self.setMinimumContentsLength(20)  # 设置最小内容长度
        
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
        # 如果输入为空，显示所有项目
        if not text:
            super().addItems(self.original_items)
            return
        
        # 筛选匹配项 - 改进匹配算法，支持拼音首字母和部分匹配
        filtered_items = []
        for item in self.original_items:
            if text.lower() in item.lower():
                filtered_items.append(item)
            # 这里可以添加拼音匹配逻辑
        
        super().addItems(filtered_items)
        self.setCurrentText(text)
        
        # 如果有匹配项，显示下拉列表
        if filtered_items:
            self.showPopup()
            
    def showPopup(self):
        """显示弹出列表时的处理"""
        # 如果列表为空，添加所有项目
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
    
    def mousePressEvent(self, event):
        """鼠标点击事件处理"""
        # 在调用父类方法前，确保数据已加载
        if self.count() == 0 and self.original_items:
            self.clear()
            super().addItems(self.original_items)
        
        # 调用父类方法
        super().mousePressEvent(event)
        
        try:
            # 尝试显示下拉列表
            if self.rect().contains(event.pos()):
                self.showPopup()
        except Exception as e:
            print(f"显示下拉列表时出错: {e}")
        
    def focusInEvent(self, event):
        """获取焦点时确保项目是完整的"""
        super().focusInEvent(event)
        # 当获取焦点时，确保下拉列表项目是完整的
        if self.count() == 0 and len(self.original_items) > 0:
            super().addItems(self.original_items)
        
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

class ScheduledTaskDialog(QDialog):
    def __init__(self, parent=None, task_config: Optional[Dict] = None):
        super().__init__(parent)
        self.task_config = task_config or {}
        # 初始化为空字典和空列表
        self.groups = {}
        self.contacts = []
        self.attachment_path = ""
        self.cities = {}
        
        # 加载城市列表
        self.load_cities()
        
        # 设置界面
        self.setup_ui()
        
        # 如果父窗口存在robot属性，则自动获取联系人信息
        if parent and hasattr(parent, 'robot'):
            # 获取群组和联系人信息
            groups = getattr(parent.robot, 'allGroups', {})
            contacts = getattr(parent.robot, 'contacts', [])
            self.update_contact_lists(groups, contacts)
        
        # 加载配置
        if self.task_config:
            self.load_config(self.task_config)
        
    def load_cities(self):
        """加载城市列表"""
        try:
            # 尝试从base目录加载
            city_file = os.path.join("base", "main_city.json")
            if not os.path.exists(city_file):
                # 如果不存在，则尝试从根目录加载
                city_file = "main_city.json"
                if not os.path.exists(city_file):
                    print(f"城市列表文件不存在: base/main_city.json 或 main_city.json")
                    self.cities = {}
                    return
            
            with open(city_file, "r", encoding="utf-8") as f:
                # 跳过第一行注释
                content = f.read()
                if content.startswith("//"):
                    # 去掉第一行注释
                    content = "\n".join(content.split("\n")[1:])
                self.cities = json.loads(content)
            
            print(f"已从 {city_file} 加载 {len(self.cities)} 个城市")
            # 打印前10个城市及代码，检查数据格式
            count = 0
            for city, code in self.cities.items():
                if count < 10:
                    print(f"城市: {city}, 代码: {code}")
                    count += 1
                else:
                    break
        except Exception as e:
            print(f"加载城市列表失败: {e}")
            import traceback
            traceback.print_exc()
            self.cities = {}
        
    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("定时消息任务配置")
        self.setMinimumWidth(500)
        
        # 创建主布局
        main_layout = QVBoxLayout()
        
        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QVBoxLayout()
        
        # 任务名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("任务名称:"))
        self.name_edit = QLineEdit(self.task_config.get("name", ""))
        name_layout.addWidget(self.name_edit)
        basic_layout.addLayout(name_layout)
        
        basic_group.setLayout(basic_layout)
        main_layout.addWidget(basic_group)
        
        # 发送时间组
        time_group = QGroupBox("发送时间")
        time_layout = QVBoxLayout()
        
        # 时间选择
        time_select_layout = QHBoxLayout()
        time_select_layout.addWidget(QLabel("时间:"))
        self.hour_spin = QSpinBox()
        self.hour_spin.setRange(0, 23)
        self.hour_spin.setValue(8)  # 默认8点
        time_select_layout.addWidget(self.hour_spin)
        time_select_layout.addWidget(QLabel(":"))
        self.min_spin = QSpinBox()
        self.min_spin.setRange(0, 59)
        self.min_spin.setValue(0)  # 默认0分
        time_select_layout.addWidget(self.min_spin)
        time_layout.addLayout(time_select_layout)
        
        # 重复方式
        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(QLabel("重复:"))
        self.repeat_combo = QComboBox()
        self.repeat_combo.addItems(["一次", "每天", "每周", "每小时"])
        repeat_layout.addWidget(self.repeat_combo)
        time_layout.addLayout(repeat_layout)
        
        # 日期选择（一次性任务）
        self.date_calendar = QCalendarWidget()
        self.date_calendar.setMinimumDate(QDate.currentDate())
        time_layout.addWidget(self.date_calendar)
        
        # 周选择（每周任务）
        self.week_widget = QWidget()
        week_layout = QHBoxLayout()
        self.week_checks = []
        week_days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for day in week_days:
            check = QCheckBox(day)
            self.week_checks.append(check)
            week_layout.addWidget(check)
        self.week_widget.setLayout(week_layout)
        time_layout.addWidget(self.week_widget)
        
        # 小时间隔（每小时任务）
        self.hourly_interval_widget = QWidget()
        hourly_layout = QHBoxLayout()
        hourly_layout.addWidget(QLabel("间隔小时数:"))
        self.interval_hours_spin = QSpinBox()
        self.interval_hours_spin.setRange(1, 24)
        self.interval_hours_spin.setValue(8)  # 默认8小时
        hourly_layout.addWidget(self.interval_hours_spin)
        hourly_layout.addStretch(1)  # 添加弹性空间，让控件靠左
        self.hourly_interval_widget.setLayout(hourly_layout)
        time_layout.addWidget(self.hourly_interval_widget)
        
        time_group.setLayout(time_layout)
        main_layout.addWidget(time_group)
        
        # 发送对象组
        target_group = QGroupBox("发送对象")
        target_layout = QVBoxLayout()
        
        # 目标类型
        target_type_layout = QHBoxLayout()
        target_type_layout.addWidget(QLabel("类型:"))
        self.target_type_combo = QComboBox()
        self.target_type_combo.addItems(["群聊", "好友"])
        target_type_layout.addWidget(self.target_type_combo)
        target_layout.addLayout(target_type_layout)
        
        # 目标选择
        target_layout.addWidget(QLabel("选择:"))
        self.target_combo = SearchableComboBox()
        target_layout.addWidget(self.target_combo)
        
        target_group.setLayout(target_layout)
        main_layout.addWidget(target_group)
        
        # 消息内容组
        message_group = QGroupBox("消息内容")
        message_layout = QVBoxLayout()
        
        # 消息内容
        self.message_edit = QTextEdit()
        self.message_edit.setMaximumHeight(100)
        message_layout.addWidget(self.message_edit)
        
        # 添加特殊消息类型选项
        special_message_layout = QHBoxLayout()
        self.weather_check = QCheckBox("发送天气消息")
        self.news_check = QCheckBox("发送新闻消息")
        special_message_layout.addWidget(self.weather_check)
        special_message_layout.addWidget(self.news_check)
        message_layout.addLayout(special_message_layout)
        
        # 添加城市选择控件（默认隐藏）
        self.city_widget = QWidget()
        city_layout = QHBoxLayout()
        city_layout.addWidget(QLabel("城市:"))

        # 使用普通的QComboBox而不是SearchableComboBox
        self.city_combo = QComboBox()
        self.city_combo.setEditable(True)
        self.city_combo.setMaxVisibleItems(15)
        self.city_combo.setInsertPolicy(QComboBox.NoInsert)  # 阻止无效输入保存到列表
        self.city_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #aaa;
                border-radius: 3px;
                padding: 5px;
                background-color: white;
                min-width: 150px;
            }
            QComboBox:hover {
                border: 1px solid #4a86e8;
            }
            QComboBox:focus {
                border: 1px solid #4a86e8;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left: 1px solid #aaa;
                background-color: #f0f0f0;
            }
            QComboBox::drop-down:hover {
                background-color: #e0e0e0;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #aaa;
                selection-background-color: #4a86e8;
                selection-color: white;
                background-color: white;
            }
        """)

        # 保存原始城市列表
        self.original_cities = sorted(self.cities.keys())
        
        # 设置自动补全功能替代之前的筛选方法
        completer = QCompleter(self.original_cities)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)  # 包含匹配而不是开头匹配
        self.city_combo.setCompleter(completer)
        
        # 加载城市列表
        self.city_combo.addItems(self.original_cities)
        if self.original_cities:
            self.city_combo.setCurrentText(self.original_cities[0])
            print(f"设置默认城市为: {self.original_cities[0]}")
        
        city_layout.addWidget(self.city_combo)

        # 添加单独的下拉按钮
        self.city_dropdown_btn = QPushButton("▼")
        self.city_dropdown_btn.setMaximumWidth(30)
        self.city_dropdown_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #aaa;
                border-radius: 3px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        self.city_dropdown_btn.clicked.connect(lambda: self.city_combo.showPopup())
        city_layout.addWidget(self.city_dropdown_btn)

        self.city_widget.setLayout(city_layout)
        self.city_widget.hide()  # 默认隐藏
        message_layout.addWidget(self.city_widget)
        
        # 确认选项
        self.confirm_check = QCheckBox("确认发送以上内容")
        self.confirm_check.setChecked(True)
        message_layout.addWidget(self.confirm_check)
        
        message_group.setLayout(message_layout)
        main_layout.addWidget(message_group)
        
        # 附件组
        attachment_group = QGroupBox("附件")
        attachment_layout = QVBoxLayout()
        
        # 附件选择
        attachment_select_layout = QHBoxLayout()
        self.attachment_btn = QPushButton("选择文件")
        self.attachment_btn.clicked.connect(self.select_attachment)
        attachment_select_layout.addWidget(self.attachment_btn)
        self.attachment_label = QLabel("未选择文件")
        attachment_select_layout.addWidget(self.attachment_label)
        attachment_layout.addLayout(attachment_select_layout)
        
        # 预览区域
        self.preview_label = QLabel("预览区域")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; padding: 10px;")
        attachment_layout.addWidget(self.preview_label)
        
        attachment_group.setLayout(attachment_layout)
        main_layout.addWidget(attachment_group)
        
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
        self.target_type_combo.currentTextChanged.connect(self.on_target_type_changed)
        self.repeat_combo.currentTextChanged.connect(self.on_repeat_changed)
        self.weather_check.stateChanged.connect(self.on_weather_check_changed)
        
        # 应用初始状态
        self.on_repeat_changed(self.repeat_combo.currentText())
        
        # 设置城市下拉框的事件处理
        if hasattr(self, 'city_combo') and self.city_combo:
            print("设置城市下拉框事件")
            # 当用户按下回车键时，强制显示下拉列表
            self.city_combo.lineEdit().returnPressed.connect(self.ensure_city_dropdown)
        
        # 确保下拉按钮正常工作
        if hasattr(self, 'city_dropdown_btn'):
            print("已添加城市下拉按钮")
            self.city_dropdown_btn.clicked.connect(lambda: self.city_combo.showPopup())
        
    def on_weather_check_changed(self, state):
        """当天气复选框状态改变时显示或隐藏城市选择"""
        if state == Qt.Checked:
            self.city_widget.show()
        else:
            self.city_widget.hide()
        
    def load_config(self, config: Dict):
        """加载配置"""
        try:
            if config:
                print(f"开始加载配置: {config}")
                self.name_edit.setText(config.get("name", ""))
                
                # 设置时间
                time_str = config.get("time", "08:00")
                print(f"加载时间配置: {time_str}")
                try:
                    hour, minute = map(int, time_str.split(":"))
                    self.hour_spin.setValue(hour)
                    self.min_spin.setValue(minute)
                    print(f"设置时间为: {hour}:{minute}")
                except Exception as e:
                    print(f"解析时间错误: {e}")
                    # 设置默认值
                    self.hour_spin.setValue(8)
                    self.min_spin.setValue(0)
                
                # 设置重复方式
                repeat_type = config.get("repeat_type", "一次")
                print(f"加载重复方式: {repeat_type}")
                self.repeat_combo.setCurrentText(repeat_type)
                
                # 设置日期
                if repeat_type == "一次":
                    date_str = config.get("date", "")
                    print(f"加载日期: {date_str}")
                    if date_str:
                        date = QDate.fromString(date_str, "yyyy-MM-dd")
                        if date.isValid():
                            self.date_calendar.setSelectedDate(date)
                            print(f"设置日期为: {date.toString('yyyy-MM-dd')}")
                        else:
                            print(f"无效的日期格式: {date_str}")
                
                # 设置周选择
                elif repeat_type == "每周":
                    week_days = config.get("week_days", [])
                    print(f"加载周选择: {week_days}")
                    for i, check in enumerate(self.week_checks):
                        check.setChecked(i + 1 in week_days)
                
                # 设置每小时任务的间隔
                elif repeat_type == "每小时":
                    # 加载间隔小时数
                    interval_hours = config.get("interval_hours", 8)
                    print(f"加载每小时任务间隔: {interval_hours}小时")
                    self.interval_hours_spin.setValue(interval_hours)
                
                # 设置目标类型和目标
                target_type = config.get("target_type", "群聊")
                print(f"加载目标类型: {target_type}")
                self.target_type_combo.setCurrentText(target_type)
                
                # 目标可能需要等待目标类型变更事件触发后再设置
                target = config.get("target", "")
                print(f"加载目标: {target}")
                if target:
                    self.target_combo.setCurrentText(target)
                    print(f"设置目标为: {target}")
                
                # 设置消息内容
                message = config.get("message", "")
                print(f"加载消息内容: {message}")
                self.message_edit.setText(message)
                
                # 设置特殊消息类型
                self.weather_check.setChecked(config.get("send_weather", False))
                self.news_check.setChecked(config.get("send_news", False))
                print(f"加载特殊消息类型: 天气={config.get('send_weather', False)}, 新闻={config.get('send_news', False)}")
                
                # 设置城市
                city_code = config.get("city_code", "")
                if city_code and self.cities:
                    # 从城市代码反查城市名
                    city_name = None
                    for name, code in self.cities.items():
                        if code == city_code:
                            city_name = name
                            break
                    
                    if city_name:
                        self.city_combo.setCurrentText(city_name)
                        print(f"设置城市: {city_name} (代码: {city_code})")
                    else:
                        print(f"未找到城市代码 {city_code} 对应的城市名")
                
                # 如果勾选了天气选项，显示城市选择框
                if config.get("send_weather", False):
                    self.city_widget.show()
                else:
                    self.city_widget.hide()
                
                # 设置确认选项
                confirm = config.get("confirm", True)
                print(f"加载确认选项: {confirm}")
                self.confirm_check.setChecked(confirm)
                
                # 设置附件
                attachment = config.get("attachment", "")
                print(f"加载附件: {attachment}")
                if attachment:
                    # 保存完整路径
                    self.attachment_path = attachment
                    # 显示文件名
                    self.attachment_label.setText(os.path.basename(attachment))
                    # 更新预览
                    self.preview_label.setText(f"已选择: {os.path.basename(attachment)}")
                    print(f"设置附件为: {os.path.basename(attachment)}")
                else:
                    self.attachment_path = ""
                    self.attachment_label.setText("未选择文件")
                    self.preview_label.setText("预览区域")
                    print("未设置附件")
        except Exception as e:
            print(f"加载配置时出错: {e}")
            import traceback
            traceback.print_exc()
        
    def get_config(self) -> Dict:
        """获取配置"""
        try:
            # 获取重复方式
            repeat_type = self.repeat_combo.currentText()
            print(f"获取重复方式: {repeat_type}")
            
            # 获取时间
            hour = self.hour_spin.value()
            minute = self.min_spin.value()
            time_str = f"{hour:02d}:{minute:02d}"
            print(f"获取时间: {time_str}")
            
            # 获取目标类型和目标
            target_type = self.target_type_combo.currentText()
            target = self.target_combo.currentText()
            print(f"获取目标类型: {target_type}, 目标: {target}")
            
            # 获取特殊消息类型选项
            send_weather = self.weather_check.isChecked()
            send_news = self.news_check.isChecked()
            print(f"获取特殊消息类型: 天气={send_weather}, 新闻={send_news}")
            
            # 获取城市代码
            city_code = ""
            if send_weather:
                city_name = self.city_combo.currentText()
                if city_name in self.cities:
                    city_code = self.cities[city_name]
                    print(f"获取城市代码: {city_code} (城市: {city_name})")
                else:
                    print(f"警告: 未找到城市 '{city_name}' 的代码")
            
            # 根据重复方式构建不同的配置
            config = {
                "name": self.name_edit.text(),
                "type": "schedule",
                "time": time_str,
                "repeat_type": repeat_type,
                "target_type": target_type,
                "target": target,
                "message": self.message_edit.toPlainText(),
                "send_weather": send_weather,
                "send_news": send_news,
                "city_code": city_code,
                "confirm": self.confirm_check.isChecked(),
                "status": self.task_config.get("status", "stopped") if self.task_config else "stopped"
            }
            
            # 如果是群聊，需要将群名转换为群ID
            if target_type == "群聊":
                # 遍历groups字典查找对应的群ID
                target_wxid = None
                for wxid, name in self.groups.items():
                    if name == target:
                        target_wxid = wxid
                        config["target_wxid"] = wxid
                        print(f"已匹配群聊 '{target}' 的wxid: {wxid}")
                        break
                
                if not target_wxid:
                    print(f"警告: 未找到群聊 '{target}' 的wxid")
                    # 打印当前可用的群组列表以便调试
                    print(f"可用群组: {self.groups}")
                    
                    # 尝试保持原始的target_wxid
                    if self.task_config and "target_wxid" in self.task_config:
                        config["target_wxid"] = self.task_config["target_wxid"]
                        print(f"使用原始的target_wxid: {config['target_wxid']}")
            
            # 根据重复类型添加额外配置
            if repeat_type == "一次":
                date_str = self.date_calendar.selectedDate().toString("yyyy-MM-dd")
                config["date"] = date_str
                print(f"一次性任务日期: {date_str}")
            elif repeat_type == "每周":
                week_days = []
                for i, check in enumerate(self.week_checks):
                    if check.isChecked():
                        week_days.append(i + 1)  # 周一到周日: 1-7
                config["week_days"] = week_days
                print(f"每周任务选中的日期: {week_days}")
            elif repeat_type == "每小时":
                interval_hours = self.interval_hours_spin.value()
                # 确保interval_hours始终被添加到配置中
                config["interval_hours"] = interval_hours
                config["start_time"] = time_str  # 用时间设置作为首次执行时间
                print(f"每小时任务间隔: {interval_hours}小时，首次执行时间: {time_str}")
            
            # 添加附件路径 - 确保使用完整路径
            if hasattr(self, 'attachment_path') and self.attachment_path:
                # 规范化路径以确保正确处理Windows路径
                normalized_path = os.path.normpath(self.attachment_path)
                config["attachment"] = normalized_path
                print(f"配置中保存的附件路径: {normalized_path}")
                
                # 验证文件是否存在
                if os.path.exists(normalized_path):
                    print(f"文件存在，大小: {os.path.getsize(normalized_path)} 字节")
                else:
                    print(f"警告: 文件不存在！")
                    
                    # 尝试检查原始路径
                    if os.path.exists(self.attachment_path):
                        print(f"但原始路径存在，将使用原始路径: {self.attachment_path}")
                        config["attachment"] = self.attachment_path
                    else:
                        print(f"原始路径也不存在，这将导致发送失败")
            else:
                config["attachment"] = ""
                print("未设置附件")
                
            # 保留其他可能的属性
            if self.task_config:
                for key in ["last_state", "target_wxid"]:
                    if key in self.task_config and key not in config:
                        config[key] = self.task_config[key]
                        print(f"保留原始属性: {key} = {config[key]}")
                        
            print(f"最终配置: {config}")
            return config
        except Exception as e:
            print(f"获取配置时出错: {e}")
            import traceback
            traceback.print_exc()
            # 返回一个基本配置以防止崩溃
            return {
                "name": self.name_edit.text() or "错误配置",
                "type": "schedule",
                "time": "08:00",
                "repeat_type": "一次",
                "target_type": "群聊",
                "target": "",
                "message": "",
                "status": "stopped"
            }
        
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
        
        # 按当前选择的目标类型更新目标列表
        current_text = self.target_type_combo.currentText()
        self.on_target_type_changed(current_text)
        
        # 如果有配置，重新加载配置，确保显示正确的选择
        if self.task_config:
            self.load_config(self.task_config)
        
    def on_target_type_changed(self, text: str):
        """目标类型变化时更新相应的列表"""
        # 使用 target_type_combo 的当前文本来判断目标类型
        is_group = text == "群聊"
        self.target_combo.clear()
        
        if is_group:
            # 群聊列表
            if isinstance(self.groups, dict):
                for wxid, name in sorted(self.groups.items(), key=lambda x: x[1]):
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
                for contact in sorted(self.contacts, key=lambda x: x.get("remark", "") or x.get("name", "") or x.get("wxid", "")):
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
        
    def on_repeat_changed(self, text: str):
        """重复方式改变时更新界面"""
        if text == "一次":
            self.date_calendar.show()
            self.week_widget.hide()
            self.hourly_interval_widget.hide()
        elif text == "每天":
            self.date_calendar.hide()
            self.week_widget.hide()
            self.hourly_interval_widget.hide()
        elif text == "每周":
            self.date_calendar.hide()
            self.week_widget.show()
            self.hourly_interval_widget.hide()
        elif text == "每小时":
            self.date_calendar.hide()
            self.week_widget.hide()
            self.hourly_interval_widget.show()
            
    def select_attachment(self):
        """选择附件文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择附件", "", "所有文件 (*.*)")
        if file_path:
            try:
                # 规范化并保存完整路径
                normalized_path = os.path.normpath(file_path)
                self.attachment_path = normalized_path
                
                # 检查文件是否存在
                if os.path.exists(normalized_path):
                    file_size = os.path.getsize(normalized_path)
                    print(f"已选择附件: {normalized_path} (大小: {file_size} 字节)")
                    
                    # 显示文件名
                    self.attachment_label.setText(os.path.basename(normalized_path))
                    # 更新预览
                    self.preview_label.setText(f"已选择: {os.path.basename(normalized_path)}")
                else:
                    print(f"警告: 选择的文件不存在 {normalized_path}")
                    # 检查原始路径
                    if os.path.exists(file_path):
                        print(f"但原始路径存在: {file_path}，将使用原始路径")
                        self.attachment_path = file_path
                        file_size = os.path.getsize(file_path)
                        print(f"文件大小: {file_size} 字节")
                        
                        # 显示文件名
                        self.attachment_label.setText(os.path.basename(file_path))
                        # 更新预览
                        self.preview_label.setText(f"已选择: {os.path.basename(file_path)}")
                    else:
                        print(f"错误: 文件不存在，可能导致发送失败")
                        # 显示错误提示
                        self.attachment_label.setText("文件不存在!")
                        self.preview_label.setText("错误: 选择的文件不存在")
            except Exception as e:
                print(f"处理附件路径时出错: {str(e)}")
                import traceback
                traceback.print_exc()
                
                # 尝试使用原始路径
                self.attachment_path = file_path
                self.attachment_label.setText(os.path.basename(file_path))
                self.preview_label.setText(f"已选择: {os.path.basename(file_path)}")
                print(f"使用原始路径: {file_path}") 

    def ensure_city_dropdown(self):
        """确保城市下拉框能正常显示"""
        if hasattr(self, 'city_combo') and self.city_combo:
            # 记录日志
            print("尝试显示城市下拉列表")
            
            # 强制显示下拉列表
            try:
                self.city_combo.showPopup()
            except Exception as e:
                print(f"显示城市下拉列表时出错: {e}")
            
            # 确保下拉按钮连接正确
            if hasattr(self, 'city_dropdown_btn'):
                try:
                    self.city_dropdown_btn.clicked.disconnect()
                except:
                    pass
                self.city_dropdown_btn.clicked.connect(lambda: self.city_combo.showPopup()) 