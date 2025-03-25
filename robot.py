# -*- coding: utf-8 -*-

import logging
import re
import time
import xml.etree.ElementTree as ET
from queue import Empty
from threading import Thread
from base.func_zhipu import ZhiPu
from base.func_time import get_time
from base.func_deepseek import Deepseek

from wcferry import Wcf, WxMsg

from base.func_bard import BardAssistant
from base.func_chatglm import ChatGLM
from base.func_ollama import Ollama
from base.func_chatgpt import ChatGPT
from base.func_chengyu import cy
from base.func_weather import Weather
from base.func_news import News
from base.func_tigerbot import TigerBot
from base.func_xinghuo_web import XinghuoWeb
from configuration import Config
from constants import ChatType
from job_mgmt import Job
import os
import json

__version__ = "39.2.4.0"


class Robot(Job):
    """个性化自己的机器人
    """

    def __init__(self, config: Config, wcf: Wcf, chat_type: int) -> None:
        self.wcf = wcf
        self.config = config
        self.LOG = logging.getLogger("Robot")
        self.wxid = self.wcf.get_self_wxid()
        
        # 获取并存储所有联系人信息
        self.contacts = self.wcf.get_contacts()
        # 获取并存储所有群组信息
        self.allGroups = self.getAllGroups()
        # 首次更新配置
        self.config.reload()
        self.LOG.info("已完成首次配置和联系人信息更新")
        
        self._msg_timestamps = []
        self.chat = None
        self.chat_type = chat_type
        self._user_states = {}  # 用于跟踪用户的设置状态
        self._user_roles = {}   # 用户角色设置
        self._chat_history = {} # 用户对话历史
        self._last_chat_time = {} # 用户最后对话时间
        
        # 加载已保存的用户角色设置
        self._load_user_roles()
        
        # 根据 chat_type 选择对应的模型
        if chat_type == ChatType.DEEPSEEK:
            if Deepseek.value_check(config.DEEPSEEK):
                self.chat = Deepseek(config.DEEPSEEK)
                self.LOG.info("已选择: Deepseek")
            else:
                self.LOG.warning("Deepseek 配置无效")
        elif chat_type == ChatType.CHATGPT:
            if ChatGPT.value_check(config.CHATGPT):
                self.chat = ChatGPT(config.CHATGPT)
                self.LOG.info("已选择: ChatGPT")
            else:
                self.LOG.warning("ChatGPT 配置无效")
        elif chat_type == ChatType.CHATGLM:
            if ChatGLM.value_check(config.CHATGLM):
                self.chat = ChatGLM(config.CHATGLM)
                self.LOG.info("已选择: ChatGLM")
            else:
                self.LOG.warning("ChatGLM 配置无效")
        elif chat_type == ChatType.ZHIPU:
            if ZhiPu.value_check(config.ZhiPu):
                self.chat = ZhiPu(config.ZhiPu)
                self.LOG.info("已选择: ZhiPu")
            else:
                self.LOG.warning("ZhiPu 配置无效")
        elif chat_type == ChatType.BARD:
            if BardAssistant.value_check(config.BardAssistant):
                self.chat = BardAssistant(config.BardAssistant)
                self.LOG.info("已选择: Bard")
            else:
                self.LOG.warning("Bard 配置无效")
        elif chat_type == ChatType.OLLAMA:
            if Ollama.value_check(config.OLLAMA):
                self.chat = Ollama(config.OLLAMA)
                self.LOG.info("已选择: Ollama")
            else:
                self.LOG.warning("Ollama 配置无效")
        elif chat_type == ChatType.TIGERBOT:
            if TigerBot.value_check(config.TIGERBOT):
                self.chat = TigerBot(config.TIGERBOT)
                self.LOG.info("已选择: TigerBot")
            else:
                self.LOG.warning("TigerBot 配置无效")
        elif chat_type == ChatType.XINGHUO_WEB:
            if XinghuoWeb.value_check(config.XINGHUO_WEB):
                self.chat = XinghuoWeb(config.XINGHUO_WEB)
                self.LOG.info("已选择: XinghuoWeb")
            else:
                self.LOG.warning("XinghuoWeb 配置无效")
        else:
            self.LOG.warning("未选择有效的模型")

    @staticmethod
    def value_check(args: dict) -> bool:
        if args:
            return all(value is not None for key, value in args.items() if key != 'proxy')
        return False

    def toAt(self, msg: WxMsg) -> bool:
        """处理被 @ 消息
        :param msg: 微信消息结构
        :return: 处理状态，`True` 成功，`False` 失败
        """
        # 获取用户ID
        user_id = msg.roomid if msg.from_group() else msg.sender
        
        # 检查是否允许该用户使用AI
        if not self.config.AI_ENABLED or not self.config.is_user_allowed(user_id):
            return False
            
        return self.toChitchat(msg)

    def toChengyu(self, msg: WxMsg) -> bool:
        """
        处理成语查询/接龙消息
        :param msg: 微信消息结构
        :return: 处理状态，`True` 成功，`False` 失败
        """
        status = False
        texts = re.findall(r"^([#?？])(.*)$", msg.content)
        # [('#', '天天向上')]
        if texts:
            flag = texts[0][0]
            text = texts[0][1]
            if flag == "#":  # 接龙
                if cy.isChengyu(text):
                    rsp = cy.getNext(text)
                    if rsp:
                        self.sendTextMsg(rsp, msg.roomid)
                        status = True
            elif flag in ["?", "？"]:  # 查词
                if cy.isChengyu(text):
                    rsp = cy.getMeaning(text)
                    if rsp:
                        self.sendTextMsg(rsp, msg.roomid)
                        status = True

        return status

    def toChitchat(self, msg: WxMsg) -> bool:
        """闲聊，接入 AI 模型
        """
        # 获取用户ID
        user_id = msg.roomid if msg.from_group() else msg.sender
        
        # 检查是否启用AI且用户在允许列表中
        if not self.config.AI_ENABLED or not self.config.is_user_allowed(user_id):
            return False
            
        if not self.chat:  # 没有配置AI模型
            self.LOG.warning("未配置AI模型")
            return False
            
        try:
            # 获取用户角色和对话上下文
            user_role = self._get_user_role(user_id)
            chat_context = self._get_chat_context(user_id)
            
            # 处理消息内容
            q = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")
            
            # 构建带有角色和上下文的提示
            prompt = f"你的角色是: {user_role}\n\n"
            if chat_context:
                prompt += f"对话历史:\n{chat_context}\n\n"
            prompt += f"用户: {q}"
            
            # 记录用户消息
            self._manage_chat_history(user_id, q, True)
            
            # 获取AI回答
            rsp = self.chat.get_answer(prompt, user_id)
            
            # 记录AI回答
            if rsp:
                self._manage_chat_history(user_id, rsp, False)
                # 发送回复
                if msg.from_group():
                    self.sendTextMsg(rsp, msg.roomid)
                else:
                    self.sendTextMsg(rsp, msg.sender)
                return True
            else:
                self.LOG.error(f"无法从AI获得答案")
                return False
                
        except Exception as e:
            self.LOG.error(f"处理聊天消息时出错: {e}")
            return False

    def processMsg(self, msg: WxMsg) -> None:
        """当接收到消息的时候，会调用本方法。如果不实现本方法，则打印原始消息。
        此处可进行自定义发送的内容,如通过 msg.content 关键字自动获取当前天气信息，并发送到对应的群组@发送者
        群号：msg.roomid  微信ID：msg.sender  消息内容：msg.content
        """
        # 检查是否是本人发送的消息且在设置状态
        if msg.from_self():
            if msg.content.strip() == "^设置":
                self.LOG.info("收到本人发送的^设置命令")
                self._handle_settings(msg.sender)
                return
            elif msg.content.strip() == "^更新$":
                self.update_contact_info()
                self.config.reload()
                self.LOG.info("已更新配置和联系人信息")
                return
            elif msg.sender in self._user_states:
                self._handle_setting_response(msg)
                return

        # 群聊消息
        if msg.from_group():
            # 如果在群里被 @ 或者是配置的群组
            if msg.roomid in self.config.get_groups():
                # 检查是否被@或者@所有人
                if msg.is_at(self.wxid) or "@所有人" in msg.content:
                    # 检查消息内容是否包含特定关键词
                    keywords = ["收到回复", "收到请回复", "请回复收到", "请回复", "回复收到", "回复"]
                    content = msg.content.lower()
                    if any(keyword in content for keyword in keywords):
                        self.sendTextMsg("收到", msg.roomid)  # 移除@发送者
                        return
                    
                    # 如果不是特定关键词，则按正常@消息处理
                    self.toAt(msg)
                else:  # 其他消息
                    self.toChengyu(msg)
            return

        # 非群聊信息，按消息类型进行处理
        if msg.type == 37:  # 好友请求
            self.autoAcceptFriendRequest(msg)
        elif msg.type == 10000:  # 系统信息
            self.sayHiToNewFriend(msg)
        elif msg.type == 0x01:  # 文本消息
            if msg.from_self():
                if msg.content == "^更新$":
                    self.config.reload()
                    self.LOG.info("已更新")
            else:
                self.toChitchat(msg)  # 闲聊

    def _handle_settings(self, sender: str) -> None:
        """处理设置命令"""
        ai_status = "开启 ✅" if self.config.AI_ENABLED else "关闭 ❌"
        menu = f"""【微信机器人设置】
当前AI回答状态：{ai_status}

请回复数字选择功能:
1. 开启AI
2. 关闭AI
3. 添加用户
4. 删除用户
5. 查看用户列表
6. 添加群组
7. 删除群组
8. 查看群组列表
9. 查看用户角色
10. 设置用户角色
0. 退出设置"""
        
        # 重置用户状态为等待选项
        self._user_states[sender] = {"state": "waiting_for_option"}
        self.sendTextMsg(menu, sender)

    def _handle_setting_response(self, msg: WxMsg) -> None:
        """处理用户对设置的响应"""
        sender = msg.sender
        content = msg.content.strip()
        state = self._user_states.get(sender, {}).get("state")
        
        if state == "waiting_for_option":
            if content == "0":  # 退出设置
                self.sendTextMsg("已退出设置 ✅", sender)
                del self._user_states[sender]
            elif content == "1":  # 开启AI
                self.config.AI_ENABLED = True
                self.sendTextMsg("已开启AI功能 ✅", sender)
                self._handle_settings(sender)  # 返回菜单
            elif content == "2":  # 关闭AI
                self.config.AI_ENABLED = False
                self.sendTextMsg("已关闭AI功能 ✅", sender)
                self._handle_settings(sender)  # 返回菜单
            elif content == "3":  # 添加用户
                self._user_states[sender] = {"state": "waiting_for_add_user"}
                self.sendTextMsg("请发送要添加的用户微信号或名片", sender)
            elif content == "4":  # 删除用户
                users = self.config.get_users()
                if not users:
                    self.sendTextMsg("当前没有允许使用AI的用户", sender)
                    self._handle_settings(sender)  # 返回菜单
                    return
                user_list = "当前用户列表：\n"
                for i, user in enumerate(users, 1):
                    display_name = self._get_user_display_name(user)
                    user_list += f"{i}. {display_name}\n"
                user_list += "\n请回复序号删除对应用户"
                self._user_states[sender] = {"state": "waiting_for_delete_user", "users": users}
                self.sendTextMsg(user_list, sender)
            elif content == "5":  # 查看用户列表
                users = self.config.get_users()
                if not users:
                    self.sendTextMsg("当前没有允许使用AI的用户", sender)
                else:
                    user_list = "当前允许使用AI的用户列表：\n"
                    for i, user in enumerate(users, 1):
                        display_name = self._get_user_display_name(user)
                        role = self._get_user_role(user)
                        user_list += f"{i}. {display_name}\n   角色: {role}\n"
                    self.sendTextMsg(user_list, sender)
                self._handle_settings(sender)  # 返回菜单
            elif content == "6":  # 添加群组
                self._user_states[sender] = {"state": "waiting_for_add_group"}
                self.sendTextMsg("请发送要添加的群名称，我会自动匹配群ID", sender)
            elif content == "7":  # 删除群组
                groups = self.config.get_groups()
                if not groups:
                    self.sendTextMsg("当前没有配置的群组", sender)
                    self._handle_settings(sender)  # 返回菜单
                    return
                group_list = "当前群组列表：\n"
                for i, group_id in enumerate(groups, 1):
                    group_name = self.allGroups.get(group_id, group_id)
                    group_list += f"{i}. {group_name} ({group_id})\n"
                group_list += "\n请回复序号删除对应群组"
                self._user_states[sender] = {"state": "waiting_for_delete_group", "groups": groups}
                self.sendTextMsg(group_list, sender)
            elif content == "8":  # 查看群组列表
                groups = self.config.get_groups()
                if not groups:
                    self.sendTextMsg("当前没有配置的群组", sender)
                else:
                    group_list = "当前配置的群组列表：\n"
                    for i, group_id in enumerate(groups, 1):
                        group_name = self.allGroups.get(group_id, group_id)
                        group_list += f"{i}. {group_name} ({group_id})\n"
                    self.sendTextMsg(group_list, sender)
                self._handle_settings(sender)  # 返回菜单
            elif content == "9":  # 查看用户角色
                users = self.config.get_users()
                if not users:
                    self.sendTextMsg("当前没有允许使用AI的用户", sender)
                else:
                    role_list = "当前用户角色列表：\n"
                    for i, user in enumerate(users, 1):
                        display_name = self._get_user_display_name(user)
                        role = self._get_user_role(user)
                        role_list += f"{i}. {display_name}\n   角色: {role}\n"
                    self.sendTextMsg(role_list, sender)
                self._handle_settings(sender)  # 返回菜单
            elif content == "10":  # 设置用户角色
                users = self.config.get_users()
                if not users:
                    self.sendTextMsg("当前没有允许使用AI的用户", sender)
                    self._handle_settings(sender)  # 返回菜单
                    return
                user_list = "请选择要设置角色的用户（回复序号）：\n"
                for i, user in enumerate(users, 1):
                    display_name = self._get_user_display_name(user)
                    role = self._get_user_role(user)
                    user_list += f"{i}. {display_name}\n   当前角色: {role}\n"
                self._user_states[sender] = {"state": "waiting_for_select_user_role", "users": users}
                self.sendTextMsg(user_list, sender)
            else:
                self.sendTextMsg("无效的选项，请重新输入", sender)
                
        elif state == "waiting_for_add_user":
            # 处理添加用户
            if content:  # 只要不是空内容就尝试添加
                # 先尝试根据输入查找匹配的联系人
                user_id = content  # 默认使用输入内容作为用户ID
                
                # 通过输入的昵称、微信号或备注名查找用户
                matched_users = []
                for contact in self.contacts:
                    # 完全匹配wxid
                    if contact.get("wxid") == content:
                        user_id = contact.get("wxid")
                        matched_users = [contact]
                        break
                    # 匹配微信号
                    elif contact.get("code") and contact.get("code").lower() == content.lower():
                        user_id = contact.get("wxid")
                        matched_users = [contact]
                        break
                    # 匹配昵称或备注名
                    elif (contact.get("name") and content.lower() in contact.get("name").lower()) or \
                         (contact.get("remark") and content.lower() in contact.get("remark").lower()):
                        matched_users.append(contact)
                
                # 处理匹配结果
                if len(matched_users) == 0:
                    # 没有找到匹配的联系人
                    self.sendTextMsg(f"未找到匹配的联系人: {content}", sender)
                elif len(matched_users) == 1:
                    # 只找到一个匹配的联系人，直接添加
                    user_id = matched_users[0].get("wxid")
                    display_name = self._get_user_display_name(user_id)
                    
                    if self.config.add_user(user_id):
                        self.sendTextMsg(f"已成功添加用户: {display_name}（{user_id}） ✅", sender)
                    else:
                        self.sendTextMsg(f"添加用户失败，该用户可能已在列表中", sender)
                else:
                    # 找到多个匹配的联系人，让用户选择
                    user_list = "找到多个匹配的联系人，请回复序号选择要添加的用户：\n"
                    for i, contact in enumerate(matched_users, 1):
                        name = contact.get("remark") or contact.get("name") or contact.get("wxid")
                        user_list += f"{i}. {name} ({contact.get('wxid')})\n"
                    
                    self._user_states[sender] = {
                        "state": "waiting_for_select_user",
                        "matched_users": matched_users
                    }
                    self.sendTextMsg(user_list, sender)
                    return  # 不返回菜单，等待用户选择
            else:
                self.sendTextMsg("请输入有效的微信昵称、微信号或备注名", sender)
            self._handle_settings(sender)  # 返回菜单
            
        elif state == "waiting_for_select_user":
            # 处理用户选择
            try:
                matched_users = self._user_states[sender].get("matched_users", [])
                idx = int(content) - 1
                if 0 <= idx < len(matched_users):
                    user_id = matched_users[idx].get("wxid")
                    display_name = self._get_user_display_name(user_id)
                    
                    if self.config.add_user(user_id):
                        self.sendTextMsg(f"已成功添加用户: {display_name}（{user_id}） ✅", sender)
                    else:
                        self.sendTextMsg(f"添加用户失败，该用户可能已在列表中", sender)
                else:
                    self.sendTextMsg("无效的序号，请重新输入", sender)
            except ValueError:
                self.sendTextMsg("请输入有效的数字", sender)
            self._handle_settings(sender)  # 返回菜单
            
        elif state == "waiting_for_delete_user":
            # 处理删除用户
            try:
                users = self._user_states[sender].get("users", [])
                idx = int(content) - 1
                if 0 <= idx < len(users):
                    user = users[idx]
                    display_name = self._get_user_display_name(user)
                    if self.config.remove_user(user):
                        # 同时删除用户角色设置
                        if user in self._user_roles:
                            del self._user_roles[user]
                            self._save_user_roles()
                        remaining_users = self.config.get_users()
                        response = f"已成功删除用户: {display_name} ✅\n"
                        if remaining_users:
                            user_list = ""
                            for i, u in enumerate(remaining_users, 1):
                                display = self._get_user_display_name(u)
                                user_list += f"{i}. {display}\n"
                            response += f"当前用户列表：\n{user_list}"
                        else:
                            response += "当前没有配置的用户"
                        self.sendTextMsg(response, sender)
                    else:
                        self.sendTextMsg(f"删除用户 {display_name} 失败", sender)
                else:
                    self.sendTextMsg("无效的序号，请重新输入", sender)
            except ValueError:
                self.sendTextMsg("请输入有效的数字", sender)
            self._handle_settings(sender)  # 返回菜单
            
        elif state == "waiting_for_add_group":
            # 处理添加群组
            group_name = content.strip()
            # 在allGroups中查找匹配的群组
            found_groups = [(gid, name) for gid, name in self.allGroups.items() 
                          if group_name.lower() in name.lower()]
            
            if not found_groups:
                self.sendTextMsg(f"未找到名称包含 '{group_name}' 的群组", sender)
                self._handle_settings(sender)  # 返回菜单
            elif len(found_groups) == 1:
                # 只找到一个匹配的群组，直接添加
                group_id, group_name = found_groups[0]
                if self.config.add_group(group_id):
                    self.sendTextMsg(f"已成功添加群组：{group_name} ({group_id}) ✅", sender)
                else:
                    self.sendTextMsg(f"添加群组失败，该群组可能已在列表中", sender)
                self._handle_settings(sender)  # 返回菜单
            else:
                # 找到多个匹配的群组，让用户选择
                group_list = "找到多个匹配的群组，请回复序号选择要添加的群组：\n"
                for i, (gid, name) in enumerate(found_groups, 1):
                    group_list += f"{str(i)}. {name} ({gid})\n"
                self._user_states[sender] = {
                    "state": "waiting_for_select_group",
                    "groups": found_groups
                }
                self.sendTextMsg(group_list, sender)
                
        elif state == "waiting_for_select_group":
            # 处理群组选择
            try:
                found_groups = self._user_states[sender].get("groups", [])
                idx = int(content) - 1
                if 0 <= idx < len(found_groups):
                    group_id, group_name = found_groups[idx]
                    if self.config.add_group(group_id):
                        self.sendTextMsg(f"已成功添加群组：{group_name} ({group_id}) ✅", sender)
                    else:
                        self.sendTextMsg(f"添加群组失败，该群组可能已在列表中", sender)
                else:
                    self.sendTextMsg("无效的序号，请重新输入", sender)
            except ValueError:
                self.sendTextMsg("请输入有效的数字", sender)
            self._handle_settings(sender)  # 返回菜单
            
        elif state == "waiting_for_delete_group":
            # 处理删除群组
            try:
                groups = self._user_states[sender].get("groups", [])
                idx = int(content) - 1
                if 0 <= idx < len(groups):
                    group_id = groups[idx]
                    group_name = self.allGroups.get(group_id, group_id)
                    if self.config.remove_group(group_id):
                        remaining_groups = self.config.get_groups()
                        response = f"已成功删除群组：{group_name} ({group_id}) ✅\n"
                        if remaining_groups:
                            response += "当前群组列表：\n"
                            for i, gid in enumerate(remaining_groups, 1):
                                gname = self.allGroups.get(gid, gid)
                                response += f"{str(i)}. {gname} ({gid})\n"
                        else:
                            response += "当前没有配置的群组"
                        self.sendTextMsg(response, sender)
                    else:
                        self.sendTextMsg(f"删除群组失败", sender)
                else:
                    self.sendTextMsg("无效的序号，请重新输入", sender)
            except ValueError:
                self.sendTextMsg("请输入有效的数字", sender)
            self._handle_settings(sender)  # 返回菜单
            
        elif state == "waiting_for_select_user_role":
            try:
                users = self._user_states[sender].get("users", [])
                idx = int(content) - 1
                if 0 <= idx < len(users):
                    selected_user = users[idx]
                    self._user_states[sender] = {
                        "state": "waiting_for_input_role",
                        "selected_user": selected_user
                    }
                    current_role = self._get_user_role(selected_user)
                    self.sendTextMsg(
                        f"请输入新的角色设定（当前角色：{current_role}）\n"
                        "建议包含角色身份、性格特点、专业领域等信息",
                        sender
                    )
                else:
                    self.sendTextMsg("无效的序号，请重新输入", sender)
            except ValueError:
                self.sendTextMsg("请输入有效的数字", sender)
                self._handle_settings(sender)  # 返回菜单
                
        elif state == "waiting_for_input_role":
            selected_user = self._user_states[sender].get("selected_user")
            if selected_user:
                self._user_roles[selected_user] = content
                self._save_user_roles()
                display_name = self._get_user_display_name(selected_user)
                self.sendTextMsg(f"已为用户 {display_name} 设置新角色 ✅", sender)
            else:
                self.sendTextMsg("设置失败，未找到选择的用户", sender)
            self._handle_settings(sender)  # 返回菜单

    def onMsg(self, msg: WxMsg) -> int:
        try:
            # 打印消息内容
            self.LOG.info(f"收到消息: {msg}")
            self.processMsg(msg)
        except Exception as e:
            self.LOG.error(e)

        return 0

    def enableRecvMsg(self) -> None:
        self.wcf.enable_recv_msg(self.onMsg)

    def enableReceivingMsg(self) -> None:
        def innerProcessMsg(wcf: Wcf):
            while wcf.is_receiving_msg():
                try:
                    msg = wcf.get_msg()
                    self.LOG.info(msg)
                    self.processMsg(msg)
                except Empty:
                    continue  # Empty message
                except Exception as e:
                    self.LOG.error(f"Receiving message error: {e}")

        self.wcf.enable_receiving_msg()
        Thread(target=innerProcessMsg, name="GetMessage", args=(self.wcf,), daemon=True).start()

    def sendTextMsg(self, msg: str, receiver: str, at_list: str = "") -> None:
        """ 发送消息
        :param msg: 消息字符串
        :param receiver: 接收人wxid或者群id
        :param at_list: 要@的wxid, @所有人的wxid为：notify@all
        """
        # 随机延迟0.3-1.3秒，并且一分钟内发送限制
        time.sleep(float(str(time.time()).split('.')[-1][-2:]) / 100.0 + 0.3)
        now = time.time()
        
        # 检查是否是发送给自己或文件传输助手的消息
        is_self_or_filehelper = receiver == self.wxid or receiver == "filehelper"
        
        if self.config.SEND_RATE_LIMIT > 0 and not is_self_or_filehelper:
            # 清除超过1分钟的记录
            self._msg_timestamps = [t for t in self._msg_timestamps if now - t < 60]
            if len(self._msg_timestamps) >= self.config.SEND_RATE_LIMIT:
                self.LOG.warning(f"发送消息过快，已达到每分钟{str(self.config.SEND_RATE_LIMIT)}条上限。")
                return
            self._msg_timestamps.append(now)

        # msg 中需要有 @ 名单中一样数量的 @
        ats = ""
        if at_list:
            if at_list == "notify@all":  # @所有人
                ats = " @所有人"
            else:
                wxids = at_list.split(",")
                for wxid in wxids:
                    # 根据 wxid 查找群昵称
                    ats += f" @{self.wcf.get_alias_in_chatroom(wxid, receiver)}"

        # {msg}{ats} 表示要发送的消息内容后面紧跟@，例如 北京天气情况为：xxx @张三
        if ats == "":
            self.LOG.info(f"To {receiver}: {msg}")
            self.wcf.send_text(f"{msg}", receiver, at_list)
        else:
            self.LOG.info(f"To {receiver}: {ats}\r{msg}")
            self.wcf.send_text(f"{ats}\n\n{msg}", receiver, at_list)

    def getAllGroups(self) -> dict:
        """
        获取群组（包括好友、公众号、服务号、群成员……）
        格式: {"wxid": "NickName"}
        """
        groups = self.wcf.query_sql("MicroMsg.db", "SELECT UserName, NickName FROM Contact;")
        return {contact["UserName"]: contact["NickName"] for contact in groups}

    def keepRunningAndBlockProcess(self) -> None:
        """
        保持机器人运行，不让进程退出
        """
        while True:
            self.runPendingJobs()
            time.sleep(1)

    def autoAcceptFriendRequest(self, msg: WxMsg) -> None:
        try:
            xml = ET.fromstring(msg.content)
            v3 = xml.attrib["encryptusername"]
            v4 = xml.attrib["ticket"]
            scene = int(xml.attrib["scene"])
            self.wcf.accept_new_friend(v3, v4, scene)

        except Exception as e:
            self.LOG.error(f"同意好友出错：{e}")

    def sayHiToNewFriend(self, msg: WxMsg) -> None:
        nickName = re.findall(r"你已添加了(.*)，现在可以开始聊天了。", msg.content)
        if nickName:
            # 添加了好友，更新好友列表
            self.allGroups[msg.sender] = nickName[0]
            self.sendTextMsg(f"Hi {nickName[0]}，我自动通过了你的好友请求。", msg.sender)

    def newsReport(self) -> None:
        receivers = self.config.NEWS
        if not receivers:
            return

        news = News().get_important_news()
        for r in receivers:
            self.sendTextMsg(news, r)

    def weatherReport(self, receivers: list) -> None:
        if not receivers or not self.config.CITY_CODE:
            self.LOG.warning("未配置天气城市代码或接收人")
            return

        report = Weather(self.config.CITY_CODE).get_weather()
        for r in receivers:
            self.sendTextMsg(report, r)

    def _load_user_roles(self) -> None:
        """从文件加载用户角色设置"""
        try:
            role_file = os.path.join(os.path.dirname(self.config.config_path), "user_roles.json")
            if os.path.exists(role_file):
                with open(role_file, "r", encoding="utf-8") as f:
                    self._user_roles = json.load(f)
        except Exception as e:
            self.LOG.error(f"加载用户角色设置失败: {e}")
            self._user_roles = {}

    def _save_user_roles(self) -> None:
        """保存用户角色设置到文件"""
        try:
            role_file = os.path.join(os.path.dirname(self.config.config_path), "user_roles.json")
            with open(role_file, "w", encoding="utf-8") as f:
                json.dump(self._user_roles, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.LOG.error(f"保存用户角色设置失败: {e}")

    def _get_user_display_name(self, user_id: str) -> str:
        """获取用户显示名称
        优先使用备注名，其次使用昵称，最后使用微信ID
        """
        try:
            # 从contacts列表中查找用户信息
            for contact in self.contacts:
                if contact.get("wxid") == user_id:
                    # 优先使用备注名
                    if contact.get("remark"):
                        return contact["remark"]
                    # 其次使用昵称
                    elif contact.get("name"):
                        return contact["name"]
                    break
        except Exception as e:
            self.LOG.warning(f"获取用户 {user_id} 信息失败: {e}")
        
        # 如果未找到匹配的联系人信息，尝试使用SQL查询
        try:
            contact_info = self.wcf.query_sql("MicroMsg.db", f"SELECT NickName, Remark FROM Contact WHERE UserName = '{user_id}';")
            if contact_info and len(contact_info) > 0:
                # 优先使用备注名
                if contact_info[0].get("Remark"):
                    return contact_info[0]["Remark"]
                # 其次使用昵称
                elif contact_info[0].get("NickName"):
                    return contact_info[0]["NickName"]
        except Exception as e:
            self.LOG.warning(f"SQL查询获取用户 {user_id} 信息失败: {e}")
        
        # 如果获取失败，返回用户ID
        return user_id

    def _get_user_role(self, user_id: str) -> str:
        """获取用户角色，如果未设置则返回默认角色"""
        return self._user_roles.get(user_id, self.config.get_default_role())

    def _manage_chat_history(self, user_id: str, message: str, is_user: bool = True):
        """管理用户对话历史
        
        Args:
            user_id: 用户ID
            message: 消息内容
            is_user: 是否是用户消息
        """
        current_time = time.time()
        
        # 初始化用户的对话历史
        if user_id not in self._chat_history:
            self._chat_history[user_id] = {
                "messages": [],
                "summaries": []
            }
        
        # 检查是否需要总结之前的对话
        if user_id in self._last_chat_time:
            time_diff = current_time - self._last_chat_time[user_id]
            if time_diff > 300:  # 5分钟无对话，总结之前的对话
                self._summarize_conversation(user_id)
        
        # 更新最后对话时间
        self._last_chat_time[user_id] = current_time
        
        # 添加新消息
        self._chat_history[user_id]["messages"].append({
            "role": "user" if is_user else "assistant",
            "content": message,
            "time": current_time
        })
        
        # 保持最近10轮对话
        if len(self._chat_history[user_id]["messages"]) > 20:  # 10轮=20条消息
            self._summarize_conversation(user_id)
            self._chat_history[user_id]["messages"] = self._chat_history[user_id]["messages"][-20:]

    def _summarize_conversation(self, user_id: str):
        """总结对话内容并添加到历史记录"""
        if not self._chat_history[user_id]["messages"]:
            return
            
        try:
            # 构建对话内容
            conversation = ""
            for msg in self._chat_history[user_id]["messages"]:
                role = "用户" if msg["role"] == "user" else "AI"
                conversation += f"{role}: {msg['content']}\n"
            
            # 使用AI生成总结
            if self.chat:
                summary_prompt = f"请简要总结以下对话的主要内容（100字以内）：\n\n{conversation}"
                summary = self.chat.get_answer(summary_prompt, user_id)
                if summary:
                    self._chat_history[user_id]["summaries"].append({
                        "content": summary,
                        "time": time.time()
                    })
                    # 保持最近5个总结
                    if len(self._chat_history[user_id]["summaries"]) > 5:
                        self._chat_history[user_id]["summaries"] = self._chat_history[user_id]["summaries"][-5:]
        except Exception as e:
            self.LOG.error(f"总结对话失败: {e}")

    def _get_chat_context(self, user_id: str) -> str:
        """获取用户聊天上下文"""
        if user_id not in self._chat_history:
            return ""
            
        context = ""
        
        # 添加历史总结
        summaries = self._chat_history[user_id]["summaries"]
        if summaries:
            context += "历史对话总结：\n"
            for summary in summaries:
                context += f"- {summary['content']}\n"
            context += "\n"
        
        # 添加最近对话
        messages = self._chat_history[user_id]["messages"]
        if messages:
            context += "最近对话：\n"
            for msg in messages:
                role = "用户" if msg["role"] == "user" else "AI"
                context += f"{role}: {msg['content']}\n"
        
        return context

    def update_contact_info(self):
        """更新联系人和群组信息"""
        try:
            self.contacts = self.wcf.get_contacts()
            self.allGroups = self.getAllGroups()
            self.LOG.info("已更新联系人和群组信息")
        except Exception as e:
            self.LOG.error(f"更新联系人和群组信息失败: {e}")
