import json
import os
from typing import Dict, List, Optional

class ConfigManager:
    def __init__(self):
        self.config_file = "tasks.json"
        self.tasks = self.load_config()
        
    def load_config(self) -> List[Dict]:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return []
            
    def save_config(self) -> bool:
        """保存配置文件"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
            
    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务"""
        return self.tasks
        
    def get_task(self, task_name: str) -> Optional[Dict]:
        """获取指定任务"""
        for task in self.tasks:
            if task["name"] == task_name:
                return task
        return None
        
    def add_task(self, task_config: Dict) -> bool:
        """添加任务"""
        try:
            # 检查任务名称是否已存在
            if self.get_task(task_config["name"]):
                return False
                
            self.tasks.append(task_config)
            return self.save_config()
        except Exception as e:
            print(f"添加任务失败: {e}")
            return False
            
    def update_task(self, task_name: str, task_config: Dict) -> bool:
        """更新任务"""
        try:
            # 查找任务
            for i, task in enumerate(self.tasks):
                if task["name"] == task_name:
                    self.tasks[i] = task_config
                    return self.save_config()
            return False
        except Exception as e:
            print(f"更新任务失败: {e}")
            return False
            
    def delete_task(self, task_name: str) -> bool:
        """删除任务"""
        try:
            # 查找任务
            for i, task in enumerate(self.tasks):
                if task["name"] == task_name:
                    del self.tasks[i]
                    return self.save_config()
            return False
        except Exception as e:
            print(f"删除任务失败: {e}")
            return False
            
    def import_config(self, file_path: str) -> bool:
        """导入配置"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                imported_tasks = json.load(f)
                
            # 检查任务名称是否重复
            existing_names = {task["name"] for task in self.tasks}
            for task in imported_tasks:
                if task["name"] in existing_names:
                    task["name"] = f"{task['name']}_导入"
                    
            self.tasks.extend(imported_tasks)
            return self.save_config()
        except Exception as e:
            print(f"导入配置失败: {e}")
            return False
            
    def export_config(self, file_path: str) -> bool:
        """导出配置"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"导出配置失败: {e}")
            return False
            
    def save_tasks(self, tasks: List[Dict]) -> bool:
        """保存任务列表"""
        try:
            self.tasks = tasks
            return self.save_config()
        except Exception as e:
            print(f"保存任务列表失败: {e}")
            return False 