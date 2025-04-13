#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging.config
import os
import shutil
import json

import yaml


class Config(object):
    def __init__(self, config_path="config/config.json"):
        self.config_path = config_path
        self.AI_ENABLED = True
        self.GROUPS = []  # 允许的群组列表
        self.USERS = []   # 允许的用户列表
        self.TASK_GROUPS = []  # 任务相关的群组列表
        self.DEFAULT_ROLE = "一个友好、专业、有趣的AI助手"  # 默认角色
        self.DEEPSEEK = None  # Deepseek配置
        self.CHATGPT = None   # ChatGPT配置
        self.CHATGLM = None   # ChatGLM配置
        self.ZHIPU = None     # 智谱配置
        self.BARD = None      # Bard配置
        self.OLLAMA = None    # Ollama配置
        self.TIGERBOT = None  # TigerBot配置
        self.XINGHUO_WEB = None  # 星火Web配置
        self.reload()

    def _load_config(self) -> dict:
        pwd = os.path.dirname(os.path.abspath(__file__))
        try:
            with open(f"{pwd}/config.yaml", "rb") as fp:
                yconfig = yaml.safe_load(fp)
        except FileNotFoundError:
            shutil.copyfile(f"{pwd}/config.yaml.template", f"{pwd}/config.yaml")
            with open(f"{pwd}/config.yaml", "rb") as fp:
                yconfig = yaml.safe_load(fp)

        return yconfig

    def reload(self) -> None:
        """重新加载配置文件"""
        try:
            # 首先加载yaml配置
            yconfig = self._load_config_from_yaml()
            
            # 然后加载json配置，如果存在的话
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # 用json配置更新或补充yaml配置
                    self.AI_ENABLED = config.get("AI_ENABLED", True)
                    self.GROUPS = config.get("GROUPS", self.GROUPS)
                    self.USERS = config.get("USERS", self.USERS)
                    self.TASK_GROUPS = config.get("TASK_GROUPS", [])
                    
                    # 加载其他自定义配置项
                    for key, value in config.items():
                        if key not in ["AI_ENABLED", "GROUPS", "USERS", "TASK_GROUPS"]:
                            setattr(self, key, value)
            except Exception as e:
                logging.warning(f"加载JSON配置文件失败，将使用默认值: {e}")
                
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")

    def save(self) -> None:
        """保存配置到文件"""
        try:
            # 保存用户、群组和任务群组列表到json文件
            config = {
                "AI_ENABLED": self.AI_ENABLED,
                "GROUPS": self.GROUPS,
                "USERS": self.USERS,
                "TASK_GROUPS": self.TASK_GROUPS
            }
            
            # 添加WECHAT_FILES_DIR和其他自定义配置
            for attr in dir(self):
                if not attr.startswith("_") and not callable(getattr(self, attr)) and attr not in config and attr != "config_path":
                    value = getattr(self, attr)
                    # 只保存基本数据类型
                    if isinstance(value, (str, int, float, bool, list, dict)) or value is None:
                        config[attr] = value
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存配置文件失败: {e}")

    def get_groups(self) -> list:
        """获取允许的群组列表"""
        return self.GROUPS
    
    def get_task_groups(self) -> list:
        """获取任务相关的群组列表"""
        return self.TASK_GROUPS

    def add_group(self, group_id: str) -> bool:
        """添加群组到允许列表
        
        Args:
            group_id: 群组ID
            
        Returns:
            bool: 是否添加成功
        """
        if group_id not in self.GROUPS:
            self.GROUPS.append(group_id)
            self.save()
            return True
        return False

    def remove_group(self, group_id: str) -> bool:
        """从允许列表中移除群组
        
        Args:
            group_id: 群组ID
            
        Returns:
            bool: 是否删除成功
        """
        if group_id in self.GROUPS:
            self.GROUPS.remove(group_id)
            self.save()
            return True
        return False

    def get_users(self) -> list:
        """获取允许的用户列表"""
        return self.USERS

    def add_user(self, user_id: str) -> bool:
        """添加用户到允许列表"""
        if user_id not in self.USERS:
            self.USERS.append(user_id)
            self.save()
            return True
        return False

    def remove_user(self, user_id: str) -> bool:
        """从允许列表中移除用户"""
        if user_id in self.USERS:
            self.USERS.remove(user_id)
            self.save()
            return True
        return False

    def is_user_allowed(self, user_id: str) -> bool:
        """检查用户是否在允许列表中"""
        return user_id in self.USERS

    def _load_config_from_yaml(self) -> dict:
        """从yaml文件加载配置"""
        yconfig = self._load_config()
        logging.config.dictConfig(yconfig["logging"])
        
        # 基础配置
        self.CITY_CODE = yconfig["weather"]["city_code"]
        self.WEATHER = yconfig["weather"]["receivers"]
        self.NEWS = yconfig["news"]["receivers"]
        self.REPORT_REMINDERS = yconfig["report_reminder"]["receivers"]
        self.GROUPS = yconfig["groups"].get("enable", [])
        
        # AI模型配置
        self.DEEPSEEK = yconfig.get("deepseek", {})
        if "role" in self.DEEPSEEK:
            self.DEFAULT_ROLE = self.DEEPSEEK["role"]
        
        self.CHATGPT = yconfig.get("chatgpt", {})
        self.OLLAMA = yconfig.get("ollama", {})
        self.TIGERBOT = yconfig.get("tigerbot", {})
        self.XINGHUO_WEB = yconfig.get("xinghuo_web", {})
        self.CHATGLM = yconfig.get("chatglm", {})
        self.BARD = yconfig.get("bard", {})
        self.ZHIPU = yconfig.get("zhipu", {})
        
        # 其他配置
        self.SEND_RATE_LIMIT = yconfig.get("send_rate_limit", 0)
        
        return yconfig

    def get_default_role(self) -> str:
        """获取默认角色设定"""
        return self.DEFAULT_ROLE
        
    def get(self, key, default=None):
        """获取配置项
        
        Args:
            key: 配置项名称
            default: 默认值，如果配置项不存在
            
        Returns:
            配置项值或默认值
        """
        return getattr(self, key, default)
        
    def set(self, key, value):
        """设置配置项
        
        Args:
            key: 配置项名称
            value: 配置项值
            
        Returns:
            bool: 是否设置成功
        """
        try:
            setattr(self, key, value)
            self.save()
            return True
        except Exception as e:
            logging.error(f"设置配置项失败: {e}")
            return False

