#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import time
from datetime import datetime
import httpx
from openai import OpenAI
import json
import os

class Deepseek():
    def __init__(self, conf: dict) -> None:
        key = conf.get("key")
        api = conf.get("api")
        proxy = conf.get("proxy")
        prompt = conf.get("prompt")
        self.model = conf.get("model", "deepseek-chat")
        self.LOG = logging.getLogger("Deepseek")
        if proxy:
            self.client = OpenAI(api_key=key, base_url=api, http_client=httpx.Client(proxy=proxy))
        else:
            self.client = OpenAI(api_key=key, base_url=api)
        
        # 对话管理
        self.conversation_list = {}  # 当前对话
        self.conversation_summaries = {}  # 对话总结
        self.last_interaction_time = {}  # 最后交互时间
        self.conversation_timeout = 300  # 5分钟超时
        self.max_conversations = 10  # 最多保存10轮对话
        self.summary_file = "conversation_summaries.json"
        self.load_summaries()  # 加载历史总结
        
        # 角色设置
        self.role_settings = {
            "default": "你是一个智能AI助手，请用简洁专业的语言回答问题。",
            "teacher": "你是一位经验丰富的教师，擅长解答学术问题，并能够耐心指导学生。",
            "friend": "你是一位知心朋友，善于倾听和安慰，能够给出温暖的建议。",
            "expert": "你是一位专业领域的专家，能够提供深入的技术分析和建议。"
        }
        
        # 系统提示词
        self.system_content_msg = {"role": "system", "content": prompt}

    def __repr__(self):
        return 'Deepseek'

    @staticmethod
    def value_check(conf: dict) -> bool:
        if conf:
            if conf.get("key") and conf.get("api") and conf.get("prompt"):
                return True
        return False

    def get_answer(self, question: str, wxid: str) -> str:
        # 检查是否需要开始新的对话
        self.check_conversation_timeout(wxid)
        
        # 获取或创建对话历史
        if wxid not in self.conversation_list:
            self.conversation_list[wxid] = []
            # 添加系统提示词和角色设置
            role = self.get_user_role(wxid)
            self.conversation_list[wxid].append({
                "role": "system",
                "content": self.role_settings.get(role, self.role_settings["default"])
            })
            # 如果有历史总结，添加到对话中
            if wxid in self.conversation_summaries:
                self.conversation_list[wxid].append({
                    "role": "system",
                    "content": f"历史对话总结：{self.conversation_summaries[wxid]}"
                })

        # 添加用户问题
        self.conversation_list[wxid].append({"role": "user", "content": question})
        self.last_interaction_time[wxid] = time.time()

        try:
            ret = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_list[wxid],
                temperature=0.2
            )
            rsp = ret.choices[0].message.content
            rsp = rsp[2:] if rsp.startswith("\n\n") else rsp
            rsp = rsp.replace("\n\n", "\n")
            
            # 添加助手回复
            self.conversation_list[wxid].append({"role": "assistant", "content": rsp})
            
            # 如果对话轮数超过限制，移除最早的对话
            if len(self.conversation_list[wxid]) > self.max_conversations * 2 + 2:  # +2 是因为系统消息和总结
                self.conversation_list[wxid] = self.conversation_list[wxid][-self.max_conversations * 2:]
            
            return rsp
        except Exception as e0:
            self.LOG.error(f"发生未知错误：{str(e0)}")
            return "抱歉，我现在无法回答，请稍后再试。"

    def check_conversation_timeout(self, wxid: str) -> None:
        """检查对话是否超时，如果超时则进行总结"""
        if wxid in self.last_interaction_time:
            current_time = time.time()
            if current_time - self.last_interaction_time[wxid] > self.conversation_timeout:
                self.summarize_conversation(wxid)
                # 清空当前对话
                self.conversation_list[wxid] = []
                self.last_interaction_time[wxid] = current_time

    def summarize_conversation(self, wxid: str) -> None:
        """总结对话内容"""
        if wxid not in self.conversation_list or not self.conversation_list[wxid]:
            return

        try:
            # 构建总结提示
            summary_prompt = "请总结以下对话的主要内容，包括关键话题和重要信息：\n\n"
            for msg in self.conversation_list[wxid]:
                if msg["role"] != "system":
                    summary_prompt += f"{msg['role']}: {msg['content']}\n"

            # 获取总结
            ret = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": "你是一个专业的对话总结助手。"},
                         {"role": "user", "content": summary_prompt}],
                temperature=0.2
            )
            new_summary = ret.choices[0].message.content

            # 如果有历史总结，进行融合
            if wxid in self.conversation_summaries:
                fusion_prompt = f"请将以下两个对话总结进行融合，保留最重要的信息：\n\n历史总结：{self.conversation_summaries[wxid]}\n\n新总结：{new_summary}"
                ret = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": "你是一个专业的对话总结融合助手。"},
                             {"role": "user", "content": fusion_prompt}],
                    temperature=0.2
                )
                self.conversation_summaries[wxid] = ret.choices[0].message.content
            else:
                self.conversation_summaries[wxid] = new_summary

            # 保存总结
            self.save_summaries()
        except Exception as e:
            self.LOG.error(f"总结对话时发生错误：{str(e)}")

    def get_user_role(self, wxid: str) -> str:
        """获取用户角色设置"""
        # 这里可以根据wxid返回不同的角色
        # 例如：可以根据群组、用户ID等条件返回不同的角色
        return "default"

    def load_summaries(self) -> None:
        """加载历史对话总结"""
        try:
            if os.path.exists(self.summary_file):
                with open(self.summary_file, 'r', encoding='utf-8') as f:
                    self.conversation_summaries = json.load(f)
        except Exception as e:
            self.LOG.error(f"加载对话总结时发生错误：{str(e)}")

    def save_summaries(self) -> None:
        """保存对话总结"""
        try:
            with open(self.summary_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_summaries, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.LOG.error(f"保存对话总结时发生错误：{str(e)}")

    def chat(self, prompt: str, role: str = None, system_prompt: str = None) -> str:
        """直接对话，不保存对话历史
        Args:
            prompt: 提示词
            role: 角色设定，可选值：default, teacher, friend, expert
            system_prompt: 自定义系统提示词，如果提供则覆盖默认角色设定
        Returns:
            str: AI的回复
        """
        try:
            # 构建系统提示词
            if system_prompt:
                system_content = system_prompt
            elif role and role in self.role_settings:
                system_content = self.role_settings[role]
            else:
                system_content = self.role_settings["default"]
            
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ]
            
            ret = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2
            )
            rsp = ret.choices[0].message.content
            rsp = rsp[2:] if rsp.startswith("\n\n") else rsp
            rsp = rsp.replace("\n\n", "\n")
            return rsp
        except Exception as e:
            self.LOG.error(f"直接对话时发生错误：{str(e)}")
            return "抱歉，我现在无法回答，请稍后再试。"