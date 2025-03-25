import os
import json
from typing import Dict, List, Optional

class AISettings:
    def __init__(self, config_path="./config/ai_settings.json"):
        self.config_path = config_path
        self.settings = {
            "ai_enabled": False,  # 默认关闭AI功能
            "allowed_users": [],  # 允许使用AI的用户
            "allowed_groups": [],  # 允许自动回复的群组
            "user_roles": {},  # 用户角色提示词配置
            "auto_reply_keywords": ["收到回复", "收到请回复", "请回复", "回复"]  # 自动回复关键词
        }
        
        # 确保配置目录存在
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # 加载配置
        self.load_settings()
    
    def load_settings(self) -> bool:
        """加载设置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
                return True
            return False
        except Exception as e:
            print(f"加载AI设置失败: {e}")
            return False
    
    def save_settings(self) -> bool:
        """保存设置"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存AI设置失败: {e}")
            return False
    
    def toggle_ai(self, enabled: bool) -> bool:
        """开启或关闭AI"""
        try:
            self.settings["ai_enabled"] = enabled
            return self.save_settings()
        except Exception as e:
            print(f"切换AI状态失败: {e}")
            return False
    
    def add_user(self, wxid: str, name: str) -> bool:
        """添加允许使用AI的用户"""
        try:
            user_info = {"wxid": wxid, "name": name}
            if user_info not in self.settings["allowed_users"]:
                self.settings["allowed_users"].append(user_info)
                return self.save_settings()
            return True
        except Exception as e:
            print(f"添加用户失败: {e}")
            return False
    
    def remove_user(self, wxid: str) -> bool:
        """删除允许使用AI的用户"""
        try:
            self.settings["allowed_users"] = [
                user for user in self.settings["allowed_users"] 
                if user["wxid"] != wxid
            ]
            return self.save_settings()
        except Exception as e:
            print(f"删除用户失败: {e}")
            return False
    
    def get_users(self) -> List[Dict]:
        """获取允许使用AI的用户列表"""
        return self.settings["allowed_users"]
    
    def add_group(self, group_id: str, group_name: str) -> bool:
        """添加允许自动回复的群组"""
        try:
            group_info = {"wxid": group_id, "name": group_name}
            if group_info not in self.settings["allowed_groups"]:
                self.settings["allowed_groups"].append(group_info)
                return self.save_settings()
            return True
        except Exception as e:
            print(f"添加群组失败: {e}")
            return False
    
    def remove_group(self, group_id: str) -> bool:
        """删除允许自动回复的群组"""
        try:
            self.settings["allowed_groups"] = [
                group for group in self.settings["allowed_groups"] 
                if group["wxid"] != group_id
            ]
            return self.save_settings()
        except Exception as e:
            print(f"删除群组失败: {e}")
            return False
    
    def get_groups(self) -> List[Dict]:
        """获取允许自动回复的群组列表"""
        return self.settings["allowed_groups"]
    
    def set_user_role(self, wxid: str, role_prompt: str) -> bool:
        """设置用户角色提示词"""
        try:
            self.settings["user_roles"][wxid] = role_prompt
            return self.save_settings()
        except Exception as e:
            print(f"设置用户角色失败: {e}")
            return False
    
    def get_user_role(self, wxid: str) -> Optional[str]:
        """获取用户角色提示词"""
        return self.settings["user_roles"].get(wxid)
    
    def is_ai_enabled(self) -> bool:
        """AI是否启用"""
        return self.settings["ai_enabled"]
    
    def is_user_allowed(self, wxid: str) -> bool:
        """用户是否允许使用AI"""
        return any(user["wxid"] == wxid for user in self.settings["allowed_users"])
    
    def is_group_allowed(self, group_id: str) -> bool:
        """群组是否允许自动回复"""
        return any(group["wxid"] == group_id for group in self.settings["allowed_groups"])
    
    def get_auto_reply_keywords(self) -> List[str]:
        """获取自动回复关键词"""
        return self.settings["auto_reply_keywords"] 