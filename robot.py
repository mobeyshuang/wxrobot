# -*- coding: utf-8 -*-

import logging
import re
import time
import xml.etree.ElementTree as ET
from queue import Empty
from threading import Thread, Timer
from base.func_zhipu import ZhiPu
from base.func_time import get_time
from base.func_deepseek import Deepseek

from wcferry import Wcf, WxMsg
from PyQt5.QtCore import QTimer

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
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

__version__ = "39.2.4.0"


class Robot(Job):
    """个性化自己的机器人
    """

    def __init__(self, config: Config, wcf: Wcf, chat_type: int, load_from_cache=True) -> None:
        super().__init__()
        self.LOG = logging.getLogger(self.__class__.__name__)
        self.config = config
        self.wcf = wcf
        self.wxid = self.wcf.get_self_wxid()
        self.nickname = ""
        self.enable_AI = True
        self.data_path = os.path.join("config", "data")
        # 创建数据目录，如果不存在
        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)
        
        # 联系人和群组缓存文件路径
        self.contacts_cache_file = os.path.join(self.data_path, "contacts.json")
        self.groups_cache_file = os.path.join(self.data_path, "groups.json")
        self.group_members_cache_file = os.path.join(self.data_path, "group_members.json")
        
        # 初始化联系人和群组
        self.contacts = []
        self.allGroups = {}
        self.group_members = {}  # 群组成员信息缓存
        
        # 优先从缓存加载联系人和群组信息
        if load_from_cache:
            loaded = self.load_contacts_from_cache()
            if loaded:
                self.LOG.info("已从缓存加载联系人和群组信息")
            else:
                self.LOG.info("未找到联系人缓存或加载失败，将从微信获取")
                self.update_contacts_and_groups()
        else:
            self.update_contacts_and_groups()

        # 用户角色管理
        self._user_roles = {}
        self._load_user_roles()

        # 设置状态存储
        self._user_states = {}
        
        # 聊天历史记录存储
        self._chat_history = {}
        self._last_chat_time = {}
        
        # 消息频率限制
        self._msg_timestamps = []

        # 计算周几
        weekday = datetime.now().weekday()
        # 设置默认值，防止配置文件中没有这些属性
        weather_days = getattr(self.config, 'WEATHER_DAYS', [0, 1, 2, 3, 4, 5, 6])  # 默认每天
        news_days = getattr(self.config, 'NEWS_DAYS', [0, 1, 2, 3, 4, 5, 6])  # 默认每天
        
        # 天气与新闻
        if weekday in weather_days and datetime.now().hour in [7, 8, 9] and self.config.CITY_CODE:
            if self.config.WEATHER:
                self.onEveryTime("07:30", self.weatherReport, self.config.WEATHER)
        if weekday in news_days and datetime.now().hour in [7, 8, 9]:
            if self.config.NEWS:
                self.onEveryTime("07:35", self.newsReport)

        # 根据聊天类型初始化AI聊天模型
        self.chat = None
        if chat_type == ChatType.DEEPSEEK:
            if Deepseek.value_check(config.DEEPSEEK):
                self.chat = Deepseek(config.DEEPSEEK)
                self.LOG.info("已选择: Deepseek")
            else:
                self.LOG.warning("Deepseek 配置无效")

        # 获取所有群组信息
        self.allGroups = self.getAllGroups()
        # 更新群成员信息，只对配置的群更新
        for group in self.config.get_groups():
            members = self.wcf.get_chatroom_members(group)
            if members:
                self.LOG.info(f"群 {self.allGroups.get(group, group)} 更新群成员成功：{len(members)} 人")
                
        # 更新联系人信息
        self.update_contact_info()

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
        # 检查task_executor是否已初始化并可用
        has_executor = hasattr(self, 'task_executor') and self.task_executor is not None
        if not has_executor:
            # 只在第一次检测到时打印警告，避免日志被刷爆
            if not hasattr(self, '_warned_no_executor'):
                self.LOG.warning("任务执行器尚未初始化，可能会影响消息处理")
                self._warned_no_executor = True
            
        # 检查是否是本人发送给本人的^设置命令
        if msg.from_self() :
            if msg.content.strip() == "^设置":
                self.LOG.info("收到本人发送给自己的^设置 命令")
                # 使用新的设置处理方法
                self._handle_settings_command(msg.sender)
                return
            if msg.content.strip() == "^更新":
                self.update_contact_info()
                self.config.reload()
                self.LOG.info("已更新配置和联系人信息")
                return
            # 检查是否是本人发送的其他消息
            if msg.sender in self._user_states:
                # 如果还有旧的状态处理，使用它处理
                self._handle_setting_response(msg)
                return
        # 群聊消息
        if msg.from_group():
            
            # 打印群消息，方便调试
            try:
                group_name = self.allGroups.get(msg.roomid, msg.roomid)
                sender_name = self.wcf.get_alias_in_chatroom(msg.sender, msg.roomid) or msg.sender
                self.LOG.info(f"群消息 [{group_name}] {sender_name}: {msg.content[:50]}")
            except Exception as e:
                self.LOG.error(f"打印群消息出错: {e}")
            
            # 检查是否是配置的群组或任务相关群组
            is_in_config_groups = msg.roomid in self.config.get_groups()
            is_in_task_groups = hasattr(self.config, 'get_task_groups') and msg.roomid in self.config.get_task_groups()
            
            # 对配置的群组应用特殊功能
            if is_in_config_groups:
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
            
            # 对于任务相关群，启用消息转发 - 使用if而不是elif，允许配置群同时是任务群
            if is_in_task_groups:
                # 将消息传递给任务执行器处理
                if has_executor:
                    try:
                        self.LOG.info(f"处理任务群消息: [{self.allGroups.get(msg.roomid, msg.roomid)}]")
                        self.task_executor.add_message(msg)
                    except Exception as e:
                        self.LOG.error(f"任务执行器处理消息失败: {e}")
                        import traceback
                        self.LOG.error(traceback.format_exc())
                else:
                    # 只在每个群的第一条消息时打印警告
                    if not hasattr(self, '_warned_groups'):
                        self._warned_groups = set()
                    if msg.roomid not in self._warned_groups:
                        self.LOG.warning(f"任务执行器未初始化，无法处理群 {self.allGroups.get(msg.roomid, msg.roomid)} 的消息")
                        self._warned_groups.add(msg.roomid)
            
            # 对未配置的非任务群组，不做任何处理
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

    def _handle_settings_command(self, sender: str) -> None:
        """处理设置命令，提供设置菜单"""
        # 当前AI功能状态
        ai_status = "✅ 开启" if self.config.AI_ENABLED else "❌ 关闭"
        user_count = len(self.config.get_users())
        group_count = len(self.config.get_groups())
        
        menu = f"""【微信机器人设置】
当前AI状态: {ai_status}
授权用户数: {user_count}
授权群组数: {group_count}

请回复数字选择功能:
1. 启用用户AI权限
2. 禁用用户AI权限
3. 添加用户
4. 删除用户
5. 查看用户列表
6. 添加群组
7. 删除群组
8. 查看群组列表
9. 查看用户角色
10. 设置用户角色
11. 设置自动回复关键词
12. 更新用户和群列表

0. 退出设置"""
        
        # 重置用户状态为等待选项
        self._user_states[sender] = {
            "state": "waiting_for_option"
        }
        
        # 取消已有的定时器(如果存在)
        if hasattr(self, '_settings_timer') and self._settings_timer:
            self._settings_timer.cancel()
        
        # 创建新的定时器，30秒后超时
        self._settings_timer = Timer(30.0, self._exit_settings, args=[sender])
        self._settings_timer.daemon = True  # 设置为守护线程，确保程序退出时线程会被终止
        self._settings_timer.start()
        
        self.sendTextMsg(menu, sender)

    def _handle_setting_response(self, msg: WxMsg) -> None:
        """处理用户对设置的响应"""
        sender = msg.sender
        content = msg.content.strip()
        
        # 重置定时器
        if hasattr(self, '_settings_timer') and self._settings_timer:
            self._settings_timer.cancel()  # 取消旧定时器
            # 创建新定时器
            self._settings_timer = Timer(30.0, self._exit_settings, args=[sender])
            self._settings_timer.daemon = True
            self._settings_timer.start()
            
        state = self._user_states.get(sender, {}).get("state")
        
        if state == "waiting_for_option":
            if content == "0":  # 退出设置
                self.sendTextMsg("已退出设置 ✅", sender)
                del self._user_states[sender]
            elif content == "1":  # 开启AI
                self.config.AI_ENABLED = True
                self.sendTextMsg("已开启AI功能 ✅", sender)
                self._handle_settings_command(sender)  # 返回菜单
            elif content == "2":  # 关闭AI
                self.config.AI_ENABLED = False
                self.sendTextMsg("已关闭AI功能 ✅", sender)
                self._handle_settings_command(sender)  # 返回菜单
            elif content == "3":  # 添加用户
                self._user_states[sender] = {
                    "state": "waiting_for_add_user"
                }
                self.sendTextMsg("请发送要添加的用户微信号或名片", sender)
            elif content == "4":  # 删除用户
                users = self.config.get_users()
                if not users:
                    self.sendTextMsg("当前没有允许使用AI的用户", sender)
                    self._handle_settings_command(sender)  # 返回菜单
                    return
                user_list = "当前用户列表：\n"
                for i, user in enumerate(users, 1):
                    display_name = self._get_user_display_name(user)
                    user_list += f"{i}. {display_name}\n"
                user_list += "\n请回复序号删除对应用户"
                self._user_states[sender] = {
                    "state": "waiting_for_delete_user", 
                    "users": users
                }
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
                self._handle_settings_command(sender)  # 返回菜单
            elif content == "6":  # 添加群组
                self._user_states[sender] = {
                    "state": "waiting_for_add_group"
                }
                self.sendTextMsg("请发送要添加的群名称，我会自动匹配群ID", sender)
            elif content == "7":  # 删除群组
                groups = self.config.get_groups()
                if not groups:
                    self.sendTextMsg("当前没有配置的群组", sender)
                    self._handle_settings_command(sender)  # 返回菜单
                    return
                group_list = "当前群组列表：\n"
                for i, group_id in enumerate(groups, 1):
                    group_name = self.allGroups.get(group_id, group_id)
                    group_list += f"{i}. {group_name} ({group_id})\n"
                group_list += "\n请回复序号删除对应群组"
                self._user_states[sender] = {
                    "state": "waiting_for_delete_group", 
                    "groups": groups
                }
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
                self._handle_settings_command(sender)  # 返回菜单
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
                self._handle_settings_command(sender)  # 返回菜单
            elif content == "10":  # 设置用户角色
                users = self.config.get_users()
                if not users:
                    self.sendTextMsg("当前没有允许使用AI的用户", sender)
                    self._handle_settings_command(sender)  # 返回菜单
                    return
                user_list = "请选择要设置角色的用户（回复序号）：\n"
                for i, user in enumerate(users, 1):
                    display_name = self._get_user_display_name(user)
                    role = self._get_user_role(user)
                    user_list += f"{i}. {display_name}\n   当前角色: {role}\n"
                self._user_states[sender] = {
                    "state": "waiting_for_select_user_role", 
                    "users": users
                }
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
            self._handle_settings_command(sender)  # 返回菜单
            
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
            self._handle_settings_command(sender)  # 返回菜单
            
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
            self._handle_settings_command(sender)  # 返回菜单
            
        elif state == "waiting_for_add_group":
            # 处理添加群组
            group_name = content.strip()
            # 在allGroups中查找匹配的群组
            found_groups = [(gid, name) for gid, name in self.allGroups.items() 
                          if group_name.lower() in name.lower()]
            
            if not found_groups:
                self.sendTextMsg(f"未找到名称包含 '{group_name}' 的群组", sender)
                self._handle_settings_command(sender)  # 返回菜单
            elif len(found_groups) == 1:
                # 只找到一个匹配的群组，直接添加
                group_id, group_name = found_groups[0]
                if self.config.add_group(group_id):
                    self.sendTextMsg(f"已成功添加群组：{group_name} ({group_id}) ✅", sender)
                else:
                    self.sendTextMsg(f"添加群组失败，该群组可能已在列表中", sender)
                self._handle_settings_command(sender)  # 返回菜单
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
            self._handle_settings_command(sender)  # 返回菜单
            
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
            self._handle_settings_command(sender)  # 返回菜单
            
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
                self._handle_settings_command(sender)  # 返回菜单
                
        elif state == "waiting_for_input_role":
            selected_user = self._user_states[sender].get("selected_user")
            if selected_user:
                self._user_roles[selected_user] = content
                self._save_user_roles()
                display_name = self._get_user_display_name(selected_user)
                self.sendTextMsg(f"已为用户 {display_name} 设置新角色 ✅", sender)
            else:
                self.sendTextMsg("设置失败，未找到选择的用户", sender)
            self._handle_settings_command(sender)  # 返回菜单

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
                    #self.LOG.info(msg)
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
        try:
            groups = self.wcf.query_sql("MicroMsg.db", "SELECT UserName, NickName FROM Contact;")
            if not groups:
                self.LOG.warning("未获取到任何群组信息")
                return {}
            return {contact["UserName"]: contact["NickName"] for contact in groups}
        except Exception as e:
            self.LOG.error(f"获取群组信息失败: {str(e)}")
            return {}

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

    def newsReport(self, receivers=None) -> None:
        """
        发送新闻报告
        
        Args:
            receivers: 可选的接收者列表。如果为None，则使用配置中的NEWS设置
        """
        if receivers is None:
            receivers = self.config.NEWS
        elif isinstance(receivers, str):
            # 处理单个接收者的情况（字符串）
            receivers = [receivers]
        
        if not receivers:
            return

        news = News().get_important_news()
        for r in receivers:
            self.sendTextMsg(news, r)
        news = News().get_domestic_news()
        for r in receivers:
            self.sendTextMsg(news, r)
        news = News().get_tech_news()
        for r in receivers:
            self.sendTextMsg(news, r)

    def weatherReport(self, receivers: list) -> None:
        if not receivers or not self.config.CITY_CODE:
            self.LOG.warning("未配置天气城市代码或接收人")
            return

        report = Weather(self.config.CITY_CODE).get_weather()
        
        # 使用 DeepSeek 生成祝福语
        if self.chat and isinstance(self.chat, Deepseek):
            prompt = f"""请根据以上天气信息输出一句与天气有关的祝福语,并加一个emoji。"

天气信息：
{report}"""
            
            # 使用自定义系统提示词
            system_prompt = "你是对话助手，正常回答对话，不需要进行多余的解释。"
            blessing = self.chat.chat(prompt, system_prompt=system_prompt)
            if blessing:
                report += f"\n\n{blessing}"
        
        for r in receivers:
            # 特殊处理 filehelper
            if r == "filehelper":
                self.sendTextMsg(report, r)
            else:
                wxid = get_wxid_by_name(self, r)
                self.sendTextMsg(report, wxid)

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
        """更新联系人和群组信息（兼容方法，请直接使用update_contacts_and_groups）"""
        # 直接调用更新方法
        return self.update_contacts_and_groups()

    def _exit_settings(self, sender: str) -> None:
        """超时退出设置模式"""
        if sender in self._user_states:
            self.sendTextMsg("设置会话已超时，已自动退出设置模式。", sender)
            del self._user_states[sender]
            self.LOG.info("设置会话已超时，已自动退出设置模式")
            
        # 取消定时器
        if hasattr(self, '_settings_timer') and self._settings_timer:
            self._settings_timer.cancel()
            self._settings_timer = None

    def cleanup(self):
        """统一的资源清理方法，确保所有退出路径都执行相同的清理流程"""
        try:
            print("执行机器人资源清理...")
            
            # 停止消息接收
            try:
                print("停止消息接收...")
                self.wcf.disable_recv_msg()
                print("消息接收已停止")
            except Exception as e:
                print(f"停止消息接收出错: {e}")
            
            # 清理wcf资源
            try:
                print("清理wcf资源...")
                # 设置一个标志，避免重复清理
                if hasattr(self, '_wcf_cleanup_done') and self._wcf_cleanup_done:
                    print("wcf已经被清理过，跳过")
                    return True
                
                import threading
                import time
                
                # 定义一个计数器和事件
                cleanup_done = threading.Event()
                
                # 清理函数
                def do_cleanup():
                    try:
                        print("开始执行wcf.cleanup()...")
                        # 添加超时控制
                        self.wcf.cleanup()
                        self._wcf_cleanup_done = True
                        print("wcf.cleanup()执行完成")
                        cleanup_done.set()
                    except Exception as e:
                        print(f"wcf.cleanup方法出错: {e}")
                        import traceback
                        traceback.print_exc()
                        cleanup_done.set()
                
                # 启动清理线程
                cleanup_thread = threading.Thread(target=do_cleanup)
                cleanup_thread.daemon = True
                cleanup_thread.start()
                
                # 等待清理完成，最多等待1.5秒 (减少超时时间，避免卡死)
                start_time = time.time()
                result = cleanup_done.wait(1.5)
                elapsed_time = time.time() - start_time
                
                if not result:
                    print(f"警告: wcf资源清理超时({elapsed_time:.2f}秒)，将强制终止清理线程")
                    # 无论成功与否，都设置清理标志，避免重复清理
                    self._wcf_cleanup_done = True
                    print("已标记清理完成，程序将继续退出")
                else:
                    print(f"wcf资源清理完成，耗时: {elapsed_time:.2f}秒")
            except Exception as e:
                print(f"清理wcf资源过程出错: {e}")
                import traceback
                traceback.print_exc()
                # 设置清理标志，避免重复清理
                self._wcf_cleanup_done = True
            
            # 停止任务执行器
            if hasattr(self, 'task_executor') and self.task_executor:
                try:
                    print("停止任务执行器...")
                    self.task_executor.stop()
                    print("任务执行器已停止")
                except Exception as e:
                    print(f"停止任务执行器出错: {e}")
                
            print("机器人资源清理完成")
            return True
        except Exception as e:
            print(f"机器人资源清理过程中出错: {e}")
            import traceback
            traceback.print_exc()
            
            # 即使出错也标记清理已完成，避免卡死
            self._wcf_cleanup_done = True
            
            return False

    def __del__(self):
        """对象销毁时的清理工作"""
        try:
            # 取消所有定时器
            if hasattr(self, '_settings_timer') and self._settings_timer:
                self._settings_timer.cancel()
                self._settings_timer = None
            
            # 调用通用清理方法
            if hasattr(self, 'cleanup'):
                self.cleanup()
            
            self.LOG.info("Robot对象已销毁，资源已清理")
        except Exception as e:
            # 即使发生异常也不抛出，防止在程序结束时引发问题
            if hasattr(self, 'LOG'):
                self.LOG.error(f"Robot对象销毁时出错: {e}")
            # 尝试最后一次cleanup
            try:
                if hasattr(self, 'wcf'):
                    self.wcf.disable_recv_msg()
                    self.wcf.cleanup()
            except:
                pass

    def update_contacts_and_groups(self):
        """更新联系人和群组信息"""
        self.LOG.info("正在从微信获取联系人和群组信息...")
        try:
            # 获取联系人列表
            contacts = self.wcf.get_contacts()
            if not contacts:
                self.LOG.warning("获取联系人失败，可能是微信未登录或API调用失败")
            else:
                self.contacts = contacts
                self.LOG.info(f"获取到 {len(contacts)} 个联系人")
            
            # 获取群组列表
            groups = {}
            # 使用getAllGroups方法替代不存在的get_chatrooms方法
            all_contacts = self.getAllGroups()
            for wxid, name in all_contacts.items():
                if wxid and "@chatroom" in wxid:
                    groups[wxid] = name
            
            if not groups:
                self.LOG.warning("获取群组失败，可能是微信未登录或API调用失败")
            else:
                self.allGroups = groups
                self.LOG.info(f"获取到 {len(groups)} 个群组")
            
            # 保存到缓存
            self.save_contacts_to_cache()
            
            return True
        except Exception as e:
            self.LOG.error(f"更新联系人和群组信息失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_contacts_from_cache(self):
        """从缓存文件加载联系人和群组信息"""
        try:
            # 加载联系人
            if os.path.exists(self.contacts_cache_file):
                with open(self.contacts_cache_file, "r", encoding="utf-8") as f:
                    self.contacts = json.load(f)
                self.LOG.info(f"从缓存加载了 {len(self.contacts)} 个联系人")
            else:
                self.LOG.warning("联系人缓存文件不存在")
                return False
            
            # 加载群组
            if os.path.exists(self.groups_cache_file):
                with open(self.groups_cache_file, "r", encoding="utf-8") as f:
                    self.allGroups = json.load(f)
                self.LOG.info(f"从缓存加载了 {len(self.allGroups)} 个群组")
            else:
                self.LOG.warning("群组缓存文件不存在")
                return False
            
            # 加载群成员信息
            if os.path.exists(self.group_members_cache_file):
                with open(self.group_members_cache_file, "r", encoding="utf-8") as f:
                    self.group_members = json.load(f)
                self.LOG.info(f"从缓存加载了 {len(self.group_members)} 个群的成员信息")
            
            # 检查数据有效性
            if not self.contacts or not self.allGroups:
                self.LOG.warning("缓存数据不完整，需要重新获取")
                return False
            
            return True
        except Exception as e:
            self.LOG.error(f"加载联系人和群组缓存失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def save_contacts_to_cache(self):
        """保存联系人和群组信息到缓存文件"""
        try:
            # 保存联系人
            with open(self.contacts_cache_file, "w", encoding="utf-8") as f:
                json.dump(self.contacts, f, ensure_ascii=False, indent=2)
            self.LOG.info(f"已保存 {len(self.contacts)} 个联系人到缓存")
            
            # 保存群组
            with open(self.groups_cache_file, "w", encoding="utf-8") as f:
                json.dump(self.allGroups, f, ensure_ascii=False, indent=2)
            self.LOG.info(f"已保存 {len(self.allGroups)} 个群组到缓存")
            
            # 保存群成员信息
            if hasattr(self, 'group_members'):
                # 过滤掉可能的None或空值
                valid_group_members = {k: v for k, v in self.group_members.items() if v}
                with open(self.group_members_cache_file, "w", encoding="utf-8") as f:
                    json.dump(valid_group_members, f, ensure_ascii=False, indent=2)
                self.LOG.info(f"已保存 {len(valid_group_members)} 个群的成员信息到缓存")
            
            return True
        except Exception as e:
            self.LOG.error(f"保存联系人和群组缓存失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_group_members(self, group_id=None):
        """更新群成员信息
        
        Args:
            group_id: 指定群ID，如果为None则更新所有群
            
        Returns:
            bool: 是否更新成功
        """
        try:
            if not hasattr(self, 'group_members'):
                self.group_members = {}
            
            if group_id:
                # 更新指定群
                members = self.wcf.get_chatroom_members(group_id)
                if members:
                    self.group_members[group_id] = members
                    self.LOG.info(f"已更新群 {group_id} 的成员信息，共 {len(members)} 个成员")
                else:
                    self.LOG.warning(f"获取群 {group_id} 的成员信息失败")
            else:
                # 更新所有群
                for group_id in self.allGroups:
                    members = self.wcf.get_chatroom_members(group_id)
                    if members:
                        self.group_members[group_id] = members
                        self.LOG.info(f"已更新群 {group_id} 的成员信息，共 {len(members)} 个成员")
                    else:
                        self.LOG.warning(f"获取群 {group_id} 的成员信息失败")
            
            # 保存到缓存
            self.save_contacts_to_cache()
            return True
        except Exception as e:
            self.LOG.error(f"更新群成员信息失败: {e}")
            import traceback
            traceback.print_exc()
            return False

def get_wxid_by_name(robot, name: str, target_type: str = "friend") -> str:
    """
    根据昵称获取wxid，支持多种匹配方式
    
    Args:
        robot: Robot实例
        name: 昵称或wxid
        target_type: 目标类型，可选 "friend" 或 "group"
        
    Returns:
        str: 找到的wxid，如果未找到则返回空字符串
    """
    try:
        # 如果输入已经是wxid格式，直接返回
        if name.endswith("@chatroom") or name.endswith("@openim") or (len(name) > 10 and not name.isascii()):
            print(f"输入似乎是wxid格式: {name}，直接使用")
            return name
    
        # 检查特殊帐号
        special_accounts = ["filehelper", "medianote"]
        if name.lower() in special_accounts:
            return name.lower()
        
        if target_type == "friend":
            # 先在联系人列表中查找
            if hasattr(robot, 'contacts') and robot.contacts:
                print(f"在contacts中查找: {name}")
                for contact in robot.contacts:
                    if isinstance(contact, dict):
                        # 检查各种可能的名称字段
                        if (contact.get("name") == name or 
                            contact.get("remark") == name or 
                            contact.get("nickname") == name):
                            print(f"在contacts中匹配到: {name} -> {contact.get('wxid')}")
                            return contact.get("wxid")
                        
                        # 如果包含特殊字符，尝试模糊匹配
                        if any(ord(c) > 127 for c in name):
                            contact_name = contact.get("name", "")
                            contact_remark = contact.get("remark", "")
                            contact_nickname = contact.get("nickname", "")
                            
                            # 移除表情符号等特殊字符后比较
                            clean_name = ''.join(c for c in name if ord(c) < 10000)
                            clean_contact_name = ''.join(c for c in contact_name if ord(c) < 10000)
                            clean_contact_remark = ''.join(c for c in contact_remark if ord(c) < 10000)
                            clean_contact_nickname = ''.join(c for c in contact_nickname if ord(c) < 10000)
                            
                            if (clean_name and (clean_name == clean_contact_name or 
                                            clean_name == clean_contact_remark or 
                                            clean_name == clean_contact_nickname)):
                                print(f"在contacts中模糊匹配到: {name}({clean_name}) -> {contact.get('wxid')}")
                                return contact.get("wxid")
            
            # 然后在好友列表中查找
            print(f"在好友列表中查找: {name}")
            friends = robot.wcf.get_friends()
            for friend in friends:
                if (friend.get("name") == name or 
                    friend.get("remark") == name or 
                    friend.get("nickname") == name):
                    print(f"在好友列表中匹配到: {name} -> {friend.get('wxid')}")
                    return friend.get("wxid")
                    
                # 如果包含特殊字符，尝试模糊匹配
                if any(ord(c) > 127 for c in name):
                    friend_name = friend.get("name", "")
                    friend_remark = friend.get("remark", "")
                    friend_nickname = friend.get("nickname", "")
                    
                    # 移除表情符号等特殊字符后比较
                    clean_name = ''.join(c for c in name if ord(c) < 10000)
                    clean_friend_name = ''.join(c for c in friend_name if ord(c) < 10000)
                    clean_friend_remark = ''.join(c for c in friend_remark if ord(c) < 10000)
                    clean_friend_nickname = ''.join(c for c in friend_nickname if ord(c) < 10000)
                    
                    if (clean_name and (clean_name == clean_friend_name or 
                                      clean_name == clean_friend_remark or 
                                      clean_name == clean_friend_nickname)):
                        print(f"在好友列表中模糊匹配到: {name}({clean_name}) -> {friend.get('wxid')}")
                        return friend.get("wxid")
        else:  # group
            # 从群组列表中查找
            if hasattr(robot, 'allGroups'):
                for wxid, group_name in robot.allGroups.items():
                    if group_name == name:
                        return wxid
                        
                    # 如果包含特殊字符，尝试模糊匹配
                    if any(ord(c) > 127 for c in name):
                        # 移除表情符号等特殊字符后比较
                        clean_name = ''.join(c for c in name if ord(c) < 10000)
                        clean_group_name = ''.join(c for c in group_name if ord(c) < 10000)
                        
                        if clean_name and clean_name == clean_group_name:
                            print(f"在群组列表中模糊匹配到: {name}({clean_name}) -> {wxid}")
                            return wxid
        
        print(f"未找到与 '{name}' 匹配的wxid")
        # 如果有特殊字符，输出清理后的结果
        if any(ord(c) > 127 for c in name):
            clean_name = ''.join(c for c in name if ord(c) < 10000)
            print(f"名称包含特殊字符，清理后为: '{clean_name}'")
                    
        return ""
    except Exception as e:
        print(f"获取wxid失败: {e}")
        import traceback
        traceback.print_exc()
        return "" 