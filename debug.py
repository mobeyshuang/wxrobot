#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试脚本，检查项目环境和导入问题
"""

import sys
import os
import traceback

# 确保项目根目录在sys.path中
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)
print(f"项目根目录: {project_root}")
print(f"Python路径: {sys.path}")

# 尝试导入ChatType
try:
    from constants import ChatType
    print(f"ChatType导入成功，可用常量: {dir(ChatType)}")
except Exception as e:
    print(f"ChatType导入失败: {e}")
    traceback.print_exc()

# 尝试导入Robot类
try:
    from robot import Robot
    print(f"Robot类导入成功")
    
    # 查看Robot.__init__的参数
    import inspect
    print(f"Robot.__init__参数: {inspect.signature(Robot.__init__)}")
except Exception as e:
    print(f"Robot类导入失败: {e}")
    traceback.print_exc()

# 尝试导入Config类
try:
    from configuration import Config
    print(f"Config类导入成功")
except Exception as e:
    print(f"Config类导入失败: {e}")
    traceback.print_exc()

# 尝试导入GUI模块
try:
    from gui import main_window, task_card, task_dialog, config_manager, task_executor
    print(f"GUI模块导入成功")
except Exception as e:
    print(f"GUI模块导入失败: {e}")
    traceback.print_exc()

# 列出项目根目录下的所有Python文件
print("\n项目根目录下的Python文件:")
for root, dirs, files in os.walk(project_root):
    for file in files:
        if file.endswith(".py"):
            print(os.path.join(root, file))

print("\n调试完成") 