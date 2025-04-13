from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QLineEdit, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
import os

class WeChatFileSettingsDialog(QDialog):
    """微信文件设置对话框"""
    
    # 定义信号，设置完成后发送
    settings_updated = pyqtSignal(str)
    
    def __init__(self, parent=None, current_path=None):
        super().__init__(parent)
        self.setWindowTitle("微信文件设置")
        self.resize(600, 150)
        self.current_path = current_path
        
        # 创建界面
        self.setup_ui()
        
    def setup_ui(self):
        """设置界面"""
        # 主布局
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # 提示标签
        tip_label = QLabel("请选择微信文件保存目录，到File级别，如:\n'D:\\WeChat Files\\微信号\\FileStorage\\File'")
        tip_label.setWordWrap(True)
        main_layout.addWidget(tip_label)
        
        # 目录选择区域
        dir_layout = QHBoxLayout()
        
        # 目录输入框
        self.dir_edit = QLineEdit()
        if self.current_path and os.path.exists(self.current_path):
            self.dir_edit.setText(self.current_path)
        dir_layout.addWidget(self.dir_edit, 3)
        
        # 选择按钮
        select_btn = QPushButton("选择目录")
        select_btn.clicked.connect(self.select_directory)
        dir_layout.addWidget(select_btn, 1)
        
        main_layout.addLayout(dir_layout)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        # 确认按钮
        confirm_btn = QPushButton("确认")
        confirm_btn.clicked.connect(self.confirm_settings)
        btn_layout.addWidget(confirm_btn)
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(btn_layout)
        
    def select_directory(self):
        """选择目录"""
        start_dir = self.dir_edit.text() if self.dir_edit.text() else "D:\\"
        
        directory = QFileDialog.getExistingDirectory(
            self, 
            "选择微信文件保存目录", 
            start_dir,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if directory:
            self.dir_edit.setText(directory)
    
    def confirm_settings(self):
        """确认设置"""
        selected_dir = self.dir_edit.text().strip()
        
        # 检查目录是否存在
        if not os.path.exists(selected_dir):
            QMessageBox.warning(self, "错误", "选择的目录不存在，请重新选择")
            return
            
        # 检查目录是否可能是有效的微信文件目录
        dir_name = os.path.basename(selected_dir)
        if dir_name != "File" and not ("FileStorage" in selected_dir):
            result = QMessageBox.question(
                self, 
                "确认", 
                "所选目录看起来不像标准的微信文件目录，是否仍要使用此目录？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if result != QMessageBox.Yes:
                return
        
        # 发送设置更新信号
        self.settings_updated.emit(selected_dir)
        self.accept() 